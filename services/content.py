"""Tin tức và các trang thông tin / chính sách."""
import re
from core import db
from services import products

WARRANTY_MONTHS = {"phone": 12, "accessory": 12}


def read_minutes(html):
    words = len(re.sub(r"<[^>]+>", " ", html or "").split())
    return max(1, round(words / 220))


def post_list(conn):
    rows = [dict(r) for r in db.all(conn, "SELECT * FROM posts WHERE is_published=1 ORDER BY published_at DESC")]
    for r in rows:
        r["minutes"] = read_minutes(r["content"])
    return rows


def post_detail(conn, slug):
    p = db.one(conn, "SELECT * FROM posts WHERE slug=? AND is_published=1", (slug,))
    if not p:
        return None
    p = dict(p)
    p["minutes"] = read_minutes(p["content"])
    slugs = list(dict.fromkeys(re.findall(r'href="/(?:dien-thoai|phu-kien)/([a-z0-9-]+)"', p["content"] or "")))
    items = []
    if slugs:
        q = ",".join("?" * len(slugs))
        found = {r["slug"]: r for r in products.cards(conn, f"AND p.slug IN ({q})", slugs, limit=len(slugs))}
        items = [found[s] for s in slugs if s in found][:8]
    others = [dict(r) for r in db.all(conn, """SELECT * FROM posts WHERE is_published=1 AND id<>? ORDER BY published_at DESC LIMIT 3""", (p["id"],))]
    return p, items, others


def warranty_lookup(conn, order):
    """Hạn bảo hành từng sản phẩm, tính từ ngày giao thành công."""
    from datetime import datetime
    delivered = db.scalar(conn, "SELECT MIN(changed_at) FROM order_status_history WHERE order_id=? AND to_status='delivered'", (order["id"],))
    rows = []
    for it in db.all(conn, """SELECT oi.*, c.kind FROM order_items oi JOIN product_variants v ON v.id=oi.variant_id
                              JOIN products p ON p.id=v.product_id JOIN categories c ON c.id=p.category_id WHERE oi.order_id=?""", (order["id"],)):
        r = dict(it)
        r["months"] = WARRANTY_MONTHS[r["kind"]]
        if delivered:
            d = datetime.fromisoformat(delivered)
            m = d.month - 1 + r["months"]
            y, m = d.year + m // 12, m % 12 + 1
            end = d.replace(year=y, month=m, day=min(d.day, 28))
            r["start"], r["end"] = d, end
            r["active"] = datetime.now() <= end
            r["days_left"] = (end - datetime.now()).days
        rows.append(r)
    return delivered, rows
