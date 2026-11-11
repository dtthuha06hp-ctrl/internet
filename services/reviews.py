"""Đánh giá sản phẩm: chỉ khách đã nhận hàng mới được viết, mỗi đơn một đánh giá cho mỗi sản phẩm, chờ admin duyệt."""
from datetime import datetime
from core import db


class ReviewError(Exception):
    pass


def pending_to_write(conn, customer_id):
    """Các sản phẩm trong đơn đã giao mà khách chưa đánh giá."""
    rows = db.all(conn, """SELECT DISTINCT o.id AS order_id, o.order_code, v.product_id, p.name, p.slug, c.kind,
                              (SELECT h.changed_at FROM order_status_history h WHERE h.order_id=o.id AND h.to_status='delivered') delivered_at,
                              (SELECT url FROM product_images im WHERE im.product_id=p.id ORDER BY im.is_main DESC, im.sort_order LIMIT 1) image
                           FROM orders o JOIN order_items oi ON oi.order_id=o.id JOIN product_variants v ON v.id=oi.variant_id
                           JOIN products p ON p.id=v.product_id JOIN categories c ON c.id=p.category_id
                           WHERE o.customer_id=? AND o.status IN ('delivered','completed')
                             AND NOT EXISTS (SELECT 1 FROM reviews r WHERE r.order_id=o.id AND r.product_id=v.product_id)
                           ORDER BY o.created_at DESC""", (customer_id,))
    return [dict(r) for r in rows]


def mine(conn, customer_id):
    return [dict(r) for r in db.all(conn, """SELECT r.*, p.name, p.slug, c.kind, o.order_code,
              (SELECT url FROM product_images im WHERE im.product_id=p.id ORDER BY im.is_main DESC, im.sort_order LIMIT 1) image
              FROM reviews r JOIN products p ON p.id=r.product_id JOIN categories c ON c.id=p.category_id
              JOIN orders o ON o.id=r.order_id WHERE r.customer_id=? ORDER BY r.created_at DESC""", (customer_id,))]


def can_review(conn, customer_id, order_code, product_id):
    """Trả về đơn hàng nếu được phép đánh giá, ngược lại báo lý do."""
    o = db.one(conn, "SELECT * FROM orders WHERE order_code=? AND customer_id=?", (order_code, customer_id))
    if not o:
        raise ReviewError("Không tìm thấy đơn hàng trong tài khoản của bạn.")
    if o["status"] not in ("delivered", "completed"):
        raise ReviewError("Bạn chỉ có thể đánh giá sau khi đã nhận hàng.")
    if not db.scalar(conn, """SELECT 1 FROM order_items oi JOIN product_variants v ON v.id=oi.variant_id
                              WHERE oi.order_id=? AND v.product_id=?""", (o["id"], product_id)):
        raise ReviewError("Sản phẩm này không có trong đơn hàng.")
    if db.scalar(conn, "SELECT 1 FROM reviews WHERE order_id=? AND product_id=?", (o["id"], product_id)):
        raise ReviewError("Bạn đã đánh giá sản phẩm này cho đơn hàng này rồi.")
    return dict(o)


def create(conn, customer_id, order_code, product_id, rating, content):
    try:
        rating = int(rating)
    except (TypeError, ValueError):
        rating = 0
    if not 1 <= rating <= 5:
        raise ReviewError("Vui lòng chọn số sao (1 đến 5).")
    content = (content or "").strip()
    if len(content) < 10:
        raise ReviewError("Hãy viết ít nhất 10 ký tự để người mua sau tham khảo.")
    if len(content) > 1000:
        raise ReviewError("Đánh giá tối đa 1000 ký tự.")
    with db.transaction(conn):
        o = can_review(conn, customer_id, order_code, product_id)
        conn.execute("INSERT INTO reviews(product_id,customer_id,order_id,rating,content,status,created_at) VALUES(?,?,?,?,?,?,?)",
                     (product_id, customer_id, o["id"], rating, content, "pending",
                      datetime.now().isoformat(sep=" ", timespec="seconds")))
