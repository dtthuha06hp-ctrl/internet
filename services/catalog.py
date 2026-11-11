"""Danh mục sản phẩm: bộ lọc, đếm số kết quả từng lựa chọn, sắp xếp, phân trang.

Bộ lọc nằm trên URL (ví dụ /dien-thoai?hang=samsung,apple&gia=5-10&sap-xep=gia-tang)
nên bấm vào sản phẩm rồi quay lại vẫn giữ nguyên (TC-02).
"""
import re
from core import db
from services import products

PER_PAGE = 20

NEEDS = [("cam", "Chụp ảnh đẹp"), ("game", "Chơi game"), ("pin", "Pin trâu"), ("slim", "Mỏng nhẹ")]

PHONE_PRICES = [("0-5", "Dưới 5 triệu", 0, 5e6), ("5-10", "5 – 10 triệu", 5e6, 10e6),
                ("10-20", "10 – 20 triệu", 10e6, 20e6), ("20-", "Trên 20 triệu", 20e6, 1e13)]
ACC_PRICES = [("0-300", "Dưới 300.000₫", 0, 3e5), ("300-1000", "300.000₫ – 1 triệu", 3e5, 1e6),
              ("1000-3000", "1 – 3 triệu", 1e6, 3e6), ("3000-", "Trên 3 triệu", 3e6, 1e13)]

SORTS = [("noi-bat", "Nổi bật"), ("ban-chay", "Bán chạy"), ("gia-tang", "Giá thấp → cao"),
         ("gia-giam", "Giá cao → thấp"), ("moi-nhat", "Mới nhất"), ("giam-nhieu", "Giảm nhiều nhất")]


def _num(s):
    m = re.search(r"(\d+)", s or "")
    return int(m.group(1)) if m else 0


def _feature(p, key):
    sm = p["spec_map"]
    if key == "5g":
        return sm.get("Mạng di động") == "5G"
    if key == "120hz":
        return _num(sm.get("Tần số quét")) >= 120
    if key == "sac-nhanh":
        return _num(sm.get("Sạc nhanh")) >= 45
    return False


def facets_for(kind, items, conn):
    """Danh sách nhóm bộ lọc: (khóa URL, tiêu đề, [(giá trị, nhãn)], hàm kiểm tra, chọn nhiều?)."""
    brands = []
    for p in items:
        if (p["brand_slug"], p["brand"]) not in brands:
            brands.append((p["brand_slug"], p["brand"]))
    order = {r["slug"]: r["sort_order"] for r in db.all(conn, "SELECT slug, sort_order FROM brands")}
    brands.sort(key=lambda b: order.get(b[0], 99))
    if kind == "phone":
        rams = sorted({r for p in items for r in p["rams"]}, key=products._gb)
        stor = sorted({s for p in items for s in p["storages"]}, key=products._gb)
        return [
            ("hang", "Hãng", brands, lambda p, v: p["brand_slug"] == v, True),
            ("gia", "Mức giá", [(k, l) for k, l, *_ in PHONE_PRICES], _price_test(PHONE_PRICES), True),
            ("nhu-cau", "Nhu cầu", NEEDS, lambda p, v: v in p["needs_list"], True),
            ("ram", "RAM", [(r, r) for r in rams], lambda p, v: v in p["rams"], True),
            ("bo-nho", "Bộ nhớ trong", [(s, s) for s in stor], lambda p, v: v in p["storages"], True),
            ("tinh-nang", "Tính năng", [("5g", "Có 5G"), ("120hz", "Màn hình 120Hz trở lên"), ("sac-nhanh", "Sạc nhanh từ 45W")],
             _feature, True),
        ]
    cats = db.all(conn, "SELECT slug, name FROM categories WHERE kind='accessory' AND parent_id IS NOT NULL AND is_active=1 ORDER BY sort_order")
    phones = db.all(conn, """SELECT p.id, p.slug, p.name FROM products p JOIN categories c ON c.id=p.category_id
                             WHERE c.kind='phone' AND p.is_active=1 ORDER BY p.name""")
    compat = {}
    for r in db.all(conn, "SELECT a.accessory_id, p.slug FROM accessory_compat a JOIN products p ON p.id=a.phone_id"):
        compat.setdefault(r["accessory_id"], set()).add(r["slug"])
    return [
        ("loai", "Loại phụ kiện", [(c["slug"], c["name"]) for c in cats], lambda p, v: p["cat_slug"] == v, True),
        ("hang", "Hãng", brands, lambda p, v: p["brand_slug"] == v, True),
        ("gia", "Mức giá", [(k, l) for k, l, *_ in ACC_PRICES], _price_test(ACC_PRICES), True),
        ("dung-cho", "Dùng cho máy", [(p["slug"], p["name"]) for p in phones], lambda p, v: v in compat.get(p["id"], ()), False),
    ]


