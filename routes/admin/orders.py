"""Quản trị đơn hàng."""
from core import db
from core.router import route
from core.server import HttpError, redirect
from routes.admin.common import staff, phone, pager
from services import admin_orders, orders
from services.orders import STATUS_VI, PAY_VI, PAY_STATUS_VI


@route("/quan-tri/don-hang")
def order_list(req):
    staff(req)
    st = req.query.get("trang-thai") if req.query.get("trang-thai") in STATUS_VI else None
    q, d1, d2 = req.query.get("q", "").strip()[:50], req.query.get("tu", ""), req.query.get("den", "")
    _, total = admin_orders.search(req.db, st, q, d1, d2, limit=1)
    pg = pager(req, total)
    rows, _ = admin_orders.search(req.db, st, q, d1, d2, limit=pg["per"], offset=pg["offset"])
    for r in rows:
        r["phone_shown"] = phone(req, r["receiver_phone"])
    counts = {k: db.scalar(req.db, "SELECT COUNT(*) FROM orders WHERE status=?", (k,)) for k in STATUS_VI}
    return req.render("admin/orders.html", active="don-hang", rows=rows, pg=pg, st=st, q=q, d1=d1, d2=d2,
                      counts=counts, all_count=db.scalar(req.db, "SELECT COUNT(*) FROM orders"),
                      status_vi=STATUS_VI, pay_vi=PAY_VI, pay_status_vi=PAY_STATUS_VI)


@route("/quan-tri/don-hang/<code>", methods=("GET", "POST"))
def order_detail(req, code):
    staff(req)
    row = db.one(req.db, "SELECT * FROM orders WHERE order_code=?", (code,))
    if not row:
        raise HttpError(404, "Không tìm thấy đơn hàng.")
    error = notice = ""
    if req.method == "POST":
        req.check_csrf()
        act = req.form.get("action", "")
        try:
            if act == "chuyen":
                admin_orders.change_status(req.db, row["id"], req.form.get("to"), req.user, req.form.get("note", "").strip(),
                                           req.form.get("carrier", ""), req.form.get("tracking", "").strip())
            elif act == "huy":
                admin_orders.admin_cancel(req.db, row["id"], req.form.get("reason", "").strip(), req.user)
            elif act == "ghi-chu":
                admin_orders.save_note(req.db, row["id"], req.form.get("internal_note"))
            return redirect(f"/quan-tri/don-hang/{code}?tb=ok")
        except orders.OrderError as e:
            error = str(e)
    if req.query.get("tb") == "ok":
        notice = "Đã cập nhật đơn hàng."
    o = orders.detail(req.db, db.one(req.db, "SELECT * FROM orders WHERE id=?", (row["id"],)))
    o["phone_shown"] = phone(req, o["receiver_phone"])
    cust = dict(db.one(req.db, "SELECT * FROM customers WHERE id=?", (o["customer_id"],)))
    cust["phone_shown"] = phone(req, cust["phone"])
    hist = [dict(h) for h in db.all(req.db, """SELECT h.*, u.full_name AS by_name FROM order_status_history h
                                               LEFT JOIN users u ON u.id=h.changed_by WHERE h.order_id=? ORDER BY h.changed_at, h.id""", (o["id"],))]
    return req.render("admin/order.html", active="don-hang", o=o, cust=cust, hist=hist, error=error, notice=notice,
                      actions=admin_orders.actions_for(o), can_cancel=o["status"] in admin_orders.CANCELLABLE,
                      carriers=admin_orders.CARRIERS, reasons=["Khách không nghe máy sau 3 lần gọi", "Khách đổi ý",
                                                               "Hết hàng ở kho", "Thông tin giao hàng không hợp lệ", "Nghi ngờ đơn ảo"],
                      shipment=db.one(req.db, "SELECT * FROM shipments WHERE order_id=?", (o["id"],)),
                      payments=db.all(req.db, "SELECT * FROM payments WHERE order_id=? ORDER BY id", (o["id"],)),
                      status_vi=STATUS_VI, pay_vi=PAY_VI)
