"""Biến động kho: mọi thay đổi tồn kho đều đi qua đây và được ghi nhật ký (inventory_transactions)."""
from datetime import datetime
from core import db


class StockError(Exception):
    pass


def now():
    return datetime.now().isoformat(sep=" ", timespec="seconds")


def move(conn, variant_id, typ, qty, reason=None, order_id=None, user_id=None):
    """typ: import (+tồn), reserve (+giữ), release (−giữ), sale (−tồn −giữ), return (+tồn), adjust (±tồn)."""
    t = now()
    if typ == "import":
        if qty <= 0:
            raise StockError("Số lượng nhập phải lớn hơn 0.")
        conn.execute("UPDATE inventory SET on_hand=on_hand+?, updated_at=? WHERE variant_id=?", (qty, t, variant_id))
        change = qty
    elif typ == "reserve":
        cur = conn.execute("UPDATE inventory SET reserved=reserved+?, updated_at=? WHERE variant_id=? AND on_hand-reserved>=?",
                           (qty, t, variant_id, qty))
        if cur.rowcount != 1:
            raise StockError("Không đủ hàng để giữ.")
        change = qty
    elif typ == "release":
        conn.execute("UPDATE inventory SET reserved=reserved-?, updated_at=? WHERE variant_id=?", (qty, t, variant_id))
        change = -qty
    elif typ == "sale":
        conn.execute("UPDATE inventory SET on_hand=on_hand-?, reserved=reserved-?, updated_at=? WHERE variant_id=?", (qty, qty, t, variant_id))
        change = -qty
    elif typ == "return":
        conn.execute("UPDATE inventory SET on_hand=on_hand+?, updated_at=? WHERE variant_id=?", (qty, t, variant_id))
        change = qty
    elif typ == "adjust":
        if not reason:
            raise StockError("Điều chỉnh kho bắt buộc ghi lý do.")
        if qty == 0:
            raise StockError("Số lượng điều chỉnh phải khác 0.")
        cur = conn.execute("UPDATE inventory SET on_hand=on_hand+?, updated_at=? WHERE variant_id=? AND on_hand+?>=reserved",
                           (qty, t, variant_id, qty))
        if cur.rowcount != 1:
            raise StockError("Không thể giảm thấp hơn số đang giữ cho đơn chưa giao.")
        change = qty
    else:
        raise StockError(typ)
    conn.execute("""INSERT INTO inventory_transactions(variant_id,type,qty_change,reason,order_id,created_by,created_at)
                    VALUES(?,?,?,?,?,?,?)""", (variant_id, typ, change, reason, order_id, user_id, t))


def ensure_row(conn, variant_id, low=5):
    if not db.scalar(conn, "SELECT 1 FROM inventory WHERE variant_id=?", (variant_id,)):
        conn.execute("INSERT INTO inventory(variant_id,on_hand,reserved,low_threshold,updated_at) VALUES(?,0,0,?,?)", (variant_id, low, now()))
