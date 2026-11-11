"""Bản đồ đường dẫn: mỗi địa chỉ (URL) ứng với một hàm xử lý."""
import re

_routes = []


def route(path, methods=("GET",)):
    """Đăng ký hàm xử lý cho một đường dẫn.

    Ví dụ: @route("/dien-thoai/<slug>") -> hàm nhận tham số slug.
    """
    pattern = "^" + re.sub(r"<(\w+)>", r"(?P<\1>[^/]+)", path.rstrip("/") or "/") + "/?$"
    rx = re.compile(pattern)

    def deco(fn):
        _routes.append((rx, tuple(m.upper() for m in methods), fn))
        return fn
    return deco


def match(method, path):
    allowed = False
    for rx, methods, fn in _routes:
        m = rx.match(path)
        if m:
            if method in methods or (method == "HEAD" and "GET" in methods):
                return fn, m.groupdict()
            allowed = True
    return (None, "method") if allowed else (None, None)
