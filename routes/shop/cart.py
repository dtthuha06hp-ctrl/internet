"""Giỏ hàng: /gio-hang và các thao tác thêm, sửa, xóa, mã giảm giá."""
import re
import config
from core import db
from core.router import route
from core.server import json_response, redirect
from services import cart as cart_svc, products


QTY_MSG = "Số lượng phải là số nguyên từ 1 đến 3."


def _qty(x):
    """Số lượng gửi lên: bỏ trống = 1; không phải số nguyên dương thì báo lỗi (lỗi B3)."""
    if x is None or str(x).strip() == "":
        return 1
    try:
        q = int(str(x).strip())
    except ValueError:
        raise cart_svc.CartError(QTY_MSG)
    if q < 1:
        raise cart_svc.CartError(QTY_MSG)
    return q


def _int(x, default=0):
    try:
        return int(x)
    except (TypeError, ValueError):
        return default


@route("/gio-hang")
def view(req):
    c = cart_svc.get(req.db, req.session)
    s = cart_svc.summary(req.db, c)
    removed = None
    m = re.fullmatch(r"(\d+)-(\d)", req.query.get("da-xoa", ""))
    if m:
        r = db.one(req.db, "SELECT p.name FROM product_variants v JOIN products p ON p.id=v.product_id WHERE v.id=?", (int(m.group(1)),))
        if r:
            removed = {"variant_id": int(m.group(1)), "qty": int(m.group(2)), "name": r["name"]}
    # gợi ý phụ kiện dùng được cho các điện thoại trong giỏ
    phone_ids = [i["product_id"] for i in s["items"] if i["kind"] == "phone"]
    in_cart = {i["product_id"] for i in s["items"]}
    suggest = []
    if phone_ids:
        q = ",".join("?" * len(phone_ids))
        suggest = [p for p in products.cards(req.db, f"AND p.id IN (SELECT accessory_id FROM accessory_compat WHERE phone_id IN ({q}))",
                                             phone_ids, order="p.sold_count DESC", limit=12)
                   if p["id"] not in in_cart and p["in_stock"]][:5]
    return req.render("shop/cart.html", s=s, removed=removed, suggest=suggest, msg=req.query.get("tb", ""))


@route("/gio-hang/them", methods=("POST",))
def add(req):
    req.check_csrf()
    data = req.json or req.form
    vid = _int(data.get("variant_id"))
    try:
        if not vid:
            vid = cart_svc.default_variant(req.db, _int(data.get("product_id")))
        res = cart_svc.add(req.db, req.session, vid, _qty(data.get("qty")))
    except cart_svc.CartError as e:
        if req.json is not None:
            return json_response({"ok": False, "message": str(e), "count": req.cart_count()}, 400)
        return redirect("/gio-hang?tb=" + _q(str(e)))
    msg = f"Đã thêm {res['name']} vào giỏ hàng"
    if res["capped"]:
        msg = f"Giỏ đã có tối đa {res['quantity']} sản phẩm {res['name']}"
    if req.json is not None:
        return json_response({"ok": True, "message": msg, "count": req.cart_count()})
    return redirect(data.get("next") if (data.get("next") or "").startswith("/") else "/gio-hang")


def _q(s):
    from urllib.parse import quote
    return quote(s)


@route("/gio-hang/cap-nhat", methods=("POST",))
def update(req):
    req.check_csrf()
    vid = _int(req.form.get("variant_id"))
    action = req.form.get("action", "")
    if action == "xoa":
        c = cart_svc.get(req.db, req.session)
        qty = db.scalar(req.db, "SELECT quantity FROM cart_items WHERE cart_id=? AND variant_id=?", (c["id"], vid)) if c else 0
        cart_svc.set_qty(req.db, req.session, vid, 0)
        return redirect(f"/gio-hang?da-xoa={vid}-{qty or 1}")
    try:
        q = _qty(req.form.get("qty"))
    except cart_svc.CartError as e:
        return redirect("/gio-hang?tb=" + _q(str(e)))
    cart_svc.set_qty(req.db, req.session, vid, q)
    if q > config.MAX_QTY_PER_ITEM:
        return redirect("/gio-hang?tb=" + _q(f"Mỗi sản phẩm chỉ mua tối đa {config.MAX_QTY_PER_ITEM} chiếc trong một đơn."))
    return redirect("/gio-hang")


@route("/gio-hang/ma-giam-gia", methods=("POST",))
def voucher(req):
    req.check_csrf()
    code = "" if req.form.get("action") == "bo" else req.form.get("code", "")
    cart_svc.set_voucher(req.db, req.session, code[:30])
    return redirect("/gio-hang#ma-giam-gia")
