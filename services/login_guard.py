"""Chống dò mật khẩu mà không cho người khác khóa được tài khoản của bạn (lỗi B2).

Trước đây: sai 5 lần → khóa cả tài khoản 15 phút, nên ai biết email cũng khóa được chủ shop.
Bây giờ: đếm lần sai theo cặp (máy gõ, tài khoản).
  - Sai 5 lần từ cùng một máy → chỉ MÁY ĐÓ bị chặn đăng nhập tài khoản đó 15 phút.
    Chủ tài khoản ở máy khác vẫn đăng nhập bình thường.
  - Một máy sai tổng cộng 20 lần (dò nhiều tài khoản) → máy đó bị chặn 15 phút với mọi tài khoản.
Đăng nhập đúng thì xóa bộ đếm của cặp đó. Dữ liệu giữ trong bộ nhớ, tắt web là tự xóa.
"""
import threading
import time

import config

PER_IP_LIMIT = 20
_lock = threading.Lock()
_fails = {}      # khóa -> danh sách thời điểm sai (giây)
_blocked = {}    # khóa -> thời điểm hết chặn


def _window():
    return config.LOCK_MINUTES * 60


def blocked_minutes(ip, login):
    """Còn bị chặn bao nhiêu phút (0 = không bị chặn)."""
    now = time.time()
    with _lock:
        until = max(_blocked.get(("pair", ip, login), 0), _blocked.get(("ip", ip), 0))
    return int((until - now) // 60) + 1 if until > now else 0


def fail(ip, login):
    """Ghi một lần sai. Trả về (số lần còn lại cho cặp này, vừa bị chặn hay không)."""
    now = time.time()
    with _lock:
        out = None
        for key, limit in ((("pair", ip, login), config.MAX_FAILED_LOGINS), (("ip", ip), PER_IP_LIMIT)):
            ts = [t for t in _fails.get(key, []) if now - t < _window()] + [now]
            _fails[key] = ts
            if len(ts) >= limit:
                _blocked[key] = now + _window()
                _fails[key] = []
            if key[0] == "pair":
                out = (max(0, limit - len(ts)), len(ts) >= limit)
        return out


def success(ip, login):
    with _lock:
        _fails.pop(("pair", ip, login), None)
        _blocked.pop(("pair", ip, login), None)


def reset():
    """Dùng cho kiểm thử."""
    with _lock:
        _fails.clear()
        _blocked.clear()
