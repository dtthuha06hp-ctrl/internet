"""Cổng thanh toán mô phỏng theo cách VNPay làm việc (FR-20, TC-16).

Luồng thật của VNPay: khách trả tiền trên trang VNPay → VNPay gọi IPN (Instant Payment
Notification) về máy chủ cửa hàng kèm chữ ký HMAC-SHA512 → cửa hàng kiểm tra chữ ký và số tiền
rồi mới đánh dấu "đã thanh toán". Ở đây cổng là giả lập nhưng bước kiểm tra phía cửa hàng làm thật:

  - chữ ký sai            → mã 97, đơn KHÔNG đổi, ghi cảnh báo vào database/thanh-toan.log
  - không có đơn          → mã 01
  - số tiền không khớp    → mã 04 (chống sửa số tiền)
  - đơn đã thanh toán     → mã 02 (IPN gửi lặp lại không cộng tiền 2 lần)
  - hợp lệ                → mã 00
"""
import hashlib
import hmac
import os
from datetime import datetime

import config
from core import db, security
from services import orders

FIELDS = ("order_code", "amount", "result", "txn_ref")


def _canonical(params):
    return "&".join(f"{k}={params.get(k, '')}" for k in sorted(FIELDS))


def signature(params):
    return hmac.new(security.secret_key(), _canonical(params).encode(), hashlib.sha512).hexdigest()


def build_ipn(order, success):
    """Cổng giả lập tạo thông báo IPN có chữ ký đúng (như VNPay gửi về)."""
    p = {"order_code": order["order_code"], "amount": str(order["total"]), "result": "00" if success else "24",
         "txn_ref": f"VNP{datetime.now():%y%m%d%H%M%S}{order['id']}"}
    p["sig"] = signature(p)
    return p


def log_warning(msg, params):
    path = os.path.join(os.path.dirname(config.DB_PATH), "thanh-toan.log")
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} CẢNH BÁO {msg} | {_canonical(params)} | sig={str(params.get('sig', ''))[:16]}…\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)
    print("[Thanh toán]", line.strip())


def handle_ipn(conn, params):
    """Xử lý IPN. Trả về (mã, thông điệp, kết quả cho trang đặt hàng)."""
    params = {k: str(v) for k, v in (params or {}).items()}
    if not hmac.compare_digest(signature(params), params.get("sig", "")):
        log_warning("Chữ ký IPN không hợp lệ – bỏ qua", params)
        return "97", "Sai chữ ký", "loi"
    o = db.one(conn, "SELECT * FROM orders WHERE order_code=?", (params.get("order_code", ""),))
    if not o:
        log_warning("IPN cho đơn không tồn tại", params)
        return "01", "Không tìm thấy đơn", "loi"
    if params.get("amount") != str(o["total"]):
        log_warning(f"Số tiền IPN {params.get('amount')} khác tổng đơn {o['total']}", params)
        return "04", "Sai số tiền", "loi"
    if o["payment_status"] == "paid":
        return "02", "Đơn đã được xác nhận thanh toán trước đó", "already"
    try:
        result = orders.simulate_payment(conn, o["id"], params.get("result") == "00")
    except orders.OrderError:
        return "02", "Đơn không ở trạng thái chờ thanh toán", "loi"
    return "00", "Xác nhận thành công", result
