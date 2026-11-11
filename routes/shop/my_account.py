"""Tài khoản người mua: đăng ký, quên mật khẩu, tổng quan, đơn của tôi, địa chỉ, yêu thích, đánh giá, đổi mật khẩu."""
from urllib.parse import quote
from core import db, session
from core.router import route
from core.server import HttpError, json_response, redirect
from services import accounts, cart as cart_svc, orders, products, reviews

TABS = [("tat-ca", "Tất cả", None), ("cho-xac-nhan", "Chờ xác nhận", ("pending",)),
        ("dang-xu-ly", "Đang xử lý", ("confirmed", "preparing", "shipping", "delivery_failed")),
        ("da-giao", "Đã giao", ("delivered", "completed")), ("da-huy", "Đã hủy / trả", ("cancelled", "returning", "refunded"))]


def _me(req):
    """Chỉ người mua đã đăng nhập; admin/nhân viên được đưa về trang quản trị."""
    if not req.user:
        raise HttpError(302, "/dang-nhap?next=" + quote(req.full_path))
    if req.user["role"] != "customer":
        raise HttpError(302, "/quan-tri")
    c = accounts.customer_of(req.db, req.user)
    if not c:
        raise HttpError(403, "Tài khoản chưa có hồ sơ người mua.")
    return c


def _render(req, tpl, me, section, **ctx):
    counts = {
        "orders": db.scalar(req.db, "SELECT COUNT(*) FROM orders WHERE customer_id=?", (me["id"],)),
        "wish": db.scalar(req.db, "SELECT COUNT(*) FROM wishlists WHERE customer_id=?", (me["id"],)),
        "to_review": len(reviews.pending_to_write(req.db, me["id"])),
    }
    return req.render(tpl, me=me, section=section, counts=counts, **ctx)


# ---------------- Đăng ký ----------------
@route("/dang-ky", methods=("GET", "POST"))
def register(req):
    if req.user:
        return redirect("/tai-khoan")
    if req.method == "GET":
        return req.render("shop/register.html", f={"title": "Anh"}, errors={}, error="")
    req.check_csrf()
    try:
        user, linked = accounts.register(req.db, req.form)
    except accounts.AccountError as e:
        f = {k: v for k, v in req.form.items() if not k.startswith("password")}
        msg = "Vui lòng kiểm tra các ô báo đỏ bên dưới." if len(e.field) > 1 else str(e)
        return req.render("shop/register.html", status=400, f=f, errors=e.field, error=msg)
    req.session = session.set_user(req.db, req.session, user["id"])
    req._session_changed = True
    cart_svc.attach_on_login(req.db, req.session["token"], accounts.customer_of(req.db, user)["id"])
    return redirect("/tai-khoan?tb=" + ("chao-cu" if linked else "chao"))


# ---------------- Quên / đặt lại mật khẩu ----------------
@route("/quen-mat-khau", methods=("GET", "POST"))
def forgot(req):
    sent = False
    if req.method == "POST":
        req.check_csrf()
        accounts.request_reset(req.db, req.form.get("email"), f"http://{req.headers.get('Host', '127.0.0.1:8000')}")
        sent = True
    return req.render("shop/forgot.html", sent=sent, email=req.form.get("email", ""))


@route("/dat-lai-mat-khau", methods=("GET", "POST"))
def reset(req):
    token = req.query.get("t") or req.form.get("t")
    user = accounts.user_from_reset(req.db, token)
    if not user:
        return req.render("shop/reset.html", status=400, invalid=True, token="", errors={}, error="")
    if req.method == "GET":
        return req.render("shop/reset.html", invalid=False, token=token, errors={}, error="")
    req.check_csrf()
    try:
        accounts.do_reset(req.db, user, req.form.get("new"), req.form.get("new2"))
    except accounts.AccountError as e:
        return req.render("shop/reset.html", status=400, invalid=False, token=token, errors=e.field, error=str(e))
    return req.render("shop/login.html", error="", notice="Đã đặt mật khẩu mới. Hãy đăng nhập lại.", login=user["email"], next="")


