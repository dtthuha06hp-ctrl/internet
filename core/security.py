"""Mã hóa mật khẩu và các tiện ích bảo mật."""
import hashlib
import hmac
import secrets
import config


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    it = config.PASSWORD_ITERATIONS
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), it).hex()
    return f"pbkdf2_sha256${it}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _algo, it, salt, digest = stored.split("$")
        test = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(it)).hex()
        return hmac.compare_digest(test, digest)
    except Exception:
        return False


def new_token(n=32) -> str:
    return secrets.token_urlsafe(n)


def mask_phone(phone: str) -> str:
    """0912345678 -> 0912***678 (che SĐT với nhân viên)."""
    if not phone or len(phone) < 7:
        return phone or ""
    return phone[:4] + "***" + phone[-3:]


def secret_key():
    """Khóa bí mật của riêng máy này (tự tạo lần đầu, nằm cạnh file dữ liệu)."""
    import os
    import config
    path = os.path.join(os.path.dirname(config.DB_PATH), "secret.key")
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(secrets.token_hex(32))
    with open(path) as f:
        return f.read().strip().encode()


def sign(text, n=20):
    return hmac.new(secret_key(), text.encode(), hashlib.sha256).hexdigest()[:n]
