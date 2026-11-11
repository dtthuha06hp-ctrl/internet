"""Đặt hàng, hủy đơn, tra cứu, mô phỏng thanh toán.

Mọi thao tác ghi đều nằm trong MỘT transaction: hoặc thành công trọn vẹn, hoặc không có gì thay đổi
(không bao giờ có chuyện tạo đơn mà không trừ kho, hay trừ kho mà không có đơn).
"""
import hashlib
import hmac
import os
import re
import secrets
from datetime import datetime

import config
from core import db
from core.template import vnd
from services import cart as cart_svc, vouchers

STATUS_VI = {"pending": "Chờ xác nhận", "confirmed": "Đã xác nhận", "preparing": "Đang chuẩn bị", "shipping": "Đang giao",
             "delivery_failed": "Giao thất bại", "delivered": "Đã giao", "completed": "Hoàn tất", "returning": "Đổi / trả",
             "refunded": "Đã hoàn tiền", "cancelled": "Đã hủy"}
PAY_VI = {"cod": "Thanh toán khi nhận hàng (COD)", "bank_qr": "Chuyển khoản QR (mô phỏng)", "ewallet": "Ví điện tử (mô phỏng)"}
PAY_STATUS_VI = {"unpaid": "Chưa thanh toán", "pending": "Chờ thanh toán", "paid": "Đã thanh toán", "refunded": "Đã hoàn tiền"}
TIMELINE = ["pending", "confirmed", "preparing", "shipping", "delivered", "completed"]

PROVINCES = ["Hà Nội", "TP. Hồ Chí Minh", "Hải Phòng", "Đà Nẵng", "Huế", "Cần Thơ",
             "An Giang", "Bắc Ninh", "Cà Mau", "Cao Bằng", "Đắk Lắk", "Điện Biên", "Đồng Nai", "Đồng Tháp", "Gia Lai",
             "Hà Tĩnh", "Hưng Yên", "Khánh Hòa", "Lai Châu", "Lâm Đồng", "Lạng Sơn", "Lào Cai", "Nghệ An", "Ninh Bình",
             "Phú Thọ", "Quảng Ngãi", "Quảng Ninh", "Quảng Trị", "Sơn La", "Tây Ninh", "Thái Nguyên", "Thanh Hóa",
             "Tuyên Quang", "Vĩnh Long"]

CANCEL_REASONS = ["Tôi muốn đổi sang phiên bản / màu khác", "Tôi tìm được giá tốt hơn", "Tôi đặt nhầm",
                  "Thời gian giao hàng quá lâu", "Tôi không còn nhu cầu"]


class OrderError(Exception):
    def __init__(self, message, field=None, to_cart=False):
        super().__init__(message)
        self.field, self.to_cart = field, to_cart


def now():
    return datetime.now().isoformat(sep=" ", timespec="seconds")


# ---------- Mã xác thực để xem trang "đặt hàng thành công" ----------
def order_token(order_code):
    from core import security
    return security.sign("order:" + order_code)


def check_token(order_code, token):
    return hmac.compare_digest(order_token(order_code), token or "")


# ---------- Kiểm tra dữ liệu khách nhập ----------
def normalize_phone(p):
    p = re.sub(r"[\s.\-]", "", p or "")
    if p.startswith("+84"):
        p = "0" + p[3:]
    return p


def validate(form, stores_ids):
    f = {k: (form.get(k) or "").strip() for k in
         ("title", "full_name", "phone", "email", "delivery_method", "province", "ward", "street", "store_id",
          "payment_method", "note", "consent", "idempotency_key", "voucher_code")}
    f["phone"] = normalize_phone(f["phone"])
    errors = {}
    if f["title"] not in ("Anh", "Chị"):
        f["title"] = "Anh"
    if len(f["full_name"]) < 2 or len(f["full_name"]) > 60 or re.search(r"\d", f["full_name"]):
        errors["full_name"] = "Vui lòng nhập họ tên người nhận (không chứa số)."
    if not re.fullmatch(r"0[35789]\d{8}", f["phone"]):
        errors["phone"] = "Số điện thoại cần 10 chữ số và bắt đầu bằng 03, 05, 07, 08 hoặc 09."
    if f["email"] and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}", f["email"]):
        errors["email"] = "Email chưa đúng định dạng, ví dụ ten@gmail.com."
    if f["delivery_method"] not in ("home", "store"):
        f["delivery_method"] = "home"
    if f["delivery_method"] == "home":
        if f["province"] not in PROVINCES:
            errors["province"] = "Vui lòng chọn tỉnh / thành phố."
        if len(f["ward"]) < 2:
            errors["ward"] = "Vui lòng nhập phường / xã."
        if len(f["street"]) < 4:
            errors["street"] = "Vui lòng nhập số nhà, tên đường."
    else:
        if not f["store_id"].isdigit() or int(f["store_id"]) not in stores_ids:
            errors["store_id"] = "Vui lòng chọn cửa hàng nhận hàng."
    if f["payment_method"] not in PAY_VI:
        errors["payment_method"] = "Vui lòng chọn cách thanh toán."
    if f["consent"] != "1":
        errors["consent"] = "Bạn cần đồng ý với điều khoản và chính sách bảo mật để đặt hàng."
    if len(f["note"]) > 300:
        errors["note"] = "Ghi chú tối đa 300 ký tự."
    return f, errors


