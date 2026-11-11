"""Cấu hình chung của website Nhịp Mobile.

Bạn có thể sửa các con số ở đây (phí giao, giới hạn số lượng...) mà không cần đụng vào phần còn lại.
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "nhipmobile.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "database", "schema.sql")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

# Máy chủ: mặc định chạy trên chính máy tính của bạn.
# Khi đưa lên mạng (Render…), các giá trị này lấy từ biến môi trường do nhà cung cấp đặt.
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", 8000))   # nếu cổng bận, chương trình tự thử 8001, 8002...
ON_SERVER = os.environ.get("NHIP_ONLINE") == "1"   # đang chạy trên máy chủ thật (sau proxy HTTPS)
if ON_SERVER and not os.environ.get("TZ"):
    # Máy chủ Render chạy giờ quốc tế (UTC). Đặt giờ Việt Nam (UTC+7) để giá sốc đổi ngày đúng 00:00,
    # giờ đặt hàng, báo cáo theo ngày… khớp với người dùng. "ICT-7" không cần gói dữ liệu múi giờ.
    import time as _time
    os.environ["TZ"] = "ICT-7"
    if hasattr(_time, "tzset"):
        _time.tzset()

# Mật khẩu tài khoản quản trị / nhân viên khi tạo dữ liệu mẫu.
# Bản chạy trên máy: giữ mật khẩu demo. Bản đưa lên mạng: đặt ADMIN_PASSWORD, STAFF_PASSWORD riêng.
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD") or "Admin@123"
STAFF_PASSWORD = os.environ.get("STAFF_PASSWORD") or "Nhanvien@123"

SHOP_NAME = "Nhịp Mobile"
SLOGAN = "Giá rõ ràng. Chọn máy dễ dàng."
HOTLINE = "1800 6868"
EMAIL = "hotro@nhipmobile.vn"

# Quy tắc nghiệp vụ (Phần 6.6 tài liệu)
MAX_QTY_PER_ITEM = 3            # tối đa 3 cái mỗi phiên bản trong một đơn
MAX_PENDING_ORDERS_PER_PHONE = 3
FREE_SHIP_FROM = 500_000        # miễn phí giao cho đơn từ 500.000đ
SHIPPING_FEE = 30_000
LOW_STOCK_DEFAULT = 5

# Bảo mật
SESSION_DAYS = 7
MAX_FAILED_LOGINS = 5
LOCK_MINUTES = 15
PASSWORD_ITERATIONS = 120_000

CONSENT_VERSION = "2026-11"
