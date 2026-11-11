"""Trang chủ."""
from core import db
from core.router import route
from services import products


@route("/")
def home(req):
    conn = req.db
    phone_where = "AND c.kind='phone'"
    banners = [dict(b) for b in db.all(conn, """SELECT * FROM banners WHERE is_active=1
        AND (starts_at IS NULL OR starts_at<=datetime('now','localtime')) AND (ends_at IS NULL OR ends_at>=datetime('now','localtime'))
        ORDER BY position, sort_order""")]
    for b in banners:
        b["price"] = None
        b["image"] = b["image2"] = None
        # Khung "Giá phải trả" chỉ hiện khi banner dẫn tới đúng trang của sản phẩm đó (lỗi B7: trước đây dựa vào tiêu đề)
        prod = db.one(conn, """SELECT p.slug, c.kind FROM products p JOIN categories c ON c.id=p.category_id WHERE p.id=?""",
                      (b["product_id"],)) if b["product_id"] else None
        prod_url = (("/dien-thoai/" if prod["kind"] == "phone" else "/phu-kien/") + prod["slug"]) if prod else None
        if prod_url and (b["link_url"] or "").split("?")[0] == prod_url:
            # giá phải trả thấp nhất trong các phiên bản còn hàng, đã tính giá sốc (cùng cách tính với thẻ sản phẩm)
            from services import pricing
            vs = [v for v in pricing.variants_of(conn, [b["product_id"]]).get(b["product_id"], []) if v["available"] > 0]
            v = min(vs, key=lambda x: (x["price"], x["id"])) if vs else None
            if v:
                b["price"], b["list_price"] = v["price"], v["list_price"]
                b["variant_label"] = v["storage"]
        if b["product_id"]:
            imgs = db.all(conn, "SELECT url FROM product_images WHERE product_id=? ORDER BY sort_order LIMIT 2", (b["product_id"],))
            b["image"] = imgs[0]["url"] if imgs else None
            b["image2"] = imgs[1]["url"] if len(imgs) > 1 else None
    promo, flash_items = products.flash_sale(conn)
    from datetime import datetime
    promo_left = max(0, int((datetime.fromisoformat(promo["ends_at"]) - datetime.now()).total_seconds())) if promo else 0
    finder = [{"id": p["id"], "name": p["name"], "price": p["price"], "brand": p["brand_slug"], "needs": p["needs"] or "",
               "url": p["url"], "image": p["image"], "in_stock": p["in_stock"]}
              for p in products.cards(conn, phone_where, limit=None)]
    return req.render(
        "shop/home.html",
        hero=[b for b in banners if b["position"] == "hero"],
        side=[b for b in banners if b["position"] == "side"],
        brands=db.all(conn, """SELECT DISTINCT b.* FROM brands b JOIN products p ON p.brand_id=b.id JOIN categories c ON c.id=p.category_id
                              WHERE c.kind='phone' ORDER BY b.sort_order"""),
        promo=promo, flash_items=flash_items, promo_left=promo_left,
        best=products.cards(conn, phone_where, order="p.sold_count DESC", limit=10),
        newest=products.cards(conn, phone_where + " AND p.is_new=1", order="p.created_at DESC", limit=5),
        ranges=products.price_ranges(conn),
        acc_cats=db.all(conn, "SELECT * FROM categories WHERE kind='accessory' AND parent_id IS NOT NULL AND is_active=1 ORDER BY sort_order"),
        accessories=products.cards(conn, "AND c.kind='accessory'", order="p.sold_count DESC", limit=25),
        posts=db.all(conn, "SELECT * FROM posts WHERE is_published=1 ORDER BY published_at DESC LIMIT 3"),
        finder=finder,
    )
