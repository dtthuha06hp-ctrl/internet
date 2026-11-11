"""Thanh toán, đặt hàng thành công, mô phỏng thanh toán trực tuyến."""
from core import db, security
from core.router import route
from core.server import json_response, HttpError, redirect
from services import cart as cart_svc, orders


def _prefill(req):
    """Điền sẵn thông tin nếu khách đã đăng nhập và từng mua hàng."""
    f = {"title": "Anh", "delivery_method": "home", "payment_method": "cod"}
    if req.user and req.user["role"] == "customer":
        c = db.one(req.db, "SELECT * FROM customers WHERE user_id=?", (req.user["id"],))
        f.update(full_name=req.user["full_name"], phone=req.user["phone"] or "", email=req.user["email"])
        if c:
            f.update(title=c["title"] or "Anh", full_name=c["full_name"], phone=c["phone"], email=c["email"] or req.user["email"])
            a = db.one(req.db, "SELECT * FROM addresses WHERE customer_id=? ORDER BY is_default DESC LIMIT 1", (c["id"],))
            if a:
                f.update(province=a["province"], ward=a["ward"], street=a["street"])
    return f


def _render(req, f, errors=None, error_msg="", status=200):
    c = cart_svc.get(req.db, req.session)
    s = cart_svc.summary(req.db, c, "home")
    return req.render("shop/checkout.html", status=status, s=s, f=f, errors=errors or {}, error_msg=error_msg,
                      provinces=orders.PROVINCES, stores=db.all(req.db, "SELECT * FROM stores WHERE is_active=1 ORDER BY id"),
                      pay_methods=orders.PAY_VI, home_fee=cart_svc.shipping_fee(s["subtotal"], "home"), key=f.get("idempotency_key") or security.new_token(16))


@route("/thanh-toan", methods=("GET", "POST"))
def checkout(req):
    c = cart_svc.get(req.db, req.session)
    if req.method == "GET":
        s = cart_svc.summary(req.db, c)
        if not s["items"]:
            return redirect("/gio-hang")
        if s["has_problem"]:
            return redirect("/gio-hang?tb=" + _q("Vui lòng xử lý các sản phẩm có cảnh báo trước khi đặt hàng."))
        return _render(req, _prefill(req))
    req.check_csrf()
    f = dict(req.form)
    try:
        order, _dup = orders.place_order(req.db, req.session, req.form, req.user)
    except orders.OrderError as e:
        if e.to_cart:
            return redirect("/gio-hang?tb=" + _q(str(e)))
        msg = "Vui lòng kiểm tra các ô báo đỏ bên dưới." if e.field and len(e.field) > 1 else str(e)
        return _render(req, f, e.field or {}, msg, status=400)
    return redirect(f"/dat-hang-thanh-cong/{order['order_code']}?t={orders.order_token(order['order_code'])}")


def _q(s):
    from urllib.parse import quote
    return quote(s)


def _load(req, code):
    o = db.one(req.db, "SELECT * FROM orders WHERE order_code=?", (code,))
    if not o or not orders.check_token(code, req.query.get("t") or req.form.get("t")):
        raise HttpError(404, "Không tìm thấy đơn hàng. Hãy dùng trang Tra cứu đơn hàng với mã đơn và số điện thoại.")
    return o


@route("/dat-hang-thanh-cong/<code>")
def success(req, code):
    o = orders.detail(req.db, _load(req, code))
    bank = {"bank": "Ngân hàng Nhịp Việt (giả lập)", "account": "0123 4567 8888", "holder": "CONG TY NHIP MOBILE (MO PHONG)",
            "content": o["order_code"]}
    qr = orders.mock_qr_svg(f"{bank['account']}|{o['total']}|{o['order_code']}") if o["payment_method"] == "bank_qr" else ""
    return req.render("shop/success.html", o=o, token=req.query.get("t"), bank=bank, qr=qr,
                      pay_result=req.query.get("tt", ""), reasons=orders.CANCEL_REASONS)


@route("/dat-hang-thanh-cong/<code>/thanh-toan", methods=("POST",))
def pay(req, code):
    req.check_csrf()
    o = _load(req, code)
    t = orders.order_token(code)
    try:
        if req.form.get("action") == "cod":
            orders.switch_to_cod(req.db, o["id"])
            result = "cod"
        else:
            # cổng giả lập gửi IPN có chữ ký về; máy chủ kiểm tra chữ ký + số tiền như với VNPay thật
            from services import payment_gateway as pg
            _, _, result = pg.handle_ipn(req.db, pg.build_ipn(o, req.form.get("action") == "ok"))
    except orders.OrderError:
        result = "loi"
    return redirect(f"/dat-hang-thanh-cong/{code}?t={t}&tt={result}#thanh-toan")


@route("/thanh-toan/ipn", methods=("POST",))
def payment_ipn(req):
    """Địa chỉ cổng thanh toán gọi về (máy chủ với máy chủ, nên không dùng mã CSRF)."""
    from services import payment_gateway as pg
    code, msg, _ = pg.handle_ipn(req.db, req.json if isinstance(req.json, dict) else req.form)
    return json_response({"RspCode": code, "Message": msg})
