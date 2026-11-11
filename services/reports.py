"""Báo cáo bán hàng.

Quy ước: DOANH THU = tổng tiền các đơn đã HOÀN TẤT, tính theo ngày hoàn tất
(giống trang Tổng quan). Đơn mới đặt / đang giao chưa được tính là doanh thu.
"""
from datetime import date, timedelta
from core import db

DONE = """SELECT o.*, date(h.changed_at) done_day FROM orders o JOIN order_status_history h
          ON h.order_id=o.id AND h.to_status='completed' WHERE o.status='completed' AND date(h.changed_at) BETWEEN ? AND ?"""


def period(days):
    d2 = date.today()
    d1 = d2 - timedelta(days=days - 1)
    return d1.isoformat(), d2.isoformat()


def summary(conn, d1, d2):
    done = db.one(conn, f"SELECT COUNT(*) n, COALESCE(SUM(total),0) rev, COALESCE(SUM(discount_amount),0) disc FROM ({DONE})", (d1, d2))
    placed = db.one(conn, """SELECT COUNT(*) n, SUM(status='cancelled') cancelled, COALESCE(SUM(CASE WHEN status<>'cancelled' THEN total END),0) value
                             FROM orders WHERE date(created_at) BETWEEN ? AND ?""", (d1, d2))
    new_cus = db.scalar(conn, "SELECT COUNT(*) FROM customers WHERE date(created_at) BETWEEN ? AND ?", (d1, d2))
    return {
        "revenue": done["rev"], "done": done["n"], "discount": done["disc"],
        "aov": done["rev"] // done["n"] if done["n"] else 0,
        "placed": placed["n"], "placed_value": placed["value"], "cancelled": placed["cancelled"] or 0,
        "cancel_rate": round((placed["cancelled"] or 0) * 100 / placed["n"], 1) if placed["n"] else 0,
        "new_customers": new_cus,
    }


def by_day(conn, d1, d2):
    rows = {r["done_day"]: (r["v"], r["n"]) for r in db.all(conn, f"SELECT done_day, SUM(total) v, COUNT(*) n FROM ({DONE}) GROUP BY done_day", (d1, d2))}
    start, end = date.fromisoformat(d1), date.fromisoformat(d2)
    out, d = [], start
    while d <= end:
        v, n = rows.get(d.isoformat(), (0, 0))
        out.append({"day": d.isoformat(), "label": d.strftime("%d/%m"), "value": v, "orders": n})
        d += timedelta(days=1)
    mx = max([x["value"] for x in out] + [1])
    for x in out:
        x["h"] = round(x["value"] * 100 / mx)
    return out


def top_products(conn, d1, d2, limit=10):
    return db.all(conn, f"""SELECT i.product_name name, SUM(i.quantity) qty, SUM(i.line_total) revenue, COUNT(DISTINCT o.id) orders
                            FROM ({DONE}) o JOIN order_items i ON i.order_id=o.id
                            GROUP BY i.product_name ORDER BY revenue DESC LIMIT ?""", (d1, d2, limit))


def by_category(conn, d1, d2):
    rows = [dict(r) for r in db.all(conn, f"""SELECT CASE WHEN c.kind='phone' THEN 'Điện thoại' ELSE c.name END cat,
                            SUM(i.line_total) revenue, SUM(i.quantity) qty
                            FROM ({DONE}) o JOIN order_items i ON i.order_id=o.id JOIN product_variants v ON v.id=i.variant_id
                            JOIN products p ON p.id=v.product_id JOIN categories c ON c.id=p.category_id
                            GROUP BY cat ORDER BY revenue DESC""", (d1, d2))]
    total = sum(r["revenue"] for r in rows) or 1
    for r in rows:
        r["pct"] = round(r["revenue"] * 100 / total, 1)
    return rows


def payment_mix(conn, d1, d2):
    names = {"cod": "Tiền mặt khi nhận (COD)", "bank_qr": "Chuyển khoản QR", "ewallet": "Ví điện tử"}
    rows = [dict(r) for r in db.all(conn, f"SELECT payment_method m, COUNT(*) n, SUM(total) v FROM ({DONE}) GROUP BY m ORDER BY v DESC", (d1, d2))]
    total = sum(r["v"] for r in rows) or 1
    for r in rows:
        r["name"], r["pct"] = names[r["m"]], round(r["v"] * 100 / total, 1)
    return rows


def cancel_reasons(conn, d1, d2):
    return db.all(conn, """SELECT COALESCE(cancel_reason,'Khác') reason, COUNT(*) n FROM orders WHERE status='cancelled'
                           AND date(created_at) BETWEEN ? AND ? GROUP BY reason ORDER BY n DESC""", (d1, d2))


def orders_csv_rows(conn, d1, d2):
    from services.orders import STATUS_VI
    pay_st = {'unpaid': 'Chưa thanh toán', 'pending': 'Chờ thanh toán', 'paid': 'Đã thanh toán', 'refunded': 'Đã hoàn tiền'}
    head = ["Mã đơn", "Ngày đặt", "Khách hàng", "Nhận hàng", "Tỉnh/Thành", "Tạm tính", "Giảm giá", "Phí giao", "Tổng tiền",
            "Thanh toán", "TT thanh toán", "Trạng thái", "Lý do hủy"]
    out = [head]
    for o in db.all(conn, "SELECT * FROM orders WHERE date(created_at) BETWEEN ? AND ? ORDER BY created_at", (d1, d2)):
        prov = (o["shipping_address"] or "").rsplit(",", 1)[-1].strip() if o["delivery_method"] == "home" else ""
        out.append([o["order_code"], o["created_at"], o["receiver_name"], "Giao tận nơi" if o["delivery_method"] == "home" else "Tại cửa hàng",
                    prov, o["subtotal"], o["discount_amount"], o["shipping_fee"], o["total"],
                    {"cod": "COD", "bank_qr": "Chuyển khoản", "ewallet": "Ví"}[o["payment_method"]], pay_st[o["payment_status"]],
                    STATUS_VI[o["status"]], o["cancel_reason"] or ""])
    return out


def to_csv(rows):
    import csv
    import io
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    return "﻿" + buf.getvalue()   # BOM để Excel đọc đúng tiếng Việt
