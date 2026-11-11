"""Mã giảm giá, banner, giá sốc, duyệt đánh giá (phía quản trị)."""
import re
from datetime import datetime
from core import db
from services.admin_catalog import money


class MarketingError(Exception):
    pass


def _dt(s, end=False):
    """Nhận '2026-11-30' hoặc '2026-11-30T10:00' từ ô chọn ngày; trả về chuỗi lưu DB hoặc None."""
    s = (s or "").strip().replace("T", " ")
    if not s:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        s += " 23:59:59" if end else " 00:00:00"
    elif re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", s):
        s += ":59" if end else ":00"
    try:
        datetime.fromisoformat(s)
    except ValueError:
        raise MarketingError("Ngày giờ không hợp lệ.")
    return s


# ---------------- Mã giảm giá ----------------
def voucher_state(v, now=None):
    now = now or datetime.now().isoformat(sep=" ", timespec="seconds")
    if not v["is_active"]:
        return "off", "Đã tắt"
    if v["ends_at"] and now > v["ends_at"]:
        return "off", "Hết hạn"
    if v["starts_at"] and now < v["starts_at"]:
        return "warn", "Chưa bắt đầu"
    if v["usage_limit"] is not None and v["used_count"] >= v["usage_limit"]:
        return "off", "Hết lượt"
    return "on", "Đang chạy"


def save_voucher(conn, form, vid=None):
    code = re.sub(r"\s+", "", (form.get("code") or "")).upper()
    typ = form.get("type")
    value = money(form.get("value"))
    if not re.fullmatch(r"[A-Z0-9]{4,20}", code):
        raise MarketingError("Mã gồm 4–20 chữ in hoa hoặc số, không dấu, không khoảng trắng.")
    if db.scalar(conn, "SELECT 1 FROM vouchers WHERE upper(code)=? AND id<>?", (code, vid or 0)):
        raise MarketingError(f"Mã {code} đã tồn tại.")
    if typ not in ("fixed", "percent"):
        raise MarketingError("Chọn loại giảm.")
    if value <= 0 or (typ == "percent" and value > 100):
        raise MarketingError("Mức giảm phải lớn hơn 0 (phần trăm tối đa 100).")
    limit = money(form.get("usage_limit")) or None
    per = money(form.get("per_customer_limit")) or 1
    starts, ends = _dt(form.get("starts_at")), _dt(form.get("ends_at"), end=True)
    if starts and ends and ends <= starts:
        raise MarketingError("Ngày kết thúc phải sau ngày bắt đầu.")
    vals = (code, (form.get("description") or "").strip() or None, typ, value, money(form.get("max_discount")) or None,
            money(form.get("min_order")), limit, per, starts, ends, 1 if form.get("is_active") == "1" else 0)
    if vid:
        conn.execute("""UPDATE vouchers SET code=?, description=?, type=?, value=?, max_discount=?, min_order=?, usage_limit=?,
                        per_customer_limit=?, starts_at=?, ends_at=?, is_active=? WHERE id=?""", vals + (vid,))
        return vid
    return conn.execute("""INSERT INTO vouchers(code,description,type,value,max_discount,min_order,usage_limit,per_customer_limit,
                           starts_at,ends_at,is_active) VALUES(?,?,?,?,?,?,?,?,?,?,?)""", vals).lastrowid


# ---------------- Banner ----------------
def save_banner(conn, form, bid):
    title = (form.get("title") or "").strip()
    if len(title) < 3:
        raise MarketingError("Tiêu đề banner quá ngắn.")
    link = (form.get("link_url") or "").strip()
    if link and not link.startswith("/"):
        raise MarketingError("Đường dẫn phải bắt đầu bằng / (trang trong website), ví dụ /dien-thoai/iphone-17.")
    color = (form.get("bg_color") or "").strip()
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
        raise MarketingError("Màu nền dạng #RRGGBB.")
    pid = form.get("product_id") or ""
    conn.execute("""UPDATE banners SET title=?, subtitle=?, link_url=?, bg_color=?, product_id=?, sort_order=?, is_active=? WHERE id=?""",
                 (title, (form.get("subtitle") or "").strip() or None, link or None, color.upper(),
                  int(pid) if pid.isdigit() else None, money(form.get("sort_order")), 1 if form.get("is_active") == "1" else 0, bid))


# ---------------- Giá sốc ----------------
def current_promotion(conn):
    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    return db.one(conn, "SELECT * FROM promotions WHERE is_active=1 AND starts_at<=? AND ends_at>=? ORDER BY id DESC LIMIT 1", (now, now))


def save_flash_item(conn, promo_id, form, item_id=None):
    price, quota = money(form.get("promo_price")), money(form.get("quota"))
    if item_id:
        it = db.one(conn, "SELECT * FROM promotion_items WHERE id=? AND promotion_id=?", (item_id, promo_id))
        if not it:
            raise MarketingError("Không tìm thấy sản phẩm trong đợt giá sốc.")
        vid, sold = it["variant_id"], it["sold"]
    else:
        vid, sold = int(form.get("variant_id") or 0), 0
        if db.scalar(conn, "SELECT 1 FROM promotion_items WHERE promotion_id=? AND variant_id=?", (promo_id, vid)):
            raise MarketingError("Phiên bản này đã có trong đợt giá sốc.")
    v = db.one(conn, "SELECT * FROM product_variants WHERE id=?", (vid,))
    if not v:
        raise MarketingError("Chọn phiên bản sản phẩm.")
    if price <= 0 or price >= v["sale_price"]:
        raise MarketingError(f"Giá sốc phải thấp hơn giá bán thường ({v['sale_price']:,}₫).".replace(",", "."))
    if quota < max(1, sold):
        raise MarketingError(f"Số suất phải ít nhất {max(1, sold)} (đã bán {sold}).")
    if item_id:
        conn.execute("UPDATE promotion_items SET promo_price=?, quota=? WHERE id=?", (price, quota, item_id))
    else:
        conn.execute("INSERT INTO promotion_items(promotion_id,variant_id,promo_price,quota) VALUES(?,?,?,?)", (promo_id, vid, price, quota))


def remove_flash_item(conn, promo_id, item_id):
    conn.execute("DELETE FROM promotion_items WHERE id=? AND promotion_id=?", (item_id, promo_id))


# ---------------- Đánh giá ----------------
def refresh_rating(conn, pid):
    conn.execute("""UPDATE products SET
        rating_count=(SELECT COUNT(*) FROM reviews r WHERE r.product_id=products.id AND r.status='approved'),
        rating_avg=COALESCE((SELECT ROUND(AVG(rating),1) FROM reviews r WHERE r.product_id=products.id AND r.status='approved'),0)
        WHERE id=?""", (pid,))


def moderate(conn, review_id, status):
    if status not in ("approved", "hidden"):
        raise MarketingError("Thao tác không hợp lệ.")
    r = db.one(conn, "SELECT * FROM reviews WHERE id=?", (review_id,))
    if not r:
        raise MarketingError("Không tìm thấy đánh giá.")
    with db.transaction(conn):
        conn.execute("UPDATE reviews SET status=? WHERE id=?", (status, review_id))
        refresh_rating(conn, r["product_id"])
