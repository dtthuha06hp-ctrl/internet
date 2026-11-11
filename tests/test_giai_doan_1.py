"""Kiểm thử tự động Giai đoạn 1.

Chạy: python -m unittest discover tests -v
Mỗi lần chạy dùng một cơ sở dữ liệu tạm, không ảnh hưởng dữ liệu của bạn.
"""
import http.cookiejar
import json
import os
import re
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import config  # noqa: E402

TMP = tempfile.mkdtemp()
config.DB_PATH = os.path.join(TMP, "test.db")

from database import seed  # noqa: E402
from core import db, server  # noqa: E402
import app  # noqa: E402,F401  (đăng ký các trang)


class Browser:
    """Trình duyệt giả lập: giữ cookie, không tự đi theo chuyển hướng."""
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None

    def __init__(self, base):
        self.base = base
        self.jar = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar), self.NoRedirect)

    def get(self, path):
        try:
            r = self.op.open(self.base + path)
            return r.status, r.read().decode(), r.headers
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode(), e.headers

    def post(self, path, data):
        body = urllib.parse.urlencode(data).encode()
        try:
            r = self.op.open(urllib.request.Request(self.base + path, data=body))
            return r.status, r.read().decode(), r.headers
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode(), e.headers

    def csrf(self):
        _, html, _ = self.get("/gio-hang")  # trang nào cũng có mã chống giả mạo của phiên hiện tại
        return re.search(r'window\.NM = \{csrf: "([^"]+)"', html).group(1)

    def login(self, user, pw):
        return self.post("/dang-nhap", {"csrf": self.csrf(), "login": user, "password": pw, "next": ""})


class GiaiDoan1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed.build(quiet=True)
        cls.httpd = server.serve("127.0.0.1", 0)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def setUp(self):
        self.b = Browser(self.base)

    def test_01_csdl_du_31_bang(self):
        conn = db.connect()
        n = db.scalar(conn, "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite%'")
        self.assertEqual(n, 31)

    def test_02_ton_kho_khop_nhat_ky_va_khong_am(self):
        conn = db.connect()
        seed.check(conn)  # báo lỗi nếu lệch
        self.assertEqual(db.scalar(conn, "SELECT COUNT(*) FROM inventory WHERE on_hand<0 OR reserved<0 OR reserved>on_hand"), 0)

    def test_03_don_hang_luu_gia_va_tong_tien_dung(self):
        conn = db.connect()
        bad = db.scalar(conn, """SELECT COUNT(*) FROM orders o WHERE o.subtotal <>
                                 (SELECT SUM(line_total) FROM order_items i WHERE i.order_id=o.id)""")
        self.assertEqual(bad, 0)

    def test_04_trang_chu_hien_san_pham_tu_csdl(self):
        st, html, _ = self.b.get("/")
        self.assertEqual(st, 200)
        self.assertIn("iPhone 17 Pro Max", html)
        self.assertIn("Giá sốc hôm nay", html)
        self.assertIn("Phụ kiện", html)

    def test_05_tim_kiem_khong_dau(self):  # TC-01
        _, body, _ = self.b.get("/api/goi-y?q=" + urllib.parse.quote("dien thoai samsung"))
        items = json.loads(body)
        self.assertTrue(items)
        self.assertTrue(all("Samsung" in i["name"] for i in items))
        _, body, _ = self.b.get("/api/goi-y?q=" + urllib.parse.quote("ốp lưng"))
        self.assertTrue(json.loads(body))

    def test_06_dang_nhap_admin_vao_quan_tri(self):
        st, _, h = self.b.login("admin@nhipmobile.vn", "Admin@123")
        self.assertEqual(st, 303)
        self.assertEqual(h["Location"], "/quan-tri")
        st, html, _ = self.b.get("/quan-tri")
        self.assertEqual(st, 200)
        self.assertIn("Doanh thu 30 ngày", html)

    def test_07_khach_khong_vao_duoc_quan_tri(self):  # TC-14
        st, _, h = self.b.get("/quan-tri")
        self.assertEqual(st, 302)
        self.assertIn("/dang-nhap", h["Location"])
        self.b.login("khach@nhipmobile.vn", "Khach@123")
        st, _, _ = self.b.get("/quan-tri")
        self.assertEqual(st, 403)

    def test_08_nhan_vien_bi_che_so_dien_thoai(self):
        self.b.login("nhanvien@nhipmobile.vn", "Nhanvien@123")
        _, html, _ = self.b.get("/quan-tri")
        self.assertIn("***", html)

    def test_09_sai_5_lan_bi_khoa(self):  # TC-15
        conn = db.connect()
        for _ in range(5):
            st, html, _ = self.b.login("nhanvien@nhipmobile.vn", "sai")
        self.assertIn("tạm khóa", html)
        st, html, _ = self.b.login("nhanvien@nhipmobile.vn", "Nhanvien@123")
        self.assertEqual(st, 400)
        from services import login_guard
        login_guard.reset()

    def test_10_form_thieu_ma_chong_gia_mao_bi_tu_choi(self):
        st, _, _ = self.b.post("/dang-nhap", {"login": "admin@nhipmobile.vn", "password": "Admin@123"})
        self.assertEqual(st, 403)

    def test_11_khong_doc_duoc_file_ngoai_thu_muc(self):
        st, _, _ = self.b.get("/static/../config.py")
        self.assertNotEqual(st, 200)
        st, _, _ = self.b.get("/uploads/..%2fdatabase%2fschema.sql")
        self.assertNotEqual(st, 200)

    def test_12_trang_khong_ton_tai_bao_404(self):
        st, html, _ = self.b.get("/khong-co-trang-nay")
        self.assertEqual(st, 404)
        self.assertIn("Không tìm thấy trang", html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
