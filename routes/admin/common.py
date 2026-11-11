"""Tiện ích dùng chung cho trang quản trị."""
from urllib.parse import urlencode
from core import security

PER_PAGE = 30


def staff(req):
    """Admin và nhân viên."""
    req.require_role("admin", "staff")


def admin(req):
    """Chỉ quản trị viên (sửa giá, kho, mã giảm giá, báo cáo...)."""
    req.require_role("admin")


def phone(req, p):
    return p if req.user["role"] == "admin" else security.mask_phone(p)


def pager(req, total, per=PER_PAGE):
    try:
        page = max(1, int(req.query.get("trang", 1)))
    except ValueError:
        page = 1
    pages = max(1, (total + per - 1) // per)
    page = min(page, pages)

    def url(n):
        q = {k: v for k, v in req.query.items() if k != "trang"}
        q["trang"] = n
        return req.path + "?" + urlencode(q)
    return {"page": page, "pages": pages, "offset": (page - 1) * per, "per": per, "total": total,
            "prev": url(page - 1) if page > 1 else "", "next": url(page + 1) if page < pages else ""}