# ---------- Đặt hàng ----------
def place_order(conn, session, form, user=None):
    stores = {r["id"]: dict(r) for r in db.all(conn, "SELECT * FROM stores WHERE is_active=1")}
    f, errors = validate(form, set(stores))
    if errors:
        raise OrderError(next(iter(errors.values())), field=errors)
    key = f["idempotency_key"] or None

    with db.transaction(conn):
        # 1. Bấm "Đặt hàng" 2 lần -> trả lại đúng đơn đã tạo
        if key:
            dup = db.one(conn, "SELECT * FROM orders WHERE idempotency_key=?", (key,))
            if dup:
                return dict(dup), True

        cart = cart_svc.get(conn, session)
        # khách đã đăng nhập: đơn luôn thuộc tài khoản của họ (kể cả khi giao cho người khác)
        cust = db.one(conn, "SELECT * FROM customers WHERE user_id=?", (user["id"],)) if user and user["role"] == "customer" else None
        cust = cust or db.one(conn, "SELECT * FROM customers WHERE phone=?", (f["phone"],))
        s = cart_svc.summary(conn, cart, f["delivery_method"], cust["id"] if cust else None, code=f["voucher_code"])
        if not s["items"]:
            raise OrderError("Giỏ hàng đang trống.", to_cart=True)
        if s["has_problem"]:
            bad = next(i for i in s["items"] if i["problem"])
            if bad["available"] <= 0:
                msg = f"Rất tiếc, {bad['name']} ({bad['label']}) vừa được người khác mua hết. Vui lòng kiểm tra lại giỏ hàng."
            else:
                msg = f"{bad['name']} ({bad['label']}) chỉ còn {bad['available']} sản phẩm. Vui lòng giảm số lượng trong giỏ hàng."
            raise OrderError(msg, to_cart=True)
        if s["voucher_code"] and s["voucher_error"]:
            raise OrderError(s["voucher_error"], field={"voucher_code": s["voucher_error"]})

        # 2. Chống lạm dụng: tối đa N đơn đang chờ xác nhận cho một SĐT
        pending = db.scalar(conn, """SELECT COUNT(*) FROM orders o JOIN customers c ON c.id=o.customer_id
                                     WHERE c.phone=? AND o.status='pending'""", (f["phone"],))
        if pending >= config.MAX_PENDING_ORDERS_PER_PHONE:
            raise OrderError(f"Số điện thoại này đang có {pending} đơn chờ xác nhận. Vui lòng chờ cửa hàng gọi xác nhận "
                             f"hoặc gọi {config.HOTLINE} để được hỗ trợ.")

        # 3. Khách hàng: tìm theo SĐT, chưa có thì tạo; lưu thời điểm đồng ý điều khoản
        t = now()
        link_uid = None
        if user and user["role"] == "customer":
            owner = db.scalar(conn, "SELECT id FROM customers WHERE user_id=?", (user["id"],))
            if owner is None or (cust and owner == cust["id"]):
                link_uid = user["id"]
        if cust:
            cid = cust["id"]
            if cust["phone"] == f["phone"]:
                conn.execute("UPDATE customers SET full_name=?, title=?, email=COALESCE(NULLIF(?,''),email) WHERE id=?",
                             (f["full_name"], f["title"], f["email"], cid))
            conn.execute("UPDATE customers SET consent_at=?, consent_version=?, user_id=COALESCE(user_id,?) WHERE id=?",
                         (t, config.CONSENT_VERSION, link_uid, cid))
        else:
            cid = conn.execute("""INSERT INTO customers(user_id,full_name,phone,email,title,consent_at,consent_version,created_at)
                                  VALUES(?,?,?,?,?,?,?,?)""",
                               (link_uid, f["full_name"], f["phone"], f["email"] or None, f["title"], t,
                                config.CONSENT_VERSION, t)).lastrowid

        # 4. Mã đơn: NM + yyMMdd + số thứ tự trong ngày
        day = datetime.now().strftime("%y%m%d")
        n = db.scalar(conn, "SELECT COUNT(*) FROM orders WHERE order_code LIKE ?", (f"NM{day}%",)) + 1
        code = f"NM{day}{n:04d}"
        while db.scalar(conn, "SELECT 1 FROM orders WHERE order_code=?", (code,)):
            n += 1
            code = f"NM{day}{n:04d}"

        store = stores.get(int(f["store_id"])) if f["delivery_method"] == "store" else None
        address = None if store else f"{f['street']}, {f['ward']}, {f['province']}"
        pay_status = "unpaid" if f["payment_method"] == "cod" else "pending"
        oid = conn.execute("""INSERT INTO orders(order_code,customer_id,status,receiver_name,receiver_phone,receiver_title,
                delivery_method,shipping_address,store_id,subtotal,discount_amount,shipping_fee,total,voucher_id,payment_method,
                payment_status,note,idempotency_key,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                           (code, cid, "pending", f["full_name"], f["phone"], f["title"], f["delivery_method"], address,
                            store["id"] if store else None, s["subtotal"], s["discount"], s["shipping_fee"], s["total"],
                            s["voucher"]["id"] if s["voucher"] else None, f["payment_method"], pay_status,
                            f["note"] or None, key, t, t)).lastrowid

        # 5. Dòng hàng (chụp giá lúc mua) + giữ hàng trong kho
        promo_now = {}
        for r in db.all(conn, """SELECT pi.id, pi.variant_id FROM promotion_items pi JOIN promotions p ON p.id=pi.promotion_id
                                 WHERE p.is_active=1 AND p.starts_at<=? AND p.ends_at>=?""", (t, t)):
            promo_now[r["variant_id"]] = r["id"]
        for it in s["items"]:
            conn.execute("""INSERT INTO order_items(order_id,variant_id,product_name,variant_label,sku,unit_price,quantity,line_total)
                            VALUES(?,?,?,?,?,?,?,?)""",
                         (oid, it["variant_id"], it["name"], it["label"], it["sku"], it["price"], it["quantity"], it["line_total"]))
            cur = conn.execute("""UPDATE inventory SET reserved=reserved+?, updated_at=?
                                  WHERE variant_id=? AND on_hand-reserved>=?""", (it["quantity"], t, it["variant_id"], it["quantity"]))
            if cur.rowcount != 1:
                raise OrderError(f"Rất tiếc, {it['name']} ({it['label']}) vừa được người khác mua hết. "
                                 "Vui lòng kiểm tra lại giỏ hàng.", to_cart=True)
            conn.execute("""INSERT INTO inventory_transactions(variant_id,type,qty_change,reason,order_id,created_at)
                            VALUES(?,?,?,?,?,?)""", (it["variant_id"], "reserve", it["quantity"], "Giữ hàng cho đơn " + code, oid, t))
            if it.get("is_promo") and it["variant_id"] in promo_now:
                cur = conn.execute("UPDATE promotion_items SET sold=sold+? WHERE id=? AND sold+?<=quota",
                                   (it["quantity"], promo_now[it["variant_id"]], it["quantity"]))
                if cur.rowcount != 1:
                    raise OrderError("Suất giá sốc vừa hết. Giá trong giỏ đã cập nhật, vui lòng kiểm tra lại.", to_cart=True)

        # 6. Mã giảm giá: tăng lượt dùng ngay trong transaction (không vượt tổng lượt)
        if s["voucher"]:
            cur = conn.execute("UPDATE vouchers SET used_count=used_count+1 WHERE id=? AND (usage_limit IS NULL OR used_count<usage_limit)",
                               (s["voucher"]["id"],))
            if cur.rowcount != 1:
                raise OrderError("Mã giảm giá vừa hết lượt sử dụng.", field={"voucher_code": "Mã giảm giá vừa hết lượt sử dụng."})
            conn.execute("INSERT INTO voucher_usages(voucher_id,customer_id,order_id,used_at) VALUES(?,?,?,?)",
                         (s["voucher"]["id"], cid, oid, t))

        conn.execute("INSERT INTO payments(order_id,method,amount,status,created_at) VALUES(?,?,?,?,?)",
                     (oid, f["payment_method"], s["total"], "pending", t))
        conn.execute("INSERT INTO order_status_history(order_id,from_status,to_status,note,changed_by,changed_at) VALUES(?,?,?,?,?,?)",
                     (oid, None, "pending", "Khách đặt hàng trên website", None, t))
        conn.execute("UPDATE customers SET order_count=order_count+1 WHERE id=?", (cid,))
        conn.execute("UPDATE carts SET status='ordered', customer_id=?, updated_at=? WHERE id=?", (cid, t, cart["id"]))
        order = dict(db.one(conn, "SELECT * FROM orders WHERE id=?", (oid,)))
        email = f["email"] or (cust["email"] if cust else None)
        if email:
            send_mail(conn, email, f"[{config.SHOP_NAME}] Xác nhận đơn hàng {code}", order_email(conn, order, s["items"], store), oid)
    return order, False


def send_mail(conn, to, subject, html, order_id=None):
    """Thay cho gửi email thật: lưu vào hộp thư mô phỏng (xem ở trang quản trị)."""
    if not html.lstrip().startswith("<div style"):
        html = ('<div style="font-family:Segoe UI,Arial,sans-serif;max-width:560px;margin:0 auto;color:#111827;'
                f'font-size:14px;line-height:1.6;padding:8px 4px"><p style="font-weight:700;color:#2F3FD1">{config.SHOP_NAME}</p>{html}'
                '<p style="color:#6B7280;font-size:12px;margin-top:20px">Email mô phỏng trong dự án học tập.</p></div>')
    conn.execute("INSERT INTO email_outbox(to_email,subject,body_html,order_id,created_at) VALUES(?,?,?,?,?)",
                 (to, subject, html, order_id, now()))


def order_email(conn, o, items, store=None):
    from core.template import render
    return render("emails/order_confirm.html", o=o, items=items, store=store, cfg=config,
                  pay=PAY_VI[o["payment_method"]], status=STATUS_VI)


# ---------- Xem / tra cứu ----------
def detail(conn, order):
    o = dict(order)
    # Viết bằng JOIN thường + một truy vấn ảnh riêng cho từng dòng: chạy được trên mọi phiên bản SQLite
    # (bản cũ đi kèm Python trên Windows không cho truy vấn con dùng cột bảng ngoài trong ORDER BY).
    o["items"] = [dict(r) for r in db.all(conn, """SELECT oi.*, p.id AS product_id, p.slug, c.kind FROM order_items oi
                                                    JOIN product_variants v ON v.id=oi.variant_id
                                                    JOIN products p ON p.id=v.product_id
                                                    JOIN categories c ON c.id=p.category_id
                                                    WHERE oi.order_id=? ORDER BY oi.id""", (o["id"],))]
    for it in o["items"]:
        it["image"] = db.scalar(conn, """SELECT url FROM product_images WHERE product_id=?
                                         ORDER BY (variant_id IS ?) DESC, is_main DESC, sort_order LIMIT 1""",
                                (it["product_id"], it["variant_id"]))
    o["history"] = [dict(r) for r in db.all(conn, "SELECT * FROM order_status_history WHERE order_id=? ORDER BY changed_at, id", (o["id"],))]
    o["store"] = dict(db.one(conn, "SELECT * FROM stores WHERE id=?", (o["store_id"],))) if o["store_id"] else None
    o["voucher_code"] = db.scalar(conn, "SELECT code FROM vouchers WHERE id=?", (o["voucher_id"],)) if o["voucher_id"] else None
    o["status_vi"] = STATUS_VI[o["status"]]
    o["pay_vi"] = PAY_VI[o["payment_method"]]
    o["pay_status_vi"] = PAY_STATUS_VI[o["payment_status"]]
    o["can_cancel"] = o["status"] == "pending"
    o["last_payment"] = db.one(conn, "SELECT * FROM payments WHERE order_id=? ORDER BY id DESC LIMIT 1", (o["id"],))
    reached = {h["to_status"]: h["changed_at"] for h in o["history"]}
    steps = []
    if o["status"] in ("cancelled", "refunded", "returning", "delivery_failed"):
        for h in o["history"]:
            steps.append({"key": h["to_status"], "label": STATUS_VI[h["to_status"]], "at": h["changed_at"], "done": True, "note": h["note"]})
    else:
        cur_idx = TIMELINE.index(o["status"]) if o["status"] in TIMELINE else 0
        for i, k in enumerate(TIMELINE):
            steps.append({"key": k, "label": STATUS_VI[k], "at": reached.get(k), "done": i <= cur_idx, "current": i == cur_idx,
                          "note": next((h["note"] for h in o["history"] if h["to_status"] == k), "")})
    o["steps"] = steps
    return o


def find(conn, code, phone):
    code = (code or "").strip().upper()
    phone = normalize_phone(phone)
    if not code or not phone:
        return None
    return db.one(conn, "SELECT * FROM orders WHERE order_code=? AND receiver_phone=?", (code, phone))


# ---------- Hủy đơn ----------
def cancel(conn, order_id, reason, by_user=None, note_prefix="Khách hủy"):
    reason = (reason or "").strip()
    if not reason:
        raise OrderError("Vui lòng chọn lý do hủy đơn.")
    with db.transaction(conn):
        o = db.one(conn, "SELECT * FROM orders WHERE id=?", (order_id,))
        if not o:
            raise OrderError("Không tìm thấy đơn hàng.")
        if o["status"] != "pending" and not by_user:
            raise OrderError("Đơn đã được cửa hàng xác nhận nên không tự hủy được. "
                             f"Vui lòng gọi {config.HOTLINE} để được hỗ trợ.")
        if o["status"] not in ("pending", "confirmed", "preparing", "delivery_failed"):
            raise OrderError("Đơn ở trạng thái này không hủy được.")
        t = now()
        for it in db.all(conn, "SELECT variant_id, quantity, unit_price FROM order_items WHERE order_id=?", (order_id,)):
            conn.execute("UPDATE inventory SET reserved=reserved-?, updated_at=? WHERE variant_id=?", (it["quantity"], t, it["variant_id"]))
            # trả lại suất giá sốc nếu dòng hàng này được mua bằng giá sốc của đợt lúc đặt (lỗi B5)
            pi = db.one(conn, """SELECT pi.id FROM promotion_items pi JOIN promotions p ON p.id=pi.promotion_id
                                 WHERE pi.variant_id=? AND pi.promo_price=? AND p.starts_at<=? AND p.ends_at>=? AND pi.sold>0
                                 ORDER BY p.id DESC LIMIT 1""", (it["variant_id"], it["unit_price"], o["created_at"], o["created_at"]))
            if pi:
                conn.execute("UPDATE promotion_items SET sold=MAX(sold-?,0) WHERE id=?", (it["quantity"], pi["id"]))
            conn.execute("""INSERT INTO inventory_transactions(variant_id,type,qty_change,reason,order_id,created_by,created_at)
                            VALUES(?,?,?,?,?,?,?)""", (it["variant_id"], "release", -it["quantity"], "Hủy đơn " + o["order_code"],
                                                       order_id, by_user["id"] if by_user else None, t))
        if o["voucher_id"]:
            conn.execute("UPDATE vouchers SET used_count=MAX(used_count-1,0) WHERE id=?", (o["voucher_id"],))
            conn.execute("DELETE FROM voucher_usages WHERE order_id=?", (order_id,))
        new_pay = "refunded" if o["payment_status"] == "paid" else o["payment_status"]
        conn.execute("UPDATE payments SET status=CASE WHEN status='paid' THEN 'refunded' ELSE 'failed' END WHERE order_id=? AND status IN ('pending','paid')",
                     (order_id,))
        conn.execute("UPDATE orders SET status='cancelled', cancel_reason=?, payment_status=?, updated_at=? WHERE id=?",
                     (reason, new_pay, t, order_id))
        conn.execute("INSERT INTO order_status_history(order_id,from_status,to_status,note,changed_by,changed_at) VALUES(?,?,?,?,?,?)",
                     (order_id, o["status"], "cancelled", f"{note_prefix}: {reason}", by_user["id"] if by_user else None, t))
        email = db.scalar(conn, "SELECT email FROM customers WHERE id=?", (o["customer_id"],))
        if email:
            send_mail(conn, email, f"[{config.SHOP_NAME}] Đơn hàng {o['order_code']} đã được hủy",
                      f"<p>Đơn hàng <b>{o['order_code']}</b> đã được hủy.</p><p>Lý do: {reason}</p>"
                      + ("<p>Số tiền đã thanh toán sẽ được hoàn lại trong 3–5 ngày làm việc (mô phỏng).</p>" if new_pay == "refunded" else ""),
                      order_id)


# ---------- Mô phỏng cổng thanh toán ----------
def simulate_payment(conn, order_id, success):
    with db.transaction(conn):
        o = db.one(conn, "SELECT * FROM orders WHERE id=?", (order_id,))
        if not o or o["payment_method"] == "cod" or o["status"] == "cancelled":
            raise OrderError("Đơn này không cần thanh toán trực tuyến.")
        if o["payment_status"] == "paid":
            return "already"
        t = now()
        p = db.one(conn, "SELECT * FROM payments WHERE order_id=? ORDER BY id DESC LIMIT 1", (order_id,))
        if p["status"] != "pending":
            pid = conn.execute("INSERT INTO payments(order_id,method,amount,status,created_at) VALUES(?,?,?,?,?)",
                               (order_id, o["payment_method"], o["total"], "pending", t)).lastrowid
        else:
            pid = p["id"]
        if success:
            conn.execute("UPDATE payments SET status='paid', paid_at=?, provider_txn_id=? WHERE id=?",
                         (t, f"MOCK{order_id:06d}-{pid}", pid))
            conn.execute("UPDATE orders SET payment_status='paid', updated_at=? WHERE id=?", (t, order_id))
            email = db.scalar(conn, "SELECT email FROM customers WHERE id=?", (o["customer_id"],))
            if email:
                send_mail(conn, email, f"[{config.SHOP_NAME}] Đã nhận thanh toán đơn {o['order_code']}",
                          f"<p>Chúng tôi đã nhận <b>{vnd(o['total'])}</b> cho đơn <b>{o['order_code']}</b>. Cảm ơn bạn!</p>", order_id)
            return "paid"
        conn.execute("UPDATE payments SET status='failed' WHERE id=?", (pid,))
        return "failed"


def switch_to_cod(conn, order_id):
    with db.transaction(conn):
        o = db.one(conn, "SELECT * FROM orders WHERE id=?", (order_id,))
        if not o or o["status"] != "pending" or o["payment_status"] == "paid":
            raise OrderError("Không đổi được cách thanh toán cho đơn này.")
        conn.execute("UPDATE payments SET status='failed' WHERE order_id=? AND status='pending'", (order_id,))
        conn.execute("INSERT INTO payments(order_id,method,amount,status,created_at) VALUES(?,?,?,?,?)",
                     (order_id, "cod", o["total"], "pending", now()))
        conn.execute("UPDATE orders SET payment_method='cod', payment_status='unpaid', updated_at=? WHERE id=?", (now(), order_id))


def mock_qr_svg(text, size=200):
    """Hình QR MINH HỌA (không quét được), sinh cố định từ nội dung."""
    h = hashlib.sha256(text.encode()).digest() * 8
    n = 25
    cell = size / n
    rects = []
    bit = 0
    for y in range(n):
        for x in range(n):
            in_finder = any(fx <= x < fx + 7 and fy <= y < fy + 7 for fx, fy in ((0, 0), (n - 7, 0), (0, n - 7)))
            if in_finder:
                continue
            if (h[bit // 8] >> (bit % 8)) & 1:
                rects.append(f'<rect x="{x * cell:.2f}" y="{y * cell:.2f}" width="{cell:.2f}" height="{cell:.2f}"/>')
            bit += 1
    finders = ""
    for fx, fy in ((0, 0), (n - 7, 0), (0, n - 7)):
        X, Y = fx * cell, fy * cell
        finders += (f'<rect x="{X:.2f}" y="{Y:.2f}" width="{7 * cell:.2f}" height="{7 * cell:.2f}"/>'
                    f'<rect x="{X + cell:.2f}" y="{Y + cell:.2f}" width="{5 * cell:.2f}" height="{5 * cell:.2f}" fill="#fff"/>'
                    f'<rect x="{X + 2 * cell:.2f}" y="{Y + 2 * cell:.2f}" width="{3 * cell:.2f}" height="{3 * cell:.2f}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}" '
            f'role="img" aria-label="Mã QR minh họa"><rect width="{size}" height="{size}" fill="#fff"/>'
            f'<g fill="#111827">{"".join(rects)}{finders}</g></svg>')
