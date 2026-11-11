"""Tin tức, trung tâm hỗ trợ, trang chính sách."""
import re
from core import db
from core.router import route
from core.server import HttpError, redirect
from services import content, orders

# slug -> (tiêu đề, mô tả ngắn, nhóm)
HELP = {
    "huong-dan-mua-hang": ("Hướng dẫn mua hàng", "Đặt hàng trong 4 bước, không cần tài khoản.", "mua"),
    "cau-hoi-thuong-gap": ("Câu hỏi thường gặp", "Giải đáp nhanh về đơn hàng, thanh toán, bảo hành.", "mua"),
    "giao-hang": ("Chính sách giao hàng", "Phí giao, thời gian và cách nhận hàng.", "chinh-sach"),
    "doi-tra-bao-hanh": ("Đổi trả và bảo hành", "Đổi mới 30 ngày, bảo hành 12 tháng.", "chinh-sach"),
    "bao-mat": ("Bảo mật dữ liệu cá nhân", "Chúng tôi thu thập gì và dùng để làm gì.", "chinh-sach"),
    "dieu-khoan": ("Điều khoản sử dụng", "Quy định khi mua sắm tại website.", "chinh-sach"),
    "gioi-thieu": ("Giới thiệu Nhịp Mobile", "Câu chuyện và cam kết của chúng tôi.", "ve"),
    "cua-hang": ("Hệ thống cửa hàng", "3 cửa hàng tại Hà Nội, Đà Nẵng, TP. Hồ Chí Minh.", "ve"),
    "lien-he": ("Liên hệ", "Gửi câu hỏi, chúng tôi trả lời trong 24 giờ.", "ve"),
}
GROUPS = [("mua", "Mua hàng"), ("chinh-sach", "Chính sách"), ("ve", "Về Nhịp Mobile")]
TOPICS = [("Đơn hàng", "don"), ("Thanh toán", "tt"), ("Giao hàng", "gh"), ("Đổi trả & bảo hành", "bh"), ("Tài khoản", "tk")]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.I)


@route("/tin-tuc")
def news(req):
    return req.render("shop/news.html", posts=content.post_list(req.db))


@route("/tin-tuc/<slug>")
def news_detail(req, slug):
    r = content.post_detail(req.db, slug)
    if not r:
        raise HttpError(404, "Bài viết không tồn tại hoặc đã bị gỡ.")
    post, items, others = r
    return req.render("shop/post.html", post=post, items=items, others=others)


@route("/ho-tro")
def help_center(req):
    return req.render("shop/help_center.html", help=HELP, groups=GROUPS)


def _help(req, slug, **ctx):
    title, desc, _ = HELP[slug]
    return req.render(f"shop/help/{slug}.html", slug=slug, title=title, desc=desc, help=HELP, groups=GROUPS, **ctx)


@route("/ho-tro/<slug>", methods=("GET", "POST"))
def help_page(req, slug):
    if slug not in HELP:
        raise HttpError(404, "Trang hỗ trợ này không tồn tại.")
    if slug == "cua-hang":
        return _help(req, slug, stores=db.all(req.db, "SELECT * FROM stores WHERE is_active=1 ORDER BY id"))
    if slug == "lien-he":
        return _contact(req, slug)
    if slug == "doi-tra-bao-hanh":
        return _warranty(req, slug)
    if req.method == "POST":
        raise HttpError(405)
    return _help(req, slug)


def _contact(req, slug):
    f, err, sent = {}, {}, req.query.get("da-gui") == "1"
    if req.user and req.method == "GET":
        f = {"name": req.user["full_name"], "email": req.user["email"]}
    if req.method == "POST":
        req.check_csrf()
        f = {k: (req.form.get(k) or "").strip() for k in ("name", "email", "topic", "order_code", "message")}
        if len(f["name"]) < 2:
            err["name"] = "Vui lòng nhập họ tên."
        if not EMAIL_RE.match(f["email"]):
            err["email"] = "Email chưa đúng, ví dụ ten@gmail.com."
        if f["topic"] not in dict((v, k) for k, v in TOPICS):
            err["topic"] = "Chọn chủ đề cần hỗ trợ."
        if len(f["message"]) < 10:
            err["message"] = "Nội dung tối thiểu 10 ký tự để chúng tôi hiểu rõ vấn đề."
        if len(f["message"]) > 2000:
            err["message"] = "Nội dung tối đa 2.000 ký tự."
        if not err:
            from html import escape
            topic = dict((v, k) for k, v in TOPICS)[f["topic"]]
            body = (f"<p><b>Liên hệ mới từ website</b></p><p>Họ tên: {escape(f['name'])}<br>Email: {escape(f['email'])}<br>"
                    f"Chủ đề: {topic}<br>Mã đơn: {escape(f['order_code'] or '—')}</p><p style=\"white-space:pre-line\">{escape(f['message'])}</p>")
            orders.send_mail(req.db, "hotro@nhipmobile.vn", f"[Liên hệ] {topic} – {f['name']}", body)
            orders.send_mail(req.db, f["email"], "Nhịp Mobile đã nhận câu hỏi của bạn",
                             f"<p>Chào {escape(f['name'])},</p><p>Chúng tôi đã nhận câu hỏi về <b>{topic}</b> và sẽ trả lời trong vòng 24 giờ làm việc.</p>"
                             f"<p style=\"white-space:pre-line;color:#6B7280\">{escape(f['message'])}</p>")
            return redirect("/ho-tro/lien-he?da-gui=1")
    return _help(req, slug, f=f, err=err, sent=sent, topics=TOPICS)


def _warranty(req, slug):
    result, error, f = None, "", {}
    if req.method == "POST":
        req.check_csrf()
        f = {"code": (req.form.get("code") or "").strip().upper(), "phone": (req.form.get("phone") or "").strip()}
        o = orders.find(req.db, f["code"], f["phone"])
        if not o:
            error = "Không tìm thấy đơn với mã và số điện thoại này. Kiểm tra lại mã đơn trong email xác nhận (dạng NM2611110001)."
        else:
            delivered, rows = content.warranty_lookup(req.db, o)
            result = {"o": o, "delivered": delivered, "rows": rows}
    return _help(req, slug, result=result, error=error, f=f)
