"""Quản trị: mã giảm giá, banner & giá sốc, duyệt đánh giá."""
from core import db
from core.router import route
from core.server import HttpError, redirect
from routes.admin.common import admin, pager
from services import admin_marketing as mk

MSG = {"ok": "Đã lưu.", "moi": "Đã tạo mã giảm giá.", "xoa": "Đã gỡ khỏi đợt giá sốc."}


@route("/quan-tri/ma-giam-gia", methods=("GET", "POST"))
def vouchers(req):
    admin(req)
    error, f = "", {"type": "fixed", "per_customer_limit": "1", "is_active": "1"}
    if req.method == "POST":
        req.check_csrf()
        act = req.form.get("action")
        vid = int(req.form.get("vid") or 0)
        try:
            if act == "tao":
                mk.save_voucher(req.db, req.form)
                return redirect("/quan-tri/ma-giam-gia?tb=moi")
            if act == "sua":
                mk.save_voucher(req.db, req.form, vid)
            elif act in ("bat", "tat"):
                req.db.execute("UPDATE vouchers SET is_active=? WHERE id=?", (1 if act == "bat" else 0, vid))
            return redirect(f"/quan-tri/ma-giam-gia?tb=ok&sua={vid}" if act == "sua" else "/quan-tri/ma-giam-gia?tb=ok")
        except mk.MarketingError as e:
            error, f = str(e), dict(req.form)
    rows = [dict(r) for r in db.all(req.db, """SELECT v.*, (SELECT COUNT(*) FROM orders o WHERE o.voucher_id=v.id AND o.status<>'cancelled') n_orders,
                (SELECT COALESCE(SUM(o.discount_amount),0) FROM orders o WHERE o.voucher_id=v.id AND o.status<>'cancelled') spent
                FROM vouchers v ORDER BY v.is_active DESC, v.id DESC""")]
    for r in rows:
        r["state"], r["state_vi"] = mk.voucher_state(r)
    edit = req.query.get("sua", "")
    if error and f.get("action") == "sua":
        edit = f.get("vid", "")
    return req.render("admin/vouchers.html", active="ma-giam-gia", rows=rows, f=f, error=error,
                      notice=MSG.get(req.query.get("tb", ""), ""), edit=str(edit))


@route("/quan-tri/banner", methods=("GET", "POST"))
def banners(req):
    admin(req)
    error = ""
    promo = mk.current_promotion(req.db)
    if req.method == "POST":
        req.check_csrf()
        act = req.form.get("action")
        try:
            with db.transaction(req.db):
                if act == "banner":
                    mk.save_banner(req.db, req.form, int(req.form.get("bid") or 0))
                elif promo and act == "gs-sua":
                    mk.save_flash_item(req.db, promo["id"], req.form, int(req.form.get("item_id") or 0))
                elif promo and act == "gs-them":
                    mk.save_flash_item(req.db, promo["id"], req.form)
                elif promo and act == "gs-xoa":
                    mk.remove_flash_item(req.db, promo["id"], int(req.form.get("item_id") or 0))
            return redirect("/quan-tri/banner?tb=" + ("xoa" if act == "gs-xoa" else "ok") + "#" + ("gia-soc" if act.startswith("gs") else "banner"))
        except (mk.MarketingError, ValueError) as e:
            error = str(e)
    bl = db.all(req.db, "SELECT * FROM banners ORDER BY position, sort_order")
    items = []
    if promo:
        items = db.all(req.db, """SELECT pi.*, v.sku, v.sale_price, COALESCE(v.storage||' · ','')||v.color_name label, p.name
                                  FROM promotion_items pi JOIN product_variants v ON v.id=pi.variant_id JOIN products p ON p.id=v.product_id
                                  WHERE pi.promotion_id=? ORDER BY pi.id""", (promo["id"],))
    variants = db.all(req.db, """SELECT v.id, v.sku, v.sale_price, p.name, COALESCE(v.storage||' · ','')||v.color_name label FROM product_variants v
                                 JOIN products p ON p.id=v.product_id WHERE v.is_active=1 AND p.is_active=1 ORDER BY p.name, v.sale_price""")
    products = db.all(req.db, "SELECT id, name FROM products WHERE is_active=1 ORDER BY name")
    return req.render("admin/banners.html", active="banner", banners=bl, promo=promo, items=items, variants=variants,
                      products=products, error=error, notice=MSG.get(req.query.get("tb", ""), ""))


@route("/quan-tri/danh-gia", methods=("GET", "POST"))
def reviews(req):
    admin(req)
    error = ""
    st = req.query.get("tt", "pending")
    if st not in ("pending", "approved", "hidden"):
        st = "pending"
    if req.method == "POST":
        req.check_csrf()
        try:
            mk.moderate(req.db, int(req.form.get("rid") or 0), req.form.get("action"))
            return redirect(f"/quan-tri/danh-gia?tt={st}&tb=ok")
        except (mk.MarketingError, ValueError) as e:
            error = str(e)
    counts = {r["status"]: r["n"] for r in db.all(req.db, "SELECT status, COUNT(*) n FROM reviews GROUP BY status")}
    total = counts.get(st, 0)
    pg = pager(req, total, 20)
    rows = db.all(req.db, """SELECT r.*, p.name product, p.slug, c.kind, cu.full_name, o.order_code FROM reviews r
                             JOIN products p ON p.id=r.product_id JOIN categories c ON c.id=p.category_id
                             JOIN customers cu ON cu.id=r.customer_id JOIN orders o ON o.id=r.order_id
                             WHERE r.status=? ORDER BY r.created_at DESC LIMIT ? OFFSET ?""", (st, pg["per"], pg["offset"]))
    return req.render("admin/reviews.html", active="danh-gia", rows=rows, st=st, counts=counts, pg=pg, error=error,
                      notice="Đã cập nhật đánh giá. Điểm trung bình của sản phẩm đã được tính lại." if req.query.get("tb") else "")
