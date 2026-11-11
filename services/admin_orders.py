"""Xử lý đơn hàng phía quản trị: chuyển trạng thái đúng quy trình, mỗi bước kéo theo đúng thay đổi về kho và thanh toán."""
from core import db
from core.template import vnd
import config
from services import inventory, orders
from services.orders import OrderError, STATUS_VI, now

# (trạng thái hiện tại) -> [(trạng thái mới, nhãn nút, kiểu nút)]
TRANSITIONS = {
    "pending": [("confirmed", "Xác nhận đơn", "primary")],
    "confirmed": [("preparing", "Bắt đầu đóng gói", "primary")],
    "preparing": [("shipping", "Bàn giao vận chuyển", "primary"), ("delivered", "Khách đã nhận tại cửa hàng", "primary")],
    "shipping": [("delivered", "Giao thành công", "primary"), ("delivery_failed", "Giao thất bại", "ghost")],
    "delivery_failed": [("shipping", "Giao lại", "primary")],
    "delivered": [("completed", "Hoàn tất (hết hạn đổi trả)", "primary"), ("returning", "Khách yêu cầu đổi / trả", "ghost")],
    "returning": [("refunded", "Đã nhận lại hàng, hoàn tiền", "danger"), ("completed", "Đổi xong, hoàn tất", "primary")],
}
CANCELLABLE = ("pending", "confirmed", "preparing", "delivery_failed")
NOTES = {"confirmed": "Đã gọi xác nhận với khách", "preparing": "Đang đóng gói", "shipping": "Đã bàn giao cho đơn vị vận chuyển",
         "delivered": "Khách đã nhận hàng", "delivery_failed": "Giao hàng không thành công", "completed": "Đơn hàng hoàn tất",
         "returning": "Khách yêu cầu đổi / trả", "refunded": "Đã nhận lại hàng và hoàn tiền"}
CARRIERS = ["GHN", "GHTK", "Viettel Post", "J&T Express", "Shop tự giao"]


def actions_for(o):
    acts = []
    for to, label, kind in TRANSITIONS.get(o["status"], []):
        if o["status"] == "preparing":
            if to == "shipping" and o["delivery_method"] == "store":
                continue
            if to == "delivered" and o["delivery_method"] == "home":
                continue
        acts.append({"to": to, "label": label, "kind": kind})
    return acts


