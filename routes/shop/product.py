"""Trang chi tiết sản phẩm: /dien-thoai/<slug> và /phu-kien/<slug>."""
from core.router import route
from core.server import HttpError
from services import detail


def _view(req, kind, slug):
    p = detail.get(req.db, kind, slug)
    if not p:
        raise HttpError(404, "Sản phẩm không tồn tại hoặc đã ngừng kinh doanh.")
    v = detail.pick(p, req.query.get("sku"))
    state, state_label = detail.stock_state(v)
    js = {
        "id": p["id"], "name": p["name"], "kind": kind, "url": req.path,
        "variants": [{k: x[k] for k in ("id", "sku", "option", "color_name", "color_hex", "price", "list_price",
                                        "discount_pct", "is_promo", "promo_left", "available", "image", "label")}
                     for x in p["variants"]],
    }
    from services import accounts, reviews
    me = accounts.customer_of(req.db, req.user) if req.user and req.user["role"] == "customer" else None
    in_wish = accounts.in_wishlist(req.db, me["id"], p["id"]) if me else False
    review_order = next((t["order_code"] for t in reviews.pending_to_write(req.db, me["id"]) if t["product_id"] == p["id"]), "") if me else ""
    base = "/dien-thoai" if kind == "phone" else "/phu-kien"
    return req.render("shop/product.html", in_wish=in_wish, review_order=review_order, p=p, v=v, state=state, state_label=state_label, js=js, base=base,
                      section="Điện thoại" if kind == "phone" else "Phụ kiện",
                      installment=round(v["price"] / 12 / 1000) * 1000 if v["price"] >= 3_000_000 else 0)


@route("/dien-thoai/<slug>")
def phone(req, slug):
    return _view(req, "phone", slug)


@route("/phu-kien/<slug>")
def accessory(req, slug):
    return _view(req, "accessory", slug)
