"""Truy vấn sản phẩm cho các trang người mua."""
import unicodedata
from core import db


def norm(s):
    """Bỏ dấu tiếng Việt + chữ thường: 'Điện Thoại' -> 'dien thoai'."""
    s = (s or "").replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower().strip()


_CARD_SQL = """
SELECT p.id, p.name, p.slug, p.short_desc, p.is_new, p.is_featured, p.rating_avg, p.rating_count, p.sold_count,
       p.needs, p.created_at, c.kind, c.slug AS cat_slug, c.name AS cat_name, b.name AS brand, b.slug AS brand_slug,
       (SELECT MIN(v.sale_price) FROM product_variants v JOIN inventory i ON i.variant_id=v.id
          WHERE v.product_id=p.id AND v.is_active=1 AND i.on_hand-i.reserved>0) AS price_in_stock,
       (SELECT MIN(v.sale_price) FROM product_variants v WHERE v.product_id=p.id AND v.is_active=1) AS price_any,
       (SELECT COALESCE(SUM(i.on_hand-i.reserved),0) FROM product_variants v JOIN inventory i ON i.variant_id=v.id
          WHERE v.product_id=p.id AND v.is_active=1) AS stock,
       (SELECT url FROM product_images im WHERE im.product_id=p.id ORDER BY im.is_main DESC, im.sort_order LIMIT 1) AS image
FROM products p JOIN categories c ON c.id=p.category_id JOIN brands b ON b.id=p.brand_id
WHERE p.is_active=1 {where}
ORDER BY {order}
LIMIT {limit}
"""

KEY_SPECS = ("Kích thước màn hình", "Chip xử lý", "Dung lượng pin")


def cards(conn, where="", params=(), order="p.sold_count DESC", limit=20):
    """limit=None: lấy tất cả (SQLite hiểu LIMIT -1 là không giới hạn)."""
    rows = [dict(r) for r in db.all(conn, _CARD_SQL.format(where=where, order=order, limit=-1 if limit is None else int(limit)), params)]
    return _decorate(conn, rows)


def _decorate(conn, rows):
    """Bổ sung giá phải trả, màu, thông số chính, RAM/bộ nhớ... cho từng thẻ sản phẩm."""
    if not rows:
        return rows
    from services import pricing
    ids = [r["id"] for r in rows]
    q = ",".join("?" * len(ids))
    specs = {}
    for r in db.all(conn, f"SELECT product_id, spec_name, spec_value FROM product_specs WHERE product_id IN ({q}) ORDER BY sort_order", ids):
        specs.setdefault(r["product_id"], []).append((r["spec_name"], r["spec_value"]))
    variants = pricing.variants_of(conn, ids)
    for r in rows:
        vs = variants.get(r["id"], [])
        avail = [v for v in vs if v["available"] > 0]
        best = min(avail or vs, key=lambda v: (v["price"], v["id"])) if vs else None
        r["price"] = best["price"] if best else 0
        r["list_price"] = best["list_price"] if best else 0
        r["discount_pct"] = best["discount_pct"] if best else 0
        r["is_promo"] = bool(best and best["is_promo"])
        r["colors"] = list(dict.fromkeys(v["color_hex"] for v in vs if v["color_hex"]))[:5]
        r["rams"] = sorted({v["ram"] for v in vs if v["ram"]}, key=_gb)
        r["storages"] = sorted({v["storage"] for v in vs if v["storage"]}, key=_gb)
        sp = specs.get(r["id"], [])
        r["spec_map"] = dict(sp)
        if r["kind"] == "phone":
            r["specs"] = [r["spec_map"][k] for k in KEY_SPECS if k in r["spec_map"]]
        else:
            r["specs"] = [v for n, v in sp[:2]]
        r["needs_list"] = [x for x in (r.get("needs") or "").split(",") if x]
        r["stock"] = sum(v["available"] for v in vs)
        r["in_stock"] = r["stock"] > 0
        r["url"] = ("/dien-thoai/" if r["kind"] == "phone" else "/phu-kien/") + r["slug"]
    return rows


def _gb(s):
    """'1TB' -> 1024, '256GB' -> 256: để sắp xếp dung lượng đúng thứ tự."""
    import re
    m = re.match(r"(\d+)\s*(TB|GB)", s or "")
    return int(m.group(1)) * (1024 if m.group(2) == "TB" else 1) if m else 0


def flash_sale(conn):
    """Chương trình giá sốc đang chạy (nếu có) cùng các sản phẩm."""
    from core.session import now
    prom = db.one(conn, "SELECT * FROM promotions WHERE is_active=1 AND starts_at<=? AND ends_at>=? ORDER BY ends_at LIMIT 1",
                  (now().replace("T", " "), now().replace("T", " ")))
    if not prom:
        return None, []
    items = db.all(conn, """SELECT pi.*, v.product_id, v.list_price, v.sale_price, v.storage, v.color_name
                             FROM promotion_items pi JOIN product_variants v ON v.id=pi.variant_id WHERE pi.promotion_id=?""",
                   (prom["id"],))
    by_pid = {i["product_id"]: dict(i) for i in items}
    rows = cards(conn, f"AND p.id IN ({','.join('?' * len(by_pid))})", list(by_pid), "p.id", 10) if by_pid else []
    for r in rows:
        it = by_pid[r["id"]]
        r["price"] = it["promo_price"]
        r["list_price"] = it["list_price"]
        r["discount_pct"] = round((1 - it["promo_price"] / it["list_price"]) * 100)
        r["variant_label"] = " · ".join(x for x in (it["storage"], it["color_name"]) if x)
        r["quota"], r["sold_flash"] = it["quota"], it["sold"]
        r["sold_pct"] = round(it["sold"] / it["quota"] * 100)
    return dict(prom), rows


def price_ranges(conn):
    ranges = [("Dưới 5 triệu", 0, 5_000_000, "0-5"), ("5 – 10 triệu", 5_000_000, 10_000_000, "5-10"),
              ("10 – 20 triệu", 10_000_000, 20_000_000, "10-20"), ("Trên 20 triệu", 20_000_000, 10**12, "20-")]
    out = []
    for label, lo, hi, key in ranges:
        n = db.scalar(conn, """SELECT COUNT(*) FROM products p JOIN categories c ON c.id=p.category_id
            WHERE p.is_active=1 AND c.kind='phone'
              AND (SELECT MIN(sale_price) FROM product_variants v WHERE v.product_id=p.id AND v.is_active=1) >= ?
              AND (SELECT MIN(sale_price) FROM product_variants v WHERE v.product_id=p.id AND v.is_active=1) < ?""", (lo, hi))
        out.append({"label": label, "count": n, "key": key})
    return out


def suggest(conn, q, limit=6):
    """Gợi ý tìm kiếm, không phân biệt dấu và hoa thường."""
    nq = norm(q)
    if len(nq) < 2:
        return []
    words = nq.split()
    rows = cards(conn, limit=None)   # xét mọi sản phẩm (lỗi B6)
    hits = []
    for r in rows:
        hay = norm(f"{r['name']} {r['brand']} {r['cat_name']} {'dien thoai' if r['kind'] == 'phone' else 'phu kien'}")
        if all(w in hay for w in words):
            score = (0 if norm(r["name"]).startswith(nq) else 1, -r["sold_count"])
            hits.append((score, r))
    hits.sort(key=lambda x: x[0])
    return [h[1] for h in hits[:limit]]
