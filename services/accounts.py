"""Đăng nhập, khóa tài khoản khi sai nhiều lần."""
from datetime import datetime, timedelta
import config
from core import db, security


class LoginError(Exception):
    pass


def authenticate(conn, login, password, ip="local"):
    """Đăng nhập. Sai 5 lần từ cùng một máy thì máy đó bị chặn 15 phút (xem services/login_guard.py)."""
    from services import login_guard as guard
    login = (login or "").strip().lower()
    generic = "Email/SĐT hoặc mật khẩu chưa đúng."
    mins = guard.blocked_minutes(ip, login)
    if mins:
        raise LoginError(f"Bạn đã nhập sai {config.MAX_FAILED_LOGINS} lần. Đăng nhập tạm khóa trên thiết bị này, thử lại sau {mins} phút.")
    user = db.one(conn, "SELECT * FROM users WHERE lower(email)=? OR phone=?", (login, login))
    if user and user["status"] != "active" and security.verify_password(password or "", user["password_hash"]):
        raise LoginError("Tài khoản đã bị khóa. Liên hệ hotline để được hỗ trợ.")
    if not user or not security.verify_password(password or "", user["password_hash"]):
        # tài khoản có hay không đều nhận cùng một thông báo, không lộ email nào đã đăng ký
        left, now_blocked = guard.fail(ip, login)
        if now_blocked:
            raise LoginError(f"Bạn đã nhập sai {config.MAX_FAILED_LOGINS} lần. Đăng nhập tạm khóa {config.LOCK_MINUTES} phút trên thiết bị này.")
        raise LoginError(f"{generic} Còn {left} lần thử trước khi tạm khóa.")
    guard.success(ip, login)
    return dict(user)


# =====================================================================
#  Giai đoạn 4: đăng ký, hồ sơ, mật khẩu, sổ địa chỉ, yêu thích
# =====================================================================
import re  # noqa: E402
from services import orders as orders_svc  # noqa: E402


class AccountError(Exception):
    def __init__(self, message, field=None):
        super().__init__(message)
        self.field = field or {}


def _now():
    return datetime.now().isoformat(sep=" ", timespec="seconds")


def check_password_rule(pw):
    if len(pw or "") < 8 or not re.search(r"[A-Za-z]", pw) or not re.search(r"\d", pw):
        return "Mật khẩu cần ít nhất 8 ký tự, gồm cả chữ và số."
    return ""


def register(conn, form):
    f = {k: (form.get(k) or "").strip() for k in ("title", "full_name", "phone", "email", "password", "password2", "consent")}
    f["phone"] = orders_svc.normalize_phone(f["phone"])
    f["email"] = f["email"].lower()
    err = {}
    if f["title"] not in ("Anh", "Chị"):
        f["title"] = "Anh"
    if len(f["full_name"]) < 2 or re.search(r"\d", f["full_name"]):
        err["full_name"] = "Vui lòng nhập họ tên (không chứa số)."
    if not re.fullmatch(r"0[35789]\d{8}", f["phone"]):
        err["phone"] = "Số điện thoại cần 10 chữ số, bắt đầu bằng 03, 05, 07, 08 hoặc 09."
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}", f["email"]):
        err["email"] = "Email chưa đúng định dạng, ví dụ ten@gmail.com."
    msg = check_password_rule(f["password"])
    if msg:
        err["password"] = msg
    elif f["password"] != f["password2"]:
        err["password2"] = "Hai lần nhập mật khẩu chưa khớp."
    if f["consent"] != "1":
        err["consent"] = "Bạn cần đồng ý với điều khoản và chính sách bảo mật."
    if not err.get("email") and db.scalar(conn, "SELECT 1 FROM users WHERE lower(email)=?", (f["email"],)):
        err["email"] = "Email này đã có tài khoản. Hãy đăng nhập hoặc dùng Quên mật khẩu."
    if not err.get("phone") and db.scalar(conn, "SELECT 1 FROM users WHERE phone=?", (f["phone"],)):
        err["phone"] = "Số điện thoại này đã có tài khoản. Hãy đăng nhập."
    cust = db.one(conn, "SELECT * FROM customers WHERE phone=?", (f["phone"],)) if not err.get("phone") else None
    if cust and cust["email"] and cust["email"].lower() != f["email"] and not err.get("email"):
        err["phone"] = ("Số điện thoại này đã từng đặt hàng với một email khác. "
                        f"Hãy dùng đúng email đó, hoặc gọi {config.HOTLINE} để được hỗ trợ.")
    if err:
        raise AccountError(next(iter(err.values())), err)
    with db.transaction(conn):
        t = _now()
        uid = conn.execute("INSERT INTO users(email,phone,password_hash,full_name,role,created_at) VALUES(?,?,?,?,?,?)",
                           (f["email"], f["phone"], security.hash_password(f["password"]), f["full_name"], "customer", t)).lastrowid
        if cust:  # khách từng mua không cần tài khoản -> gắn các đơn cũ vào tài khoản mới
            conn.execute("UPDATE customers SET user_id=?, full_name=?, title=?, email=?, consent_at=?, consent_version=? WHERE id=?",
                         (uid, f["full_name"], f["title"], f["email"], t, config.CONSENT_VERSION, cust["id"]))
        else:
            conn.execute("""INSERT INTO customers(user_id,full_name,phone,email,title,consent_at,consent_version,created_at)
                            VALUES(?,?,?,?,?,?,?,?)""", (uid, f["full_name"], f["phone"], f["email"], f["title"], t, config.CONSENT_VERSION, t))
        orders_svc.send_mail(conn, f["email"], f"Chào mừng bạn đến với {config.SHOP_NAME}",
                             f"<p>Chào {f['title']} {f['full_name']},</p><p>Tài khoản của bạn đã được tạo thành công."
                             + (" Các đơn hàng trước đây đặt bằng số điện thoại này đã được gắn vào tài khoản." if cust else "")
                             + "</p><p>Giờ bạn có thể theo dõi đơn, lưu địa chỉ, danh sách yêu thích và viết đánh giá.</p>")
    return dict(db.one(conn, "SELECT * FROM users WHERE id=?", (uid,))), bool(cust)


