"""Chương trình "Giá sốc hôm nay": mỗi ngày một đợt, làm mới lúc 0 giờ."""
from datetime import datetime, timedelta
from core import db


def ensure_daily(conn):
    """Nếu hôm nay chưa có đợt giá sốc, tạo đợt mới từ danh sách SKU của đợt gần nhất."""
    now = datetime.now().replace(microsecond=0)
    day0 = now.replace(hour=0, minute=0, second=0)
    s = lambda d: d.isoformat(sep=" ")
    active = db.one(conn, "SELECT id FROM promotions WHERE is_active=1 AND starts_at<=? AND ends_at>=?", (s(now), s(now)))
    if active:
        return
    last = db.one(conn, "SELECT * FROM promotions WHERE name='Giá sốc hôm nay' ORDER BY ends_at DESC LIMIT 1")
    if not last:
        return
    with db.transaction(conn):
        new_id = conn.execute("INSERT INTO promotions(name,starts_at,ends_at) VALUES(?,?,?)",
                              (last["name"], s(day0), s(day0 + timedelta(days=1, seconds=-1)))).lastrowid
        conn.execute("""INSERT INTO promotion_items(promotion_id,variant_id,promo_price,quota,sold)
                        SELECT ?, variant_id, promo_price, quota, 0 FROM promotion_items WHERE promotion_id=?""",
                     (new_id, last["id"]))


# ----- Tự sang ngày mới khi web chạy qua nửa đêm (lỗi B4) -----
import threading  # noqa: E402
from datetime import date  # noqa: E402

_checked_day = None
_day_lock = threading.Lock()


def ensure_today(conn):
    """Gọi ở mỗi yêu cầu; chỉ thực sự làm việc một lần mỗi ngày (lần đầu sau 00:00)."""
    global _checked_day
    today = date.today()
    if _checked_day == today:
        return
    with _day_lock:
        if _checked_day != today:
            ensure_daily(conn)
            _checked_day = today
