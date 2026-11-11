"""Đăng nhập / đăng xuất (bản đầy đủ: đăng ký, tài khoản... ở Giai đoạn 4)."""
from core import session
from core.router import route
from core.server import redirect
from services import accounts


def _safe_next(url):
    return url if url and url.startswith("/") and not url.startswith("//") else ""


@route("/dang-nhap", methods=("GET", "POST"))
def login(req):
    nxt = _safe_next(req.query.get("next") or req.form.get("next"))
    if req.method == "GET":
        if req.user:
            return redirect(nxt or ("/quan-tri" if req.user["role"] in ("admin", "staff") else "/"))
        notice = "Vui lòng đăng nhập để tiếp tục." if nxt else ""
        return req.render("shop/login.html", error="", notice=notice, login="", next=nxt)
    req.check_csrf()
    try:
        user = accounts.authenticate(req.db, req.form.get("login"), req.form.get("password"), req.ip)
    except accounts.LoginError as e:
        return req.render("shop/login.html", status=400, error=str(e), notice="", login=req.form.get("login", ""), next=nxt)
    req.session = session.set_user(req.db, req.session, user["id"])
    req._session_changed = True
    req.user = user
    cust = accounts.customer_of(req.db, user)
    if cust:
        from services import cart as cart_svc
        cart_svc.attach_on_login(req.db, req.session["token"], cust["id"])
    return redirect(nxt or ("/quan-tri" if user["role"] in ("admin", "staff") else "/"))


@route("/dang-xuat", methods=("POST",))
def logout(req):
    req.check_csrf()
    cust = accounts.customer_of(req.db, req.user)
    if cust:
        from services import cart as cart_svc
        cart_svc.detach_on_logout(req.db, req.session["token"], cust["id"])
    req.session = session.set_user(req.db, req.session, None)
    req._session_changed = True
    return redirect("/")
