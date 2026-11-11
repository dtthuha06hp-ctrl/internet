"""Kiểm tra và tính tiền giảm của mã giảm giá."""
from datetime import datetime
from core import db
from core.template import vnd


class VoucherError(Exception):
    pass


def is_shipping_voucher(v):
    """Mã bắt đầu bằng FREESHIP chỉ trừ vào phí giao hàng."""
    return v["code"].upper().startswith("FREESHIP")


def check(conn, code, subtotal, shipping_fee=0, customer_id=None):
    """Trả về (bản ghi mã, số tiền giảm). Báo VoucherError với lý do rõ ràng nếu không dùng được."""
    code = (code or "").strip().upper()
    if not code:
        raise VoucherError("Bạn chưa nhập mã giảm giá.")
    v = db.one(conn, "SELECT * FROM vouchers WHERE upper(code)=?", (code,))
    if not v or not v["is_active"]:
        raise VoucherError(f"Mã {code} không tồn tại. Kiểm tra lại chính tả.")
    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    if v["starts_at"] and now < v["starts_at"]:
        raise VoucherError(f"Mã {code} chưa đến thời gian áp dụng.")
    if v["ends_at"] and now > v["ends_at"]:
        raise VoucherError(f"Mã {code} đã hết hạn.")
    if v["usage_limit"] is not None and v["used_count"] >= v["usage_limit"]:
        raise VoucherError(f"Mã {code} đã hết lượt sử dụng.")
    if subtotal < v["min_order"]:
        raise VoucherError(f"Mã {code} áp dụng cho đơn từ {vnd(v['min_order'])}. "
                           f"Bạn cần mua thêm {vnd(v['min_order'] - subtotal)}.")
    if customer_id:
        used = db.scalar(conn, """SELECT COUNT(*) FROM voucher_usages u JOIN orders o ON o.id=u.order_id
                                  WHERE u.voucher_id=? AND u.customer_id=? AND o.status<>'cancelled'""", (v["id"], customer_id))
        if used >= v["per_customer_limit"]:
            raise VoucherError(f"Bạn đã dùng mã {code} rồi (mỗi khách {v['per_customer_limit']} lần).")
    if is_shipping_voucher(v):
        discount = min(v["value"], shipping_fee)
    elif v["type"] == "percent":
        discount = subtotal * v["value"] // 100
        if v["max_discount"]:
            discount = min(discount, v["max_discount"])
    else:
        discount = min(v["value"], subtotal)
    return dict(v), int(discount)