def customer_of(conn, user):
    if not user:
        return None
    c = db.one(conn, "SELECT * FROM customers WHERE user_id=?", (user["id"],))
    return dict(c) if c else None


def update_profile(conn, user, form):
    name = (form.get("full_name") or "").strip()
    title = form.get("title") if form.get("title") in ("Anh", "Chị") else "Anh"
    if len(name) < 2 or re.search(r"\d", name):
        raise AccountError("Vui lòng nhập họ tên (không chứa số).", {"full_name": "Vui lòng nhập họ tên (không chứa số)."})
    conn.execute("UPDATE users SET full_name=? WHERE id=?", (name, user["id"]))
    conn.execute("UPDATE customers SET full_name=?, title=? WHERE user_id=?", (name, title, user["id"]))


def change_password(conn, user, old, new, new2):
    u = db.one(conn, "SELECT * FROM users WHERE id=?", (user["id"],))
    if not security.verify_password(old or "", u["password_hash"]):
        raise AccountError("Mật khẩu hiện tại chưa đúng.", {"old": "Mật khẩu hiện tại chưa đúng."})
    msg = check_password_rule(new)
    if msg:
        raise AccountError(msg, {"new": msg})
    if new != new2:
        raise AccountError("Hai lần nhập mật khẩu mới chưa khớp.", {"new2": "Hai lần nhập mật khẩu mới chưa khớp."})
    conn.execute("UPDATE users SET password_hash=? WHERE id=?", (security.hash_password(new), user["id"]))
    # đăng xuất mọi phiên khác của tài khoản này
    conn.execute("DELETE FROM sessions WHERE user_id=?", (user["id"],))


# ---------- Quên mật khẩu: liên kết ký số, dùng 1 lần, hết hạn sau 30 phút ----------
RESET_MINUTES = 30


def reset_token(user):
    exp = int((datetime.now() + timedelta(minutes=RESET_MINUTES)).timestamp())
    payload = f"{user['id']}.{exp}"
    # gắn với mật khẩu hiện tại -> đổi mật khẩu xong thì liên kết cũ tự hết hiệu lực
    return payload + "." + security.sign(f"reset:{payload}:{user['password_hash']}", 32)


def request_reset(conn, email, base_url):
    """Luôn trả lời giống nhau dù email có tồn tại hay không (không lộ ai có tài khoản)."""
    u = db.one(conn, "SELECT * FROM users WHERE lower(email)=? AND status='active'", ((email or "").strip().lower(),))
    if u:
        link = f"{base_url}/dat-lai-mat-khau?t={reset_token(u)}"
        orders_svc.send_mail(conn, u["email"], f"[{config.SHOP_NAME}] Đặt lại mật khẩu",
                             f"<p>Chào {u['full_name']},</p><p>Bấm vào liên kết dưới đây để đặt mật khẩu mới "
                             f"(hiệu lực {RESET_MINUTES} phút, dùng một lần):</p><p><a href=\"{link}\">{link}</a></p>"
                             "<p>Nếu bạn không yêu cầu, hãy bỏ qua email này.</p>")


def user_from_reset(conn, token):
    try:
        uid, exp, sig = (token or "").split(".")
        if int(exp) < datetime.now().timestamp():
            return None
        u = db.one(conn, "SELECT * FROM users WHERE id=?", (int(uid),))
        if u and hmac_eq(sig, security.sign(f"reset:{uid}.{exp}:{u['password_hash']}", 32)):
            return dict(u)
    except (ValueError, TypeError):
        pass
    return None


def hmac_eq(a, b):
    import hmac
    return hmac.compare_digest(a or "", b or "")


