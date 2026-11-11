"""Quản trị: khách hàng (nhân viên xem được, SĐT bị che)."""
from core import db
from core.router import route
from core.server import HttpError
from routes.admin.common import staff, pager, phone
from services.orders import STATUS_VI


@route("/quan-tri/khach-hang")
def customer_list(req):
    staff(req)
    q = req.query.get("q", "").strip()[:50]
    sort = req.query.get("xep", "moi")
    sql, args = " FROM customers c LEFT JOIN users u ON u.id=c.user_id WHERE 1=1", []
    if q:
        sql += " AND (c.full_name LIKE ? OR c.phone LIKE ? OR c.email LIKE ?)"
        args += [f"%{q}%"] * 3
    total = db.scalar(req.db, "SELECT COUNT(*)" + sql, args)
    pg = pager(req, total)
    order = {"chi-tieu": "c.total_spent DESC", "don": "c.order_count DESC"}.get(sort, "c.created_at DESC, c.id DESC")
    rows = [dict(r) for r in db.all(req.db, """SELECT c.*, u.id uid, u.status ustatus,
              (SELECT MAX(created_at) FROM orders o WHERE o.customer_id=c.id) last_order""" + sql
                                    + f" ORDER BY {order} LIMIT ? OFFSET ?", args + [pg["per"], pg["offset"]])]
    for r in rows:
        r["phone_shown"] = phone(req, r["phone"])
    return req.render("admin/customers.html", active="khach-hang", rows=rows, pg=pg, q=q, sort=sort)


@route("/quan-tri/khach-hang/<cid>")
def customer_detail(req, cid):
    staff(req)
    c = db.one(req.db, """SELECT c.*, u.email login_email, u.status ustatus FROM customers c
                          LEFT JOIN users u ON u.id=c.user_id WHERE c.id=?""", (int(cid) if cid.isdigit() else 0,))
    if not c:
        raise HttpError(404, "Không tìm thấy khách hàng.")
    c = dict(c)
    c["phone_shown"] = phone(req, c["phone"])
    orders = db.all(req.db, """SELECT o.*, (SELECT SUM(quantity) FROM order_items i WHERE i.order_id=o.id) n_items
                               FROM orders o WHERE o.customer_id=? ORDER BY o.created_at DESC""", (c["id"],))
    addresses = [dict(a) for a in db.all(req.db, "SELECT * FROM addresses WHERE customer_id=? ORDER BY is_default DESC", (c["id"],))]
    for a in addresses:
        a["phone_shown"] = phone(req, a["receiver_phone"])
        if req.user["role"] != "admin":
            a["street"] = "•••"
    reviews = db.all(req.db, """SELECT r.*, p.name product FROM reviews r JOIN products p ON p.id=r.product_id
                                WHERE r.customer_id=? ORDER BY r.created_at DESC""", (c["id"],))
    return req.render("admin/customer.html", active="khach-hang", c=c, orders=orders, addresses=addresses, reviews=reviews,
                      status_vi=STATUS_VI)
