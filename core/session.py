"""Ghi nhớ người dùng giữa các lần tải trang (qua cookie)."""
from datetime import datetime, timedelta
import config
from core import security

COOKIE = "nm_sid"


def now():
    return datetime.now().isoformat(timespec="seconds")


def load(conn, token):
    if not token:
        return None
    row = conn.execute("SELECT * FROM sessions WHERE token=? AND expires_at>?", (token, now())).fetchone()
    return dict(row) if row else None


def create(conn, user_id=None):
    token = security.new_token()
    exp = (datetime.now() + timedelta(days=config.SESSION_DAYS)).isoformat(timespec="seconds")
    conn.execute("INSERT INTO sessions(token,user_id,csrf_token,expires_at,created_at) VALUES(?,?,?,?,?)",
                 (token, user_id, security.new_token(16), exp, now()))
    return load(conn, token)


def set_user(conn, sess, user_id):
    """Đổi mã phiên khi đăng nhập/đăng xuất để chống chiếm phiên."""
    new = create(conn, user_id)
    if sess:
        conn.execute("UPDATE carts SET session_token=? WHERE session_token=? AND status='active'",
                     (new["token"], sess["token"]))
        conn.execute("DELETE FROM sessions WHERE token=?", (sess["token"],))
    return new


def cleanup(conn):
    conn.execute("DELETE FROM sessions WHERE expires_at<=?", (now(),))
