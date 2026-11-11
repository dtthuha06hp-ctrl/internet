"""Giỏ hàng. Giá luôn tính lại ở máy chủ mỗi lần xem, trình duyệt chỉ gửi mã phiên bản và số lượng."""
from datetime import datetime
import config
from core import db
from services import pricing, vouchers


class CartError(Exception):
    pass


def now():
    return datetime.now().isoformat(sep=" ", timespec="seconds")


def get(conn, session, create=False):
    row = db.one(conn, "SELECT * FROM carts WHERE session_token=? AND status='active' ORDER BY id DESC LIMIT 1",
                 (session["token"],))
    if row or not create:
        return dict(row) if row else None
    cid = conn.execute("INSERT INTO carts(session_token,updated_at) VALUES(?,?)", (session["token"], now())).lastrowid
    return dict(db.one(conn, "SELECT * FROM carts WHERE id=?", (cid,)))


def default_variant(conn, product_id):
    """Phiên bản còn hàng rẻ nhất (dùng cho nút "Thêm vào giỏ" trên thẻ sản phẩm)."""
    vs = pricing.variants_of(conn, [product_id]).get(product_id, [])
    avail = [v for v in vs if v["available"] > 0]
    if not avail:
        raise CartError("Sản phẩm này đang tạm hết hàng.")
    return min(avail, key=lambda v: (v["price"], v["id"]))["id"]


def add(conn, session, variant_id, qty=1):
    qty = max(1, int(qty or 1))
    v = db.one(conn, """SELECT v.*, p.name, p.is_active AS p_active, COALESCE(i.on_hand-i.reserved,0) available
                        FROM product_variants v JOIN products p ON p.id=v.product_id
                        LEFT JOIN inventory i ON i.variant_id=v.id WHERE v.id=?""", (variant_id,))
    if not v or not v["is_active"] or not v["p_active"]:
        raise CartError("Sản phẩm không còn kinh doanh.")
    if v["available"] <= 0:
        raise CartError(f"{v['name']} phiên bản này đang tạm hết hàng.")
    with db.transaction(conn):
        cart = get(conn, session, create=True)
        cur = db.scalar(conn, "SELECT quantity FROM cart_items WHERE cart_id=? AND variant_id=?", (cart["id"], variant_id)) or 0
        limit = min(config.MAX_QTY_PER_ITEM, v["available"])
        new = min(cur + qty, limit)
        if new <= cur:
            if cur >= config.MAX_QTY_PER_ITEM:
                raise CartError(f"Mỗi phiên bản chỉ mua tối đa {config.MAX_QTY_PER_ITEM} sản phẩm trong một đơn.")
            raise CartError(f"Chỉ còn {v['available']} sản phẩm, giỏ của bạn đã có {cur}.")
        if cur:
            conn.execute("UPDATE cart_items SET quantity=? WHERE cart_id=? AND variant_id=?", (new, cart["id"], variant_id))
        else:
            conn.execute("INSERT INTO cart_items(cart_id,variant_id,quantity,added_at) VALUES(?,?,?,?)",
                         (cart["id"], variant_id, new, now()))
        conn.execute("UPDATE carts SET updated_at=? WHERE id=?", (now(), cart["id"]))
    capped = new < cur + qty
    return {"name": v["name"], "quantity": new, "capped": capped}


def set_qty(conn, session, variant_id, qty):
    cart = get(conn, session)
    if not cart:
        return
    qty = int(qty)
    if qty <= 0:
        conn.execute("DELETE FROM cart_items WHERE cart_id=? AND variant_id=?", (cart["id"], variant_id))
        return
    avail = db.scalar(conn, "SELECT on_hand-reserved FROM inventory WHERE variant_id=?", (variant_id,)) or 0
    qty = min(qty, config.MAX_QTY_PER_ITEM, max(avail, 1))
    conn.execute("UPDATE cart_items SET quantity=? WHERE cart_id=? AND variant_id=?", (qty, cart["id"], variant_id))


def set_voucher(conn, session, code):
    cart = get(conn, session, create=True)
    conn.execute("UPDATE carts SET voucher_code=? WHERE id=?", ((code or "").strip().upper() or None, cart["id"]))


