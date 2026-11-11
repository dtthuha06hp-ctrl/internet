"""Máy chủ web: nhận yêu cầu từ trình duyệt, gọi đúng hàm xử lý, trả trang về."""
import json
import mimetypes
import os
import traceback
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs, quote

import config
from core import db, router, session, template

mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("image/webp", ".webp")


class HttpError(Exception):
    def __init__(self, status, message=""):
        super().__init__(message)
        self.status, self.message = status, message


class Response:
    def __init__(self, body=b"", status=200, content_type="text/html; charset=utf-8", headers=None):
        self.body = body.encode("utf-8") if isinstance(body, str) else body
        self.status = status
        self.headers = {"Content-Type": content_type}
        self.headers.update(headers or {})
        self.cookies = []


def redirect(url, status=303):
    return Response(b"", status, headers={"Location": url})


def json_response(data, status=200):
    return Response(json.dumps(data, ensure_ascii=False), status, "application/json; charset=utf-8")


def _parse_multipart(raw, ctype):
    """Đọc form có tải tệp (ảnh sản phẩm). Trả về (trường chữ, tệp)."""
    from email import message_from_bytes
    from email.policy import HTTP
    msg = message_from_bytes(b"Content-Type: " + ctype.encode() + b"\r\n\r\n" + raw, policy=HTTP)
    fields, files = {}, {}
    for part in msg.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        filename = part.get_filename()
        data = part.get_payload(decode=True) or b""
        if filename:
            files.setdefault(name, []).append({"filename": filename, "data": data, "type": part.get_content_type()})
        else:
            fields.setdefault(name, []).append(data.decode("utf-8", "replace"))
    return fields, files


