"""Giá phải trả của từng phiên bản (SKU).

Quy tắc "một giá rõ ràng": nếu SKU đang trong đợt Giá sốc còn suất thì giá phải trả là giá sốc,
ngược lại là giá bán. Giỏ hàng và đơn hàng (Giai đoạn 3) cũng dùng đúng hàm này.
"""
from datetime import datetime
from core import db


def active_promos(conn):
    """{variant_id: {"promo_price", "quota", "sold", "ends_at"}} của đợt giá sốc đang chạy và còn suất."""
    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    rows = db.all(conn, """SELECT pi.variant_id, pi.promo_price, pi.quota, pi.sold, p.ends_at
                           FROM promotion_items pi JOIN promotions p ON p.id=pi.promotion_id
                           WHERE p.is_active=1 AND p.starts_at<=? AND p.ends_at>=? AND pi.sold<pi.quota""", (now, now))
    return {r["variant_id"]: dict(r) for r in rows}


def variants_of(conn, product_ids, promos=None):
    """Mọi phiên bản đang bán của các sản phẩm, kèm tồn kho có thể bán và giá phải trả."""
    if not product_ids:
        return {}
    promos = active_promos(conn) if promos is None else promos
    q = ",".join("?" * len(product_ids))
    out = {}
    for r in db.all(conn, f"""SELECT v.*, COALESCE(i.on_hand-i.reserved,0) AS available
                              FROM product_variants v LEFT JOIN inventory i ON i.variant_id=v.id
                              WHERE v.product_id IN ({q}) AND v.is_active=1 ORDER BY v.id""", list(product_ids)):
        v = dict(r)
        pr = promos.get(v["id"])
        v["is_promo"] = bool(pr)
        v["price"] = pr["promo_price"] if pr else v["sale_price"]
        v["promo_left"] = (pr["quota"] - pr["sold"]) if pr else None
        v["discount_pct"] = round((1 - v["price"] / v["list_price"]) * 100) if v["list_price"] > v["price"] else 0
        out.setdefault(v["product_id"], []).append(v)
    return out