def do_reset(conn, user, new, new2):
    msg = check_password_rule(new)
    if msg:
        raise AccountError(msg, {"new": msg})
    if new != new2:
        raise AccountError("Hai lần nhập mật khẩu chưa khớp.", {"new2": "Hai lần nhập mật khẩu chưa khớp."})
    conn.execute("UPDATE users SET password_hash=?, failed_logins=0, locked_until=NULL WHERE id=?",
                 (security.hash_password(new), user["id"]))
    conn.execute("DELETE FROM sessions WHERE user_id=?", (user["id"],))


# ---------- Sổ địa chỉ ----------
MAX_ADDRESSES = 5


def addresses(conn, customer_id):
    return [dict(r) for r in db.all(conn, "SELECT * FROM addresses WHERE customer_id=? ORDER BY is_default DESC, id", (customer_id,))]


def save_address(conn, customer_id, form, address_id=None):
    f = {k: (form.get(k) or "").strip() for k in ("receiver_name", "receiver_phone", "province", "ward", "street", "is_default")}
    f["receiver_phone"] = orders_svc.normalize_phone(f["receiver_phone"])
    err = {}
    if len(f["receiver_name"]) < 2:
        err["receiver_name"] = "Vui lòng nhập tên người nhận."
    if not re.fullmatch(r"0[35789]\d{8}", f["receiver_phone"]):
        err["receiver_phone"] = "Số điện thoại cần 10 chữ số."
    if f["province"] not in orders_svc.PROVINCES:
        err["province"] = "Vui lòng chọn tỉnh / thành phố."
    if len(f["ward"]) < 2:
        err["ward"] = "Vui lòng nhập phường / xã."
    if len(f["street"]) < 4:
        err["street"] = "Vui lòng nhập số nhà, tên đường."
    if err:
        raise AccountError(next(iter(err.values())), err)
    with db.transaction(conn):
        count = db.scalar(conn, "SELECT COUNT(*) FROM addresses WHERE customer_id=?", (customer_id,))
        make_default = f["is_default"] == "1" or count == 0
        if make_default:
            conn.execute("UPDATE addresses SET is_default=0 WHERE customer_id=?", (customer_id,))
        if address_id:
            conn.execute("""UPDATE addresses SET receiver_name=?, receiver_phone=?, province=?, ward=?, street=?,
                            is_default=CASE WHEN ? THEN 1 ELSE is_default END WHERE id=? AND customer_id=?""",
                         (f["receiver_name"], f["receiver_phone"], f["province"], f["ward"], f["street"],
                          1 if make_default else 0, address_id, customer_id))
        else:
            if count >= MAX_ADDRESSES:
                raise AccountError(f"Sổ địa chỉ tối đa {MAX_ADDRESSES} địa chỉ. Hãy xóa bớt địa chỉ cũ.")
            conn.execute("""INSERT INTO addresses(customer_id,receiver_name,receiver_phone,province,ward,street,is_default)
                            VALUES(?,?,?,?,?,?,?)""", (customer_id, f["receiver_name"], f["receiver_phone"], f["province"],
                                                       f["ward"], f["street"], 1 if make_default else 0))


def delete_address(conn, customer_id, address_id):
    with db.transaction(conn):
        was_default = db.scalar(conn, "SELECT is_default FROM addresses WHERE id=? AND customer_id=?", (address_id, customer_id))
        conn.execute("DELETE FROM addresses WHERE id=? AND customer_id=?", (address_id, customer_id))
        if was_default:
            conn.execute("""UPDATE addresses SET is_default=1 WHERE id=(SELECT MIN(id) FROM addresses WHERE customer_id=?)""", (customer_id,))


def set_default_address(conn, customer_id, address_id):
    with db.transaction(conn):
        if db.scalar(conn, "SELECT 1 FROM addresses WHERE id=? AND customer_id=?", (address_id, customer_id)):
            conn.execute("UPDATE addresses SET is_default=CASE WHEN id=? THEN 1 ELSE 0 END WHERE customer_id=?", (address_id, customer_id))


# ---------- Yêu thích ----------
def toggle_wishlist(conn, customer_id, product_id):
    if not db.scalar(conn, "SELECT 1 FROM products WHERE id=? AND is_active=1", (product_id,)):
        raise AccountError("Sản phẩm không tồn tại.")
    if db.scalar(conn, "SELECT 1 FROM wishlists WHERE customer_id=? AND product_id=?", (customer_id, product_id)):
        conn.execute("DELETE FROM wishlists WHERE customer_id=? AND product_id=?", (customer_id, product_id))
        return False
    conn.execute("INSERT INTO wishlists(customer_id,product_id,created_at) VALUES(?,?,?)", (customer_id, product_id, _now()))
    return True


def in_wishlist(conn, customer_id, product_id):
    return bool(customer_id and db.scalar(conn, "SELECT 1 FROM wishlists WHERE customer_id=? AND product_id=?", (customer_id, product_id)))
