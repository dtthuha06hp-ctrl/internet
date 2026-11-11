"""Kết nối cơ sở dữ liệu SQLite."""
import sqlite3
from contextlib import contextmanager
import config


def connect(path=None):
    conn = sqlite3.connect(path or config.DB_PATH, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


@contextmanager
def transaction(conn):
    """Mọi bước bên trong cùng thành công hoặc cùng thất bại.

    BEGIN IMMEDIATE khóa ghi ngay từ đầu, nên hai người mua chiếc máy cuối cùng
    sẽ được xử lý lần lượt chứ không chồng lên nhau.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def one(conn, sql, params=()):
    return conn.execute(sql, params).fetchone()


def all(conn, sql, params=()):
    return conn.execute(sql, params).fetchall()


def scalar(conn, sql, params=()):
    row = conn.execute(sql, params).fetchone()
    return row[0] if row else None
