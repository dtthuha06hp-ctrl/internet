"""So sánh sản phẩm (/so-sanh) và Chọn máy theo nhu cầu (/chon-may)."""
import re
from core.router import route
from services import products, catalog

BUDGETS = [("duoi-5", "Dưới 5 triệu", 0, 5e6), ("5-10", "5 – 10 triệu", 5e6, 10e6),
           ("10-20", "10 – 20 triệu", 10e6, 20e6), ("tren-20", "Trên 20 triệu", 20e6, 1e13)]
OSES = [("ios", "iPhone (iOS)"), ("android", "Android"), ("any", "Sao cũng được")]


@route("/so-sanh")
def compare(req):
    ids = []
    for x in (req.query.get("ids") or "").split(","):
        if x.strip().isdigit() and int(x) not in ids:
            ids.append(int(x))
    ids = ids[:3]
    items = products.cards(req.db, f"AND c.kind='phone' AND p.id IN ({','.join('?' * len(ids))})", ids, limit=3) if ids else []
    items.sort(key=lambda p: ids.index(p["id"]))
    for p in items:
        others = [i for i in ids if i != p["id"]]
        p["remove_url"] = "/so-sanh?ids=" + ",".join(map(str, others)) if others else "/so-sanh"
    rows = []
    if items:
        from core import db
        order = []
        for r in db.all(req.db, f"""SELECT spec_group, spec_name, MIN(sort_order) so FROM product_specs
                                    WHERE product_id IN ({','.join('?' * len(ids))}) GROUP BY spec_group, spec_name
                                    ORDER BY MIN(sort_order)""", ids):
            order.append((r["spec_group"], r["spec_name"]))
        rank = {}
        for g, _n in order:
            rank.setdefault(g, len(rank))
        order.sort(key=lambda gn: rank[gn[0]])  # gom các dòng cùng nhóm lại với nhau
        rows.append({"group": "Giá & đánh giá", "name": "Giá phải trả", "values": [products_price(p) for p in items], "diff": True})
        rows.append({"group": "Giá & đánh giá", "name": "Đánh giá", "values": [f"{p['rating_avg']:.1f} ★ ({p['rating_count']})".replace(".", ",") if p["rating_count"] else "Chưa có" for p in items], "diff": True})
        rows.append({"group": "Giá & đánh giá", "name": "Đã bán", "values": [f"{p['sold_count']:,}".replace(",", ".") for p in items], "diff": True})
        for g, n in order:
            vals = [p["spec_map"].get(n, "—") for p in items]
            rows.append({"group": g, "name": n, "values": vals, "diff": len(set(vals)) > 1})
        rows.append({"group": "Phiên bản", "name": "Dung lượng", "values": [" / ".join(p["storages"]) for p in items], "diff": True})
        rows.append({"group": "Phiên bản", "name": "Màu sắc", "values": [len(p["colors"]) for p in items], "diff": True})
        best = _winners(items)
        for r in rows:
            r["best"] = best.get(r["name"])
    pickable = products.cards(req.db, "AND c.kind='phone'", order="p.name", limit=None)
    return req.render("shop/compare.html", items=items, rows=rows, ids=ids,
                      pickable=[{"id": p["id"], "name": p["name"], "price": p["price"]} for p in pickable if p["id"] not in ids])


def products_price(p):
    from core.template import vnd
    return vnd(p["price"])


def _num(s):
    m = re.search(r"(\d+(?:\.\d+)?)", str(s or ""))
    return float(m.group(1)) if m else None


def _winners(items):
    """Đánh dấu ô "tốt nhất" ở vài hàng dễ so sánh bằng số."""
    if len(items) < 2:
        return {}
    out = {}
    rules = {"Dung lượng pin": max, "Sạc nhanh": max, "Tần số quét": max, "Trọng lượng": min}
    for name, fn in rules.items():
        vals = [_num(p["spec_map"].get(name)) for p in items]
        if all(v is not None for v in vals) and len(set(vals)) > 1:
            out[name] = vals.index(fn(vals))
    prices = [p["price"] for p in items]
    if len(set(prices)) > 1:
        out["Giá phải trả"] = prices.index(min(prices))
    return out


@route("/chon-may")
def finder(req):
    b = req.query.get("ngan-sach")
    need = req.query.get("nhu-cau")
    os_ = req.query.get("he-dieu-hanh")
    done = b in dict((k, l) for k, l, *_ in BUDGETS) and need in dict(catalog.NEEDS) and os_ in dict(OSES)
    results = []
    if done:
        lo, hi = next((lo, hi) for k, _l, lo, hi in BUDGETS if k == b)
        mid = (lo + min(hi, 4e7)) / 2
        cands = [p for p in products.cards(req.db, "AND c.kind='phone'", limit=None) if p["in_stock"]]
        if os_ != "any":
            cands = [p for p in cands if (p["brand_slug"] == "apple") == (os_ == "ios")]
        for p in cands:
            score, why = 0, []
            if lo <= p["price"] < hi:
                score += 100
                why.append(f"Nằm trong ngân sách {next(lbl for k, lbl, *_ in BUDGETS if k == b)}")
            else:
                score -= abs(p["price"] - mid) / 1e6 * 4
                why.append("Gần với ngân sách của bạn nhất")
            if need in p["needs_list"]:
                score += 40
                why.append(_need_reason(need, p))
            score += min(p["sold_count"], 300) / 30 + p["rating_avg"]
            p["score"], p["why"] = score, why
        cands.sort(key=lambda p: -p["score"])
        results = cands[:3]
        for p in results:
            if len(p["why"]) < 3:
                p["why"].append(f"Đã bán {p['sold_count']:,} máy".replace(",", "."))
    return req.render("shop/finder.html", budgets=BUDGETS, needs=catalog.NEEDS, oses=OSES,
                      b=b, need=need, os_=os_, done=done, results=results)


def _need_reason(need, p):
    s = p["spec_map"]
    return {
        "cam": f"Camera sau {s.get('Camera sau', '')}",
        "game": f"Chip {s.get('Chip xử lý', '')}, màn {s.get('Tần số quét', '')}",
        "pin": f"Pin {s.get('Dung lượng pin', '')}, sạc {s.get('Sạc nhanh', '')}",
        "slim": f"Nặng chỉ {s.get('Trọng lượng', '')}",
    }.get(need, "")