class Request:
    def __init__(self, handler, method):
        self.method = method
        self.ip = handler.client_address[0] if handler.client_address else "local"
        if config.ON_SERVER:   # sau proxy của nhà cung cấp: địa chỉ thật của người dùng nằm trong X-Forwarded-For
            fwd = (handler.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
            self.ip = fwd or self.ip
        parts = urlsplit(handler.path)
        self.path = parts.path
        self.full_path = handler.path
        self.query = {k: v[0] for k, v in parse_qs(parts.query, keep_blank_values=True).items()}
        self.query_list = parse_qs(parts.query, keep_blank_values=True)
        self.headers = handler.headers
        jar = cookies.SimpleCookie(handler.headers.get("Cookie", ""))
        self.cookies = {k: m.value for k, m in jar.items()}
        self.form, self.form_list, self.json, self.files = {}, {}, None, {}
        if method == "POST":
            n = int(handler.headers.get("Content-Length") or 0)
            raw = handler.rfile.read(min(n, 5_000_000)) if n else b""
            ctype = handler.headers.get("Content-Type", "")
            if "application/json" in ctype:
                self.json = json.loads(raw or b"null")
            elif "multipart/form-data" in ctype:
                self.form_list, self.files = _parse_multipart(raw, ctype)
                self.form = {k: v[0] for k, v in self.form_list.items()}
            else:
                self.form_list = parse_qs(raw.decode("utf-8", "replace"), keep_blank_values=True)
                self.form = {k: v[0] for k, v in self.form_list.items()}
        self.db = None
        self.session = None
        self.user = None
        self.flash = []

    # ----- tiện ích cho hàm xử lý -----
    def render(self, name, status=200, **ctx):
        base = {
            "req": self, "user": self.user, "path": self.path,
            "csrf": self.session["csrf_token"] if self.session else "",
            "cart_count": self.cart_count(), "cfg": config, "flash": self.flash,
        }
        base.update(ctx)
        return Response(template.render(name, **base), status)

    def cart_count(self):
        if not self.session or not self.db:
            return 0
        n = db.scalar(self.db, """SELECT COALESCE(SUM(ci.quantity),0) FROM cart_items ci JOIN carts c ON c.id=ci.cart_id
                                 WHERE c.status='active' AND c.session_token=?""", (self.session["token"],))
        return n or 0

    def check_csrf(self):
        token = self.form.get("csrf") or (self.json or {}).get("csrf") or self.headers.get("X-CSRF-Token")
        if not self.session or token != self.session["csrf_token"]:
            raise HttpError(403, "Phiên làm việc đã hết hạn. Hãy tải lại trang rồi thử lại.")

    def require_role(self, *roles):
        if not self.user:
            raise HttpError(302, "/dang-nhap?next=" + quote(self.full_path))
        if self.user["role"] not in roles:
            raise HttpError(403, "Tài khoản của bạn không có quyền vào trang này.")


class Handler(BaseHTTPRequestHandler):
    server_version = "NhipMobile/1.0"

    def log_message(self, fmt, *args):
        pass  # giữ cửa sổ dòng lệnh gọn gàng

    def do_GET(self):
        self._handle("GET")

    def do_HEAD(self):
        self._handle("HEAD")

    def do_POST(self):
        self._handle("POST")

    def _static(self, path):
        for prefix, root in (("/static/", config.STATIC_DIR), ("/uploads/", config.UPLOAD_DIR)):
            if path.startswith(prefix):
                rel = path[len(prefix):]
                full = os.path.realpath(os.path.join(root, rel))
                if not full.startswith(os.path.realpath(root) + os.sep) or not os.path.isfile(full):
                    return Response("Không tìm thấy", 404, "text/plain; charset=utf-8")
                ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
                with open(full, "rb") as f:
                    return Response(f.read(), 200, ctype, {"Cache-Control": "no-cache"})
        return None

    def _handle(self, method):
        req = Request(self, method)
        resp = self._static(req.path) if method in ("GET", "HEAD") else None
        if resp is None:
            conn = db.connect()
            req.db = conn
            try:
                from services import promotions
                promotions.ensure_today(conn)   # sang ngày mới thì tạo đợt giá sốc mới
                req.session = session.load(conn, req.cookies.get(session.COOKIE))
                new_cookie = False
                if not req.session:
                    req.session = session.create(conn)
                    new_cookie = True
                if req.session.get("user_id"):
                    u = db.one(conn, "SELECT * FROM users WHERE id=? AND status='active'", (req.session["user_id"],))
                    req.user = dict(u) if u else None
                fn, params = router.match(method, req.path)
                if fn is None:
                    raise HttpError(405 if params == "method" else 404)
                resp = fn(req, **params)
                if isinstance(resp, str):
                    resp = Response(resp)
                if new_cookie or getattr(req, "_session_changed", False):
                    resp.cookies.append(req.session["token"])
            except HttpError as e:
                if e.status == 302:
                    resp = redirect(e.message, 302)
                else:
                    resp = self._error(req, e.status, e.message)
            except Exception:
                traceback.print_exc()
                resp = self._error(req, 500, "")
            finally:
                conn.close()
        self.send_response(resp.status)
        for k, v in resp.headers.items():
            self.send_header(k, v)
        for tok in resp.cookies:
            secure = "; Secure" if config.ON_SERVER else ""   # trên mạng chạy HTTPS: cookie chỉ gửi qua kết nối mã hóa
            self.send_header("Set-Cookie", f"{session.COOKIE}={tok}; Path=/; HttpOnly; SameSite=Lax; Max-Age={config.SESSION_DAYS*86400}{secure}")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Content-Length", str(len(resp.body)))
        self.end_headers()
        if method != "HEAD":
            self.wfile.write(resp.body)

    def _error(self, req, status, message):
        titles = {403: "Không có quyền truy cập", 404: "Không tìm thấy trang", 405: "Thao tác không hợp lệ",
                  500: "Có lỗi xảy ra"}
        msgs = {404: "Trang bạn tìm không tồn tại hoặc đã được chuyển đi.",
                500: "Máy chủ gặp lỗi khi xử lý. Chi tiết lỗi đã được in ra cửa sổ dòng lệnh."}
        try:
            return req.render("shop/error.html", status=status, code=status, title=titles.get(status, "Lỗi"),
                              message=message or msgs.get(status, ""))
        except Exception:
            traceback.print_exc()
            return Response(f"<h1>{status}</h1><p>{message}</p>", status)


def serve(host, port):
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.daemon_threads = True
    return httpd