# ---------------- Tổng quan ----------------
@route("/tai-khoan", methods=("GET", "POST"))
def overview(req):
    me = _me(req)
    errors, notice = {}, {"chao": "Tạo tài khoản thành công. Chào mừng bạn!",
                          "chao-cu": "Tạo tài khoản thành công. Các đơn bạn từng đặt bằng số điện thoại này đã được gắn vào tài khoản.",
                          "luu": "Đã lưu thông tin."}.get(req.query.get("tb", ""), "")
    if req.method == "POST":
        req.check_csrf()
        try:
            accounts.update_profile(req.db, req.user, req.form)
            return redirect("/tai-khoan?tb=luu")
        except accounts.AccountError as e:
            errors = e.field
    recent = [orders.detail(req.db, o) for o in db.all(req.db, "SELECT * FROM orders WHERE customer_id=? ORDER BY created_at DESC LIMIT 3", (me["id"],))]
    return _render(req, "shop/account/overview.html", me, "tong-quan", recent=recent, errors=errors, notice=notice)


# ---------------- Đơn của tôi ----------------
@route("/tai-khoan/don-hang")
def my_orders(req):
    me = _me(req)
    tab = req.query.get("tab", "tat-ca")
    statuses = next((s for k, _l, s in TABS if k == tab), None)
    sql, args = "SELECT * FROM orders WHERE customer_id=?", [me["id"]]
    if statuses:
        sql += f" AND status IN ({','.join('?' * len(statuses))})"
        args += list(statuses)
    rows = [orders.detail(req.db, o) for o in db.all(req.db, sql + " ORDER BY created_at DESC", args)]
    tab_counts = {}
    for k, _l, s in TABS:
        q, a = "SELECT COUNT(*) FROM orders WHERE customer_id=?", [me["id"]]
        if s:
            q += f" AND status IN ({','.join('?' * len(s))})"
            a += list(s)
        tab_counts[k] = db.scalar(req.db, q, a)
    return _render(req, "shop/account/orders.html", me, "don-hang", rows=rows, tabs=TABS, tab=tab, tab_counts=tab_counts)


@route("/tai-khoan/don-hang/<code>", methods=("GET", "POST"))
def my_order(req, code):
    me = _me(req)
    o = db.one(req.db, "SELECT * FROM orders WHERE order_code=? AND customer_id=?", (code, me["id"]))
    if not o:
        raise HttpError(404, "Không tìm thấy đơn hàng trong tài khoản của bạn.")
    error = notice = ""
    if req.method == "POST":
        req.check_csrf()
        try:
            orders.cancel(req.db, o["id"], req.form.get("reason"))
            notice = "Đã hủy đơn hàng. Sản phẩm đã được trả lại kho."
        except orders.OrderError as e:
            error = str(e)
    o = orders.detail(req.db, db.one(req.db, "SELECT * FROM orders WHERE id=?", (o["id"],)))
    reviewed = {r["product_id"] for r in db.all(req.db, "SELECT product_id FROM reviews WHERE order_id=?", (o["id"],))}
    pids = {}
    for it in o["items"]:
        pids[it["id"]] = db.scalar(req.db, "SELECT product_id FROM product_variants WHERE id=?", (it["variant_id"],))
    return _render(req, "shop/account/order.html", me, "don-hang", o=o, reviewed=reviewed, pids=pids,
                   reasons=orders.CANCEL_REASONS, error=error, notice=notice)


# ---------------- Sổ địa chỉ ----------------
@route("/tai-khoan/dia-chi", methods=("GET", "POST"))
def my_addresses(req):
    me = _me(req)
    errors, error, form, edit_id = {}, "", {}, None
    if req.method == "POST":
        req.check_csrf()
        action = req.form.get("action")
        aid = int(req.form.get("id")) if (req.form.get("id") or "").isdigit() else None
        try:
            if action == "xoa" and aid:
                accounts.delete_address(req.db, me["id"], aid)
            elif action == "mac-dinh" and aid:
                accounts.set_default_address(req.db, me["id"], aid)
            else:
                accounts.save_address(req.db, me["id"], req.form, aid)
            return redirect("/tai-khoan/dia-chi")
        except accounts.AccountError as e:
            errors, error, form, edit_id = e.field, str(e), dict(req.form), aid
    edit = req.query.get("sua")
    if edit and edit.isdigit() and not form:
        a = db.one(req.db, "SELECT * FROM addresses WHERE id=? AND customer_id=?", (int(edit), me["id"]))
        if a:
            form, edit_id = dict(a), a["id"]
    return _render(req, "shop/account/addresses.html", me, "dia-chi", items=accounts.addresses(req.db, me["id"]),
                   provinces=orders.PROVINCES, form=form, errors=errors, error=error, edit_id=edit_id,
                   show_form=bool(form) or req.query.get("them") == "1", max_n=accounts.MAX_ADDRESSES)


