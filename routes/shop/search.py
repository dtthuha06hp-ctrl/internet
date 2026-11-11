"""Tìm kiếm và gợi ý khi gõ."""
from core.router import route
from core.server import json_response
from services import products


@route("/api/goi-y")
def api_suggest(req):
    items = products.suggest(req.db, req.query.get("q", ""), limit=6)
    return json_response([{"name": p["name"], "price": p["price"], "image": p["image"], "url": p["url"]} for p in items])


@route("/tim-kiem")
def search(req):
    q = req.query.get("q", "").strip()[:100]
    items = products.suggest(req.db, q, limit=60) if q else []
    best = [] if items else products.cards(req.db, "AND c.kind='phone'", limit=5)
    return req.render("shop/search.html", q=q, items=items, best=best)
