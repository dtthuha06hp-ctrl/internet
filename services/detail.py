"""Dữ liệu cho trang chi tiết sản phẩm."""
import re
from core import db
from services import pricing, products

NEED_LABEL = {"cam": "Chụp ảnh đẹp", "game": "Chơi game mượt", "pin": "Pin trâu", "slim": "Mỏng nhẹ"}


def get(conn, kind, slug):
    p = db.one(conn, """SELECT p.*, c.kind, c.name AS cat_name, c.slug AS cat_slug, b.name AS brand, b.slug AS brand_slug
                        FROM products p JOIN categories c ON c.id=p.category_id JOIN brands b ON b.id=p.brand_id
                        WHERE p.slug=? AND p.is_active=1""", (slug,))
    if not p or p["kind"] != kind:
        return None
    p = dict(p)
    pid = p["id"]
    variants = pricing.variants_of(conn, [pid]).get(pid, [])
    if not variants:
        return None
    images = db.all(conn, "SELECT * FROM product_images WHERE product_id=? ORDER BY sort_order", (pid,))
    color_img = {}
    for im in images:
        if im["variant_id"]:
            c = db.scalar(conn, "SELECT color_name FROM product_variants WHERE id=?", (im["variant_id"],))
            color_img.setdefault(c, im["url"])
    split = {st for st in {v["storage"] for v in variants}
             if len({v["ram"] for v in variants if v["storage"] == st}) > 1}
    for v in variants:
        v["_ram_split"] = v["storage"] in split
        v["image"] = color_img.get(v["color_name"]) or (images[0]["url"] if images else "")
        v["label"] = " · ".join(x for x in (v["storage"], v["ram"] and f"RAM {v['ram']}", v["color_name"]) if x)
        v["option"] = _option_key(v)

    # nhóm lựa chọn dung lượng (theo bộ nhớ + RAM nếu cùng bộ nhớ có nhiều RAM)
    options = []
    for v in variants:
        if v["option"] and v["option"] not in [o["key"] for o in options]:
            same = [x for x in variants if x["option"] == v["option"]]
            avail = [x for x in same if x["available"] > 0]
            options.append({"key": v["option"], "label": v["option"],
                            "price": min(x["price"] for x in (avail or same)), "in_stock": bool(avail)})
    colors = []
    for v in variants:
        if v["color_name"] not in [c["name"] for c in colors]:
            colors.append({"name": v["color_name"], "hex": v["color_hex"], "image": v["image"]})

    specs = db.all(conn, "SELECT spec_group, spec_name, spec_value FROM product_specs WHERE product_id=? ORDER BY sort_order, id", (pid,))
    groups = []
    for s in specs:
        if not groups or groups[-1]["name"] != s["spec_group"]:
            groups.append({"name": s["spec_group"], "rows": []})
        groups[-1]["rows"].append((s["spec_name"], s["spec_value"]))
    spec_map = {s["spec_name"]: s["spec_value"] for s in specs}

    reviews = [dict(r) for r in db.all(conn, """SELECT r.*, c.full_name, c.title FROM reviews r JOIN customers c ON c.id=r.customer_id
                                                WHERE r.product_id=? AND r.status='approved' ORDER BY r.created_at DESC""", (pid,))]
    for r in reviews:
        parts = r["full_name"].split()
        r["display_name"] = f"{r['title']} {parts[-1]}" if parts else "Khách hàng"
    dist = {k: 0 for k in range(5, 0, -1)}
    for r in reviews:
        dist[r["rating"]] += 1
    n = len(reviews)
    rating = {"avg": round(sum(r["rating"] for r in reviews) / n, 1) if n else 0, "count": n,
              "dist": [(k, dist[k], round(dist[k] / n * 100) if n else 0) for k in dist]}

    if kind == "phone":
        related = products.cards(conn, "AND p.id IN (SELECT accessory_id FROM accessory_compat WHERE phone_id=?)", (pid,),
                                 order="p.sold_count DESC", limit=8)
        related_title = "Phụ kiện dùng được cho máy này"
        compat_phones = []
    else:
        related = []
        related_title = ""
        compat_phones = db.all(conn, """SELECT p.name, p.slug FROM accessory_compat a JOIN products p ON p.id=a.phone_id
                                        WHERE a.accessory_id=? AND p.is_active=1 ORDER BY p.name""", (pid,))

    base_price = min(v["price"] for v in variants)
    similar = [c for c in products.cards(conn, "AND c.kind=? AND p.id<>?", (kind, pid), order="p.sold_count DESC", limit=None)
               if abs(c["price"] - base_price) <= base_price * 0.25 and c["in_stock"]][:5]
    if len(similar) < 5:
        extra = [c for c in products.cards(conn, "AND c.kind=? AND p.id<>?", (kind, pid), order="p.sold_count DESC", limit=20)
                 if c["id"] not in {s["id"] for s in similar}]
        similar += extra[: 5 - len(similar)]

    p.update(variants=variants, options=options, colors=colors, spec_groups=groups, spec_map=spec_map,
             reviews=reviews, rating=rating, related=related, related_title=related_title, compat_phones=compat_phones,
             similar=similar, images=[dict(i) for i in images], faq=faq(p, spec_map), highlights=highlights(p, spec_map),
             main_image=images[0]["url"] if images else "", needs_labels=[NEED_LABEL[x] for x in (p["needs"] or "").split(",") if x in NEED_LABEL])
    return p


