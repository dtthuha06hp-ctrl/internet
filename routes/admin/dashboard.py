"""Tổng quan trang quản trị."""
from core import db, security
from core.router import route
from services import reports

STATUS_VI = {"pending": "Chờ xác nhận", "confirmed": "Đã xác nhận", "preparing": "Đang chuẩn bị", "shipping": "Đang giao",
             "delivery_failed": "Giao thất bại", "delivered": "Đã giao", "completed": "Hoàn tất", "returning": "Đổi / trả",
             "refunded": "Đã hoàn tiền", "cancelled": "Đã hủy"}


@route("/quan-tri")
def dashboard(req):
    req.require_role("admin", "staff")
    c = req.db
    d1, d2 = reports.period(30)
    days = reports.by_day(c, d1, d2)   # cùng cách tính với trang Báo cáo
    k = {
        "revenue30": sum(d["value"] for d in days),
        "today": db.scalar(c, "SELECT COUNT(*) FROM orders WHERE date(created_at)=date('now','localtime')"),
        "orders": db.scalar(c, "SELECT COUNT(*) FROM orders"),
        "pending": db.scalar(c, "SELECT COUNT(*) FROM orders WHERE status='pending'"),
    }
    chart = [{"label": d["label"], "value": d["value"], "h": d["h"]} for d in days]
    recent = [dict(r) for r in db.all(c, "SELECT * FROM orders ORDER BY created_at DESC LIMIT 8")]
    for o in recent:
        o["phone_shown"] = o["receiver_phone"] if req.user["role"] == "admin" else security.mask_phone(o["receiver_phone"])
    low = db.all(c, """SELECT p.name, v.sku, COALESCE(v.storage||' · ','')||v.color_name label, i.on_hand-i.reserved available
                       FROM inventory i JOIN product_variants v ON v.id=i.variant_id JOIN products p ON p.id=v.product_id
                       WHERE i.on_hand-i.reserved<=i.low_threshold AND v.is_active=1 ORDER BY available, p.name""")
    counts = [(label, db.scalar(c, f"SELECT COUNT(*) FROM {t}")) for label, t in (
        ("Sản phẩm", "products"), ("Phiên bản (SKU)", "product_variants"), ("Khách hàng", "customers"),
        ("Đơn hàng", "orders"), ("Đánh giá", "reviews"), ("Mã giảm giá", "vouchers"), ("Biến động kho", "inventory_transactions"))]
    return req.render("admin/dashboard.html", active="", k=k, chart=chart, recent=recent, low=low, counts=counts, status_vi=STATUS_VI)