# ---------------- Yêu thích ----------------
@route("/tai-khoan/yeu-thich")
def my_wishlist(req):
    me = _me(req)
    items = products.cards(req.db, "AND p.id IN (SELECT product_id FROM wishlists WHERE customer_id=?)", (me["id"],),
                           order="(SELECT created_at FROM wishlists w WHERE w.product_id=p.id AND w.customer_id=%d) DESC" % me["id"], limit=100)
    return _render(req, "shop/account/wishlist.html", me, "yeu-thich", items=items)


@route("/yeu-thich/doi", methods=("POST",))
def toggle_wish(req):
    req.check_csrf()
    if not req.user or req.user["role"] != "customer":
        return json_response({"ok": False, "login": True, "message": "Đăng nhập để lưu sản phẩm yêu thích."}, 401)
    me = accounts.customer_of(req.db, req.user)
    data = req.json or req.form
    try:
        on = accounts.toggle_wishlist(req.db, me["id"], int(data.get("product_id") or 0))
    except (accounts.AccountError, ValueError) as e:
        return json_response({"ok": False, "message": str(e)}, 400)
    return json_response({"ok": True, "on": on, "message": "Đã thêm vào danh sách yêu thích" if on else "Đã bỏ khỏi danh sách yêu thích"})


# ---------------- Đánh giá ----------------
@route("/tai-khoan/danh-gia")
def my_reviews(req):
    me = _me(req)
    return _render(req, "shop/account/reviews.html", me, "danh-gia", todo=reviews.pending_to_write(req.db, me["id"]),
                   done=reviews.mine(req.db, me["id"]), notice="Cảm ơn bạn! Đánh giá sẽ hiện sau khi cửa hàng duyệt." if req.query.get("tb") == "ok" else "")


@route("/tai-khoan/danh-gia/viet", methods=("GET", "POST"))
def write_review(req):
    me = _me(req)
    code = (req.query.get("don") or req.form.get("don") or "").upper()
    try:
        pid = int(req.query.get("sp") or req.form.get("sp") or 0)
    except ValueError:
        pid = 0
    error = ""
    try:
        o = reviews.can_review(req.db, me["id"], code, pid)
    except reviews.ReviewError as e:
        return _render(req, "shop/account/review_form.html", me, "danh-gia", blocked=str(e), p=None, o=None, f={}, error="")
    p = products.cards(req.db, "AND p.id=?", (pid,), limit=1)[0]
    f = {}
    if req.method == "POST":
        req.check_csrf()
        f = dict(req.form)
        try:
            reviews.create(req.db, me["id"], code, pid, req.form.get("rating"), req.form.get("content"))
            return redirect("/tai-khoan/danh-gia?tb=ok")
        except reviews.ReviewError as e:
            error = str(e)
    return _render(req, "shop/account/review_form.html", me, "danh-gia", blocked="", p=p, o=o, f=f, error=error)


# ---------------- Đổi mật khẩu ----------------
@route("/tai-khoan/doi-mat-khau", methods=("GET", "POST"))
def change_pw(req):
    me = _me(req)
    errors, error = {}, ""
    if req.method == "POST":
        req.check_csrf()
        try:
            accounts.change_password(req.db, req.user, req.form.get("old"), req.form.get("new"), req.form.get("new2"))
            cart_svc.detach_on_logout(req.db, req.session["token"], me["id"])
            # các phiên đã bị xóa -> tạo phiên mới cho chính trình duyệt này
            req.session = session.create(req.db, req.user["id"])
            req._session_changed = True
            cart_svc.attach_on_login(req.db, req.session["token"], me["id"])
            return _render(req, "shop/account/password.html", me, "mat-khau", errors={}, error="",
                           notice="Đã đổi mật khẩu. Các thiết bị khác đã được đăng xuất.")
        except accounts.AccountError as e:
            errors, error = e.field, str(e)
    return _render(req, "shop/account/password.html", me, "mat-khau", errors=errors, error=error, notice="")