def lines(conn, cart):
    if not cart:
        return []
    rows = [dict(r) for r in db.all(conn, """SELECT ci.variant_id, ci.quantity, v.product_id, v.sku, v.storage, v.ram, v.color_name,
              p.name, p.slug, c.kind, p.is_active AS p_active, v.is_active AS v_active
              FROM cart_items ci JOIN product_variants v ON v.id=ci.variant_id JOIN products p ON p.id=v.product_id
              JOIN categories c ON c.id=p.category_id WHERE ci.cart_id=? ORDER BY ci.id""", (cart["id"],))]
    vmap = {}
    for vs in pricing.variants_of(conn, list({r["product_id"] for r in rows})).values():
        for v in vs:
            vmap[v["id"]] = v
    imgs = {}
    for r in db.all(conn, "SELECT product_id, variant_id, url FROM product_images ORDER BY is_main DESC, sort_order"):
        imgs.setdefault((r["product_id"], r["variant_id"]), r["url"])
        imgs.setdefault((r["product_id"], None), r["url"])
    out = []
    for r in rows:
        v = vmap.get(r["variant_id"])
        r["label"] = " · ".join(x for x in (r["storage"], r["color_name"]) if x)
        r["url"] = ("/dien-thoai/" if r["kind"] == "phone" else "/phu-kien/") + r["slug"] + "?sku=" + r["sku"]
        r["image"] = imgs.get((r["product_id"], r["variant_id"])) or imgs.get((r["product_id"], None), "")
        if not v or not r["p_active"]:
            r.update(price=0, list_price=0, available=0, problem="Sản phẩm đã ngừng kinh doanh. Hãy xóa khỏi giỏ.")
        else:
            r.update(price=v["price"], list_price=v["list_price"], available=v["available"], is_promo=v["is_promo"], problem="")
            if v["available"] <= 0:
                r["problem"] = "Phiên bản này vừa hết hàng. Hãy xóa hoặc chọn màu khác."
            elif r["quantity"] > v["available"]:
                r["problem"] = f"Chỉ còn {v['available']} sản phẩm, hãy giảm số lượng."
        r["max_qty"] = max(1, min(config.MAX_QTY_PER_ITEM, r.get("available", 0) or 1))
        r["line_total"] = r["price"] * r["quantity"]
        out.append(r)
    return out


def shipping_fee(subtotal, method="home"):
    if method == "store" or subtotal == 0 or subtotal >= config.FREE_SHIP_FROM:
        return 0
    return config.SHIPPING_FEE


def summary(conn, cart, method="home", customer_id=None, code=None):
    items = lines(conn, cart)
    subtotal = sum(i["line_total"] for i in items if not i["problem"])
    ship = shipping_fee(subtotal, method)
    code = code if code is not None else (cart or {}).get("voucher_code")
    voucher, discount, voucher_error = None, 0, ""
    if code and items:
        try:
            voucher, discount = vouchers.check(conn, code, subtotal, ship, customer_id)
        except vouchers.VoucherError as e:
            voucher_error = str(e)
    return {
        "items": items, "count": sum(i["quantity"] for i in items), "subtotal": subtotal, "shipping_fee": ship,
        "discount": discount, "total": subtotal - discount + ship, "voucher": voucher, "voucher_code": code or "",
        "voucher_error": voucher_error, "has_problem": any(i["problem"] for i in items),
        "free_ship_gap": max(0, config.FREE_SHIP_FROM - subtotal) if method == "home" and subtotal else 0,
    }


# ---------- Giữ giỏ hàng theo tài khoản (Giai đoạn 4) ----------
def attach_on_login(conn, session_token, customer_id):
    """Sau khi đăng nhập: gộp giỏ đang chọn (khách vãng lai) với giỏ đã lưu của tài khoản."""
    if not customer_id:
        return 0
    with db.transaction(conn):
        guest = db.one(conn, "SELECT * FROM carts WHERE session_token=? AND status='active' ORDER BY id DESC LIMIT 1", (session_token,))
        saved = db.one(conn, """SELECT * FROM carts WHERE customer_id=? AND status='active' AND (session_token IS NULL OR session_token<>?)
                                ORDER BY updated_at DESC LIMIT 1""", (customer_id, session_token))
        moved = 0
        if guest and saved:
            for it in db.all(conn, "SELECT variant_id, quantity FROM cart_items WHERE cart_id=?", (guest["id"],)):
                cur = db.scalar(conn, "SELECT quantity FROM cart_items WHERE cart_id=? AND variant_id=?", (saved["id"], it["variant_id"]))
                if cur:
                    conn.execute("UPDATE cart_items SET quantity=? WHERE cart_id=? AND variant_id=?",
                                 (min(config.MAX_QTY_PER_ITEM, cur + it["quantity"]), saved["id"], it["variant_id"]))
                else:
                    conn.execute("INSERT INTO cart_items(cart_id,variant_id,quantity,added_at) VALUES(?,?,?,?)",
                                 (saved["id"], it["variant_id"], it["quantity"], now()))
                moved += 1
            conn.execute("UPDATE carts SET status='merged', session_token=NULL WHERE id=?", (guest["id"],))
            if not saved["voucher_code"] and guest["voucher_code"]:
                conn.execute("UPDATE carts SET voucher_code=? WHERE id=?", (guest["voucher_code"], saved["id"]))
            conn.execute("UPDATE carts SET session_token=?, updated_at=? WHERE id=?", (session_token, now(), saved["id"]))
        elif saved:
            conn.execute("UPDATE carts SET session_token=? WHERE id=?", (session_token, saved["id"]))
        elif guest:
            conn.execute("UPDATE carts SET customer_id=? WHERE id=?", (customer_id, guest["id"]))
        # các giỏ cũ khác của tài khoản không còn dùng
        conn.execute("""UPDATE carts SET status='merged' WHERE customer_id=? AND status='active' AND
                        (session_token IS NULL OR session_token<>?)""", (customer_id, session_token))
    return moved


def detach_on_logout(conn, session_token, customer_id):
    """Khi đăng xuất: cất giỏ vào tài khoản để lần sau đăng nhập vẫn còn; trình duyệt trở về giỏ trống."""
    if customer_id:
        conn.execute("UPDATE carts SET customer_id=?, session_token=NULL WHERE session_token=? AND status='active'",
                     (customer_id, session_token))
