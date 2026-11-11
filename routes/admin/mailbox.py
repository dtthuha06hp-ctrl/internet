"""Hộp thư mô phỏng: xem các "email" hệ thống đã gửi cho khách."""
from core import db
from core.router import route
from core.server import Response


@route("/quan-tri/hop-thu")
def inbox(req):
    req.require_role("admin", "staff")
    mails = db.all(req.db, """SELECT e.*, o.order_code FROM email_outbox e LEFT JOIN orders o ON o.id=e.order_id
                              ORDER BY e.created_at DESC, e.id DESC LIMIT 200""")
    sel = None
    mid = req.query.get("id")
    if mid and mid.isdigit():
        sel = db.one(req.db, "SELECT * FROM email_outbox WHERE id=?", (int(mid),))
    elif mails:
        sel = mails[0]
    return req.render("admin/mailbox.html", mails=mails, sel=sel, active="hop-thu")


@route("/quan-tri/hop-thu/<mid>/noi-dung")
def body(req, mid):
    """Nội dung email hiển thị trong khung riêng (iframe) để không lẫn kiểu chữ với trang quản trị."""
    req.require_role("admin", "staff")
    m = db.one(req.db, "SELECT body_html FROM email_outbox WHERE id=?", (int(mid) if mid.isdigit() else 0,))
    return Response(m["body_html"] if m else "", headers={"Content-Security-Policy": "default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'"})
