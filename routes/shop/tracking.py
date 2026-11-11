"""Tra cứu đơn hàng (mã đơn + SĐT) và hủy đơn đang chờ xác nhận.

Dùng POST để số điện thoại không nằm trên thanh địa chỉ.
"""
from core.router import route
from core.server import redirect
from services import orders


@route("/tra-cuu-don-hang", methods=("GET", "POST"))
def track(req):
    code = phone = error = ""
    o = None
    notice = {"huy": "Đã hủy đơn hàng. Sản phẩm đã được trả lại kho."}.get(req.query.get("tb", ""), "")
    if req.method == "POST":
        req.check_csrf()
        code = req.form.get("code", "").strip().upper()[:20]
        phone = req.form.get("phone", "")[:15]
        row = orders.find(req.db, code, phone)
        if not row:
            error = "Không tìm thấy đơn phù hợp. Kiểm tra lại mã đơn (ví dụ NM2611110001) và số điện thoại đã dùng khi đặt."
        else:
            o = orders.detail(req.db, row)
            if req.form.get("action") == "huy":
                try:
                    orders.cancel(req.db, o["id"], req.form.get("reason"))
                    o = orders.detail(req.db, orders.find(req.db, code, phone))
                    notice = "Đã hủy đơn hàng. Sản phẩm đã được trả lại kho."
                except orders.OrderError as e:
                    error = str(e)
    return req.render("shop/tracking.html", code=code, phone=phone, o=o, error=error, notice=notice,
                      reasons=orders.CANCEL_REASONS, token=orders.order_token(o["order_code"]) if o else "")


@route("/dat-hang-thanh-cong/<code>/huy", methods=("POST",))
def cancel_from_success(req, code):
    req.check_csrf()
    from core import db
    o = db.one(req.db, "SELECT * FROM orders WHERE order_code=?", (code,))
    t = req.form.get("t")
    if not o or not orders.check_token(code, t):
        return redirect("/tra-cuu-don-hang")
    try:
        orders.cancel(req.db, o["id"], req.form.get("reason"))
        return redirect(f"/dat-hang-thanh-cong/{code}?t={t}&tt=huy")
    except orders.OrderError:
        return redirect(f"/dat-hang-thanh-cong/{code}?t={t}&tt=khong-huy")