def _option_key(v):
    if not v["storage"]:
        return ""
    return v["storage"] if not v.get("_ram_split") else f"{v['storage']} · RAM {v['ram']}"


def pick(p, sku):
    """Phiên bản được chọn: theo ?sku=, nếu không có thì bản còn hàng rẻ nhất."""
    vs = p["variants"]
    if sku:
        for v in vs:
            if v["sku"].lower() == sku.lower():
                return v
    avail = [v for v in vs if v["available"] > 0]
    return min(avail or vs, key=lambda v: (v["price"], v["id"]))


def stock_state(v):
    a = v["available"]
    if a <= 0:
        return ("out", "Tạm hết hàng")
    if a <= 5:
        return ("low", f"Sắp hết – còn {a} sản phẩm")
    return ("ok", "Còn hàng")


def highlights(p, s):
    """Đoạn mô tả ngắn theo từng phần, viết từ thông số (thay cho bài viết dài)."""
    if p["kind"] != "phone":
        return [("Tổng quan", p["description"] or "")] + [(k, v) for k, v in s.items() if k != "Bảo hành"]
    out = [("Tổng quan", p["description"] or p["short_desc"] or "")]
    if "Kích thước màn hình" in s:
        out.append(("Màn hình", f"Màn hình {s.get('Công nghệ màn hình', '')} {s['Kích thước màn hình']}, tần số quét {s.get('Tần số quét', '')} "
                                f"cho thao tác cuộn và chơi game {'rất mượt' if _n(s.get('Tần số quét')) >= 120 else 'ổn định'}."))
    if "Chip xử lý" in s:
        out.append(("Hiệu năng", f"Chip {s['Chip xử lý']}, RAM {s.get('RAM', '')}, bộ nhớ {s.get('Bộ nhớ trong', '')}."))
    if "Camera sau" in s:
        out.append(("Camera", f"Camera sau {s['Camera sau']}, camera trước {s.get('Camera trước', '')}."))
    if "Dung lượng pin" in s:
        out.append(("Pin và sạc", f"Pin {s['Dung lượng pin']}, sạc nhanh {s.get('Sạc nhanh', '')}. "
                                  f"{'Dùng thoải mái hơn một ngày.' if _n(s['Dung lượng pin']) >= 5000 else 'Đủ dùng trọn một ngày với nhu cầu thông thường.'}"))
    return out


def faq(p, s):
    if p["kind"] == "phone":
        return [
            ("Máy có kèm củ sạc trong hộp không?",
             "Phần lớn điện thoại mới chỉ kèm cáp sạc. Bạn có thể chọn củ sạc phù hợp ở mục phụ kiện bên dưới."),
            ("Có hỗ trợ trả góp 0% không?",
             "Có. Với đơn từ 3 triệu, bạn trả góp 0% qua thẻ tín dụng kỳ hạn 6 hoặc 12 tháng (mô phỏng)."),
            ("Máy được bảo hành bao lâu?",
             "12 tháng chính hãng. Lỗi phần cứng do nhà sản xuất trong 30 ngày đầu được đổi máy mới."),
            (f"Máy có {s.get('Mạng di động', '4G')} không?",
             f"Máy hỗ trợ mạng {s.get('Mạng di động', '4G')}."),
            ("Giá trên trang đã gồm VAT chưa?",
             "Đã gồm VAT. Giá hiển thị là giá bạn trả, phí giao hàng (nếu có) hiện rõ ở giỏ hàng trước khi đặt."),
        ]
    return [
        ("Phụ kiện này dùng được cho máy nào?", "Xem danh sách \"Dùng được cho\" ngay bên dưới phần chọn màu."),
        ("Phụ kiện có được bảo hành không?", "Có, bảo hành 12 tháng, 1 đổi 1 trong 30 ngày nếu lỗi nhà sản xuất."),
        ("Mua kèm điện thoại có được giảm thêm không?", "Nhập mã PHUKIEN10 ở giỏ hàng để giảm 10% (tối đa 200.000₫) cho đơn từ 300.000₫."),
    ]


def _n(s):
    m = re.search(r"(\d+)", s or "")
    return int(m.group(1)) if m else 0