def change_status(conn, order_id, to, user, note="", carrier="", tracking=""):
    with db.transaction(conn):
        o = db.one(conn, "SELECT * FROM orders WHERE id=?", (order_id,))
        if not o:
            raise OrderError("Không tìm thấy đơn hàng.")
        if to not in [a["to"] for a in actions_for(o)]:
            raise OrderError(f"Không thể chuyển từ \"{STATUS_VI[o['status']]}\" sang \"{STATUS_VI.get(to, to)}\". "
                             "Đơn chỉ được đi theo đúng quy trình.")
        t = now()
        items = db.all(conn, "SELECT variant_id, quantity FROM order_items WHERE order_id=?", (order_id,))
        pay_status = o["payment_status"]

        if to == "shipping":
            if not carrier:
                raise OrderError("Vui lòng chọn đơn vị vận chuyển.")
            if db.scalar(conn, "SELECT 1 FROM shipments WHERE order_id=?", (order_id,)):
                conn.execute("UPDATE shipments SET carrier=?, tracking_code=?, shipped_at=? WHERE order_id=?",
                             (carrier, tracking or None, t, order_id))
            else:
                conn.execute("INSERT INTO shipments(order_id,carrier,tracking_code,shipped_at) VALUES(?,?,?,?)",
                             (order_id, carrier, tracking or None, t))
            note = note or f"Bàn giao {carrier}" + (f", mã vận đơn {tracking}" if tracking else "")
        elif to == "delivered":
            for it in items:   # hàng rời kho: trừ tồn thực và số đang giữ
                inventory.move(conn, it["variant_id"], "sale", it["quantity"], "Xuất bán đơn " + o["order_code"], order_id, user["id"])
                conn.execute("UPDATE products SET sold_count=sold_count+? WHERE id=(SELECT product_id FROM product_variants WHERE id=?)",
                             (it["quantity"], it["variant_id"]))
            conn.execute("UPDATE shipments SET delivered_at=? WHERE order_id=?", (t, order_id))
            if o["payment_method"] == "cod" and pay_status != "paid":
                conn.execute("UPDATE payments SET status='paid', paid_at=? WHERE order_id=? AND status='pending'", (t, order_id))
                pay_status = "paid"
        elif to == "completed":
            conn.execute("UPDATE customers SET total_spent=total_spent+? WHERE id=?", (o["total"], o["customer_id"]))
        elif to == "refunded":
            for it in items:
                inventory.move(conn, it["variant_id"], "return", it["quantity"], "Nhận lại hàng đơn " + o["order_code"], order_id, user["id"])
                conn.execute("UPDATE products SET sold_count=MAX(sold_count-?,0) WHERE id=(SELECT product_id FROM product_variants WHERE id=?)",
                             (it["quantity"], it["variant_id"]))
            conn.execute("UPDATE payments SET status='refunded' WHERE order_id=? AND status='paid'", (order_id,))
            pay_status = "refunded" if pay_status == "paid" else pay_status

        conn.execute("UPDATE orders SET status=?, payment_status=?, updated_at=? WHERE id=?", (to, pay_status, t, order_id))
        conn.execute("INSERT INTO order_status_history(order_id,from_status,to_status,note,changed_by,changed_at) VALUES(?,?,?,?,?,?)",
                     (order_id, o["status"], to, note or NOTES.get(to, ""), user["id"], t))
        email = db.scalar(conn, "SELECT email FROM customers WHERE id=?", (o["customer_id"],))
        if email:
            extra = ""
            if to == "shipping":
                extra = f"<p>Đơn vị vận chuyển: <b>{carrier}</b>" + (f", mã vận đơn <b>{tracking}</b>" if tracking else "") + ".</p>"
            if to == "refunded":
                extra = f"<p>Số tiền {vnd(o['total'])} sẽ được hoàn trong 3–5 ngày làm việc (mô phỏng).</p>"
            orders.send_mail(conn, email, f"[{config.SHOP_NAME}] Đơn {o['order_code']}: {STATUS_VI[to]}",
                             f"<p>Đơn hàng <b>{o['order_code']}</b> vừa chuyển sang trạng thái <b>{STATUS_VI[to]}</b>.</p>{extra}"
                             "<p>Tra cứu đơn tại mục \"Tra cứu đơn hàng\" trên website.</p>", order_id)


def admin_cancel(conn, order_id, reason, user):
    o = db.one(conn, "SELECT status FROM orders WHERE id=?", (order_id,))
    if not o or o["status"] not in CANCELLABLE:
        raise OrderError("Đơn ở trạng thái này không hủy được.")
    if o["status"] == "delivery_failed":
        # hàng đang trên đường hoàn về: vẫn là "đang giữ", hủy thì nhả giữ
        pass
    orders.cancel(conn, order_id, reason, by_user=user, note_prefix="Cửa hàng hủy")


def save_note(conn, order_id, note):
    conn.execute("UPDATE orders SET internal_note=?, updated_at=? WHERE id=?", ((note or "").strip()[:500] or None, now(), order_id))


def search(conn, status=None, q="", date_from="", date_to="", limit=50, offset=0):
    sql = " FROM orders o JOIN customers c ON c.id=o.customer_id WHERE 1=1"
    args = []
    if status:
        sql += " AND o.status=?"
        args.append(status)
    if q:
        like = f"%{q.strip()}%"
        sql += " AND (o.order_code LIKE ? OR o.receiver_phone LIKE ? OR o.receiver_name LIKE ? OR c.phone LIKE ?)"
        args += [like, like, like, like]
    if date_from:
        sql += " AND date(o.created_at)>=?"
        args.append(date_from)
    if date_to:
        sql += " AND date(o.created_at)<=?"
        args.append(date_to)
    total = db.scalar(conn, "SELECT COUNT(*)" + sql, args)
    rows = [dict(r) for r in db.all(conn, "SELECT o.*, (SELECT COUNT(*) FROM order_items i WHERE i.order_id=o.id) n_items"
                                    + sql + " ORDER BY o.created_at DESC LIMIT ? OFFSET ?", args + [limit, offset])]
    return rows, total