def _price_test(ranges):
    table = {k: (lo, hi) for k, _l, lo, hi in ranges}

    def test(p, v):
        lo, hi = table.get(v, (None, None))
        return lo is not None and lo <= p["price"] < hi
    return test


def parse(query, facets):
    """Đọc bộ lọc từ URL, bỏ qua giá trị lạ."""
    sel = {}
    for key, _t, opts, _f, multi in facets:
        valid = {o[0] for o in opts}
        vals = [v for v in (query.get(key, "") or "").split(",") if v in valid]
        if not multi:
            vals = vals[:1]
        if vals:
            sel[key] = vals
    return sel


def _match(p, sel, facets, skip=None, price_min=None, price_max=None):
    for key, _t, _o, test, _m in facets:
        if key == skip or key not in sel:
            continue
        if not any(test(p, v) for v in sel[key]):
            return False
    if price_min is not None and p["price"] < price_min:
        return False
    if price_max is not None and p["price"] > price_max:
        return False
    return True


def _sort(items, key):
    if key == "gia-tang":
        items.sort(key=lambda p: (not p["in_stock"], p["price"]))
    elif key == "gia-giam":
        items.sort(key=lambda p: (not p["in_stock"], -p["price"]))
    elif key == "ban-chay":
        items.sort(key=lambda p: (not p["in_stock"], -p["sold_count"]))
    elif key == "moi-nhat":
        items.sort(key=lambda p: (not p["in_stock"], p["created_at"]), reverse=False)
        items.sort(key=lambda p: (not p["in_stock"], -_ts(p["created_at"])))
    elif key == "giam-nhieu":
        items.sort(key=lambda p: (not p["in_stock"], -p["discount_pct"], -p["sold_count"]))
    else:  # nổi bật
        items.sort(key=lambda p: (not p["in_stock"], -p["is_featured"], -p["sold_count"]))


def _ts(s):
    from datetime import datetime
    try:
        return datetime.fromisoformat(s).timestamp()
    except Exception:
        return 0


def _money(s, unit):
    try:
        v = float((s or "").replace(",", "."))
        return v * unit if v >= 0 else None
    except ValueError:
        return None


def browse(conn, kind, query):
    where = "AND c.kind=?"
    items = products.cards(conn, where, (kind,), limit=1000)
    facets = facets_for(kind, items, conn)
    sel = parse(query, facets)
    unit = 1e6 if kind == "phone" else 1e3
    pmin, pmax = _money(query.get("tu"), unit), _money(query.get("den"), unit)
    sort = query.get("sap-xep") if query.get("sap-xep") in dict(SORTS) else "noi-bat"
    try:
        page = max(1, min(50, int(query.get("trang", 1))))
    except ValueError:
        page = 1

    result = [p for p in items if _match(p, sel, facets, price_min=pmin, price_max=pmax)]
    _sort(result, sort)

    groups = []
    for key, title, opts, test, multi in facets:
        base = [p for p in items if _match(p, sel, facets, skip=key, price_min=pmin, price_max=pmax)]
        options = []
        for val, label in opts:
            n = sum(1 for p in base if test(p, val))
            on = val in sel.get(key, [])
            if n or on:
                options.append({"value": val, "label": label, "count": n, "on": on})
        if options:
            groups.append({"key": key, "title": title, "multi": multi, "options": options})

    chips = []
    for g in groups:
        for o in g["options"]:
            if o["on"]:
                chips.append({"label": o["label"], "url": _url_without(query, g["key"], o["value"])})
    if pmin is not None or pmax is not None:
        u = "triệu" if kind == "phone" else "nghìn"
        lbl = f"Giá {query.get('tu') or 0} – {query.get('den') or '…'} {u}"
        chips.append({"label": lbl, "url": _url_without(query, "tu", None, also="den")})

    return {
        "items": result[: page * PER_PAGE], "total": len(result), "page": page,
        "has_more": len(result) > page * PER_PAGE, "remaining": max(0, len(result) - page * PER_PAGE),
        "groups": groups, "chips": chips, "sort": sort, "sorts": SORTS, "sel": sel,
        "tu": query.get("tu", ""), "den": query.get("den", ""),
    }


def _url_without(query, key, value, also=None):
    from urllib.parse import urlencode
    q = {k: v for k, v in query.items() if k not in ("trang", "partial")}
    if value is None:
        q.pop(key, None)
    else:
        vals = [v for v in q.get(key, "").split(",") if v and v != value]
        if vals:
            q[key] = ",".join(vals)
        else:
            q.pop(key, None)
    if also:
        q.pop(also, None)
    s = urlencode(q)
    return "?" + s if s else "?"
