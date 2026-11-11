"""Kiểm thử tự động Giai đoạn 4: tài khoản người mua."""
import json
import re
import threading
import unittest
import urllib.request

from tests.test_giai_doan_1 import Browser, seed, server, db


def jpost(b, path, data):
    req = urllib.request.Request(b.base + path, data=json.dumps(dict(data, csrf=b.csrf())).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        r = b.op.open(req)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


class GiaiDoan4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed.build(quiet=True)
        cls.httpd = server.serve("127.0.0.1", 0)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        cls.conn = db.connect()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def setUp(self):
        self.b = Browser(self.base)

    def reg(self, **kw):
        data = {"csrf": self.b.csrf(), "title": "Anh", "full_name": "Lê Văn Tèo", "phone": "0933111222",
                "email": "teo@example.com", "password": "Matkhau123", "password2": "Matkhau123", "consent": "1"}
        data.update(kw)
        return self.b.post("/dang-ky", data)

    def test_01_dang_ky_va_tu_dang_nhap(self):
        st, _, h = self.reg()
        self.assertEqual(st, 303)
        self.assertIn("/tai-khoan", h["Location"])
        st, html, _ = self.b.get("/tai-khoan")
        self.assertEqual(st, 200)
        self.assertIn("Lê Văn Tèo", html)
        self.assertTrue(db.scalar(self.conn, "SELECT COUNT(*) FROM email_outbox WHERE to_email='teo@example.com'"))

    def test_02_dang_ky_sai_quy_tac(self):
        st, html, _ = self.reg(phone="0933000001", email="x@example.com", password="abc", password2="abc")
        self.assertEqual(st, 400)
        self.assertIn("ít nhất 8 ký tự", html)
        st, html, _ = self.reg(phone="0933000002", email="khach@nhipmobile.vn")
        self.assertIn("Email này đã có tài khoản", html)

    def test_03_dang_ky_bang_sdt_tung_mua_se_nhan_don_cu(self):
        c = db.one(self.conn, "SELECT * FROM customers WHERE user_id IS NULL AND email IS NOT NULL AND order_count>0 LIMIT 1")
        st, _, h = self.reg(phone=c["phone"], email=c["email"], full_name="Khách Cũ")
        self.assertIn("chao-cu", h["Location"])
        _, html, _ = self.b.get("/tai-khoan/don-hang")
        self.assertEqual(html.count('class="ord-row"'), c["order_count"])

    def test_04_khong_nhan_don_cua_nguoi_khac(self):
        c = db.one(self.conn, "SELECT * FROM customers WHERE user_id IS NULL AND email IS NOT NULL LIMIT 1 OFFSET 1")
        st, html, _ = self.reg(phone=c["phone"], email="nguoila@example.com")
        self.assertEqual(st, 400)
        self.assertIn("email khác", html)

    def test_05_don_cua_toi_va_chi_xem_duoc_don_minh(self):
        self.b.login("khach@nhipmobile.vn", "Khach@123")
        _, html, _ = self.b.get("/tai-khoan/don-hang?tab=da-giao")
        self.assertIn("ord-row", html)
        other = db.scalar(self.conn, "SELECT order_code FROM orders WHERE customer_id<>1 LIMIT 1")
        st, _, _ = self.b.get("/tai-khoan/don-hang/" + other)
        self.assertEqual(st, 404)

    def test_06_admin_vao_tai_khoan_bi_chuyen_ve_quan_tri(self):
        self.b.login("admin@nhipmobile.vn", "Admin@123")
        st, _, h = self.b.get("/tai-khoan")
        self.assertEqual((st, h["Location"]), (302, "/quan-tri"))

    def test_07_so_dia_chi(self):
        self.b.login("khach@nhipmobile.vn", "Khach@123")
        csrf = self.b.csrf()
        st, _, _ = self.b.post("/tai-khoan/dia-chi", {"csrf": csrf, "receiver_name": "Nguyễn Văn Minh", "receiver_phone": "0912345678",
                                                      "province": "Đà Nẵng", "ward": "Phường Hải Châu", "street": "Số 5 Bạch Đằng", "is_default": "1"})
        self.assertEqual(st, 303)
        rows = db.all(self.conn, "SELECT * FROM addresses WHERE customer_id=1 ORDER BY id")
        self.assertEqual(sum(r["is_default"] for r in rows), 1)          # luôn đúng 1 địa chỉ mặc định
        self.assertEqual(rows[-1]["is_default"], 1)
        _, html, _ = self.b.get("/thanh-toan")  # trang thanh toán điền sẵn địa chỉ mặc định (cần giỏ có hàng)
        st, html, _ = self.b.post("/tai-khoan/dia-chi", {"csrf": csrf, "receiver_name": "A", "receiver_phone": "1", "province": "", "ward": "", "street": ""})
        self.assertEqual(st, 200)
        self.assertIn("field-err", html)

    def test_08_yeu_thich_can_dang_nhap(self):
        st, data = jpost(self.b, "/yeu-thich/doi", {"product_id": 5})
        self.assertEqual(st, 401)
        self.b.login("khach@nhipmobile.vn", "Khach@123")
        st, data = jpost(self.b, "/yeu-thich/doi", {"product_id": 5})
        self.assertTrue(data["on"])
        _, html, _ = self.b.get("/tai-khoan/yeu-thich")
        self.assertIn('data-wish-id="5"', html)
        st, data = jpost(self.b, "/yeu-thich/doi", {"product_id": 5})
        self.assertFalse(data["on"])

    def test_09_chi_danh_gia_khi_da_nhan_hang(self):  # US-08
        self.b.login("khach@nhipmobile.vn", "Khach@123")
        pending = db.one(self.conn, """SELECT o.order_code, v.product_id FROM orders o JOIN order_items oi ON oi.order_id=o.id
                                       JOIN product_variants v ON v.id=oi.variant_id WHERE o.customer_id=1 AND o.status='pending' LIMIT 1""")
        _, html, _ = self.b.get(f"/tai-khoan/danh-gia/viet?don={pending['order_code']}&sp={pending['product_id']}")
        self.assertIn("sau khi đã nhận hàng", html)
        _, html, _ = self.b.get("/tai-khoan/danh-gia")
        m = re.search(r'/tai-khoan/danh-gia/viet\?don=(NM\d+)&amp;sp=(\d+)', html) or re.search(r'/tai-khoan/danh-gia/viet\?don=(NM\d+)&sp=(\d+)', html)
        code, pid = m.group(1), m.group(2)
        st, _, h = self.b.post("/tai-khoan/danh-gia/viet", {"csrf": self.b.csrf(), "don": code, "sp": pid, "rating": "5",
                                                            "content": "Rất hài lòng, máy chạy mượt."})
        self.assertEqual(st, 303)
        r = db.one(self.conn, "SELECT * FROM reviews WHERE product_id=? AND order_id=(SELECT id FROM orders WHERE order_code=?)", (pid, code))
        self.assertEqual((r["rating"], r["status"]), (5, "pending"))   # chờ admin duyệt
        _, html, _ = self.b.get(f"/tai-khoan/danh-gia/viet?don={code}&sp={pid}")
        self.assertIn("đã đánh giá", html)                               # không viết lần 2
        # đánh giá chờ duyệt chưa hiện trên trang sản phẩm (TC-66)
        slug, kind = db.one(self.conn, """SELECT p.slug, c.kind FROM products p JOIN categories c ON c.id=p.category_id
                                          WHERE p.id=?""", (pid,))
        page = Browser(self.base).get(("/dien-thoai/" if kind == "phone" else "/phu-kien/") + slug)[1]
        self.assertNotIn("Rất hài lòng, máy chạy mượt.", page)

    def test_10_gio_hang_duoc_giu_va_gop_khi_dang_nhap(self):
        vid = db.scalar(self.conn, "SELECT id FROM product_variants WHERE sku LIKE 'PK-%' ORDER BY id LIMIT 1")
        vid2 = db.scalar(self.conn, "SELECT id FROM product_variants WHERE sku LIKE 'PK-%' ORDER BY id LIMIT 1 OFFSET 3")
        self.b.login("khach@nhipmobile.vn", "Khach@123")
        self.b.post("/gio-hang/them", {"csrf": self.b.csrf(), "variant_id": vid, "qty": 1})
        self.b.post("/dang-xuat", {"csrf": self.b.csrf()})
        _, html, _ = self.b.get("/gio-hang")
        self.assertIn("Giỏ hàng đang trống", html)                       # đăng xuất: trình duyệt trở về giỏ trống
        self.b.post("/gio-hang/them", {"csrf": self.b.csrf(), "variant_id": vid2, "qty": 1})  # thêm khi chưa đăng nhập
        self.b.login("khach@nhipmobile.vn", "Khach@123")
        _, html, _ = self.b.get("/gio-hang")
        self.assertIn("(2 sản phẩm)", html)                              # gộp cả hai

    def test_11_quen_va_dat_lai_mat_khau(self):
        self.b.post("/quen-mat-khau", {"csrf": self.b.csrf(), "email": "nhanvien@nhipmobile.vn"})
        body = db.scalar(self.conn, "SELECT body_html FROM email_outbox WHERE to_email='nhanvien@nhipmobile.vn' ORDER BY id DESC LIMIT 1")
        token = re.search(r"dat-lai-mat-khau\?t=([\w.]+)", body).group(1)
        st, _, _ = self.b.post("/dat-lai-mat-khau", {"csrf": self.b.csrf(), "t": token, "new": "Moi12345", "new2": "Moi12345"})
        self.assertEqual(st, 200)
        st, _, h = Browser(self.base).login("nhanvien@nhipmobile.vn", "Moi12345")
        self.assertEqual(st, 303)
        st, html, _ = self.b.get("/dat-lai-mat-khau?t=" + token)        # liên kết chỉ dùng 1 lần
        self.assertIn("không hợp lệ", html)
        # email lạ: vẫn trả lời giống nhau, không gửi gì
        n = db.scalar(self.conn, "SELECT COUNT(*) FROM email_outbox")
        _, html, _ = self.b.post("/quen-mat-khau", {"csrf": self.b.csrf(), "email": "khongco@example.com"})
        self.assertIn("Nếu", html)
        self.assertEqual(db.scalar(self.conn, "SELECT COUNT(*) FROM email_outbox"), n)

    def test_12_doi_mat_khau(self):
        self.reg(phone="0933222333", email="doimk@example.com")
        st, html, _ = self.b.post("/tai-khoan/doi-mat-khau", {"csrf": self.b.csrf(), "old": "sai", "new": "Moi12345", "new2": "Moi12345"})
        self.assertIn("chưa đúng", html)
        st, html, _ = self.b.post("/tai-khoan/doi-mat-khau", {"csrf": self.b.csrf(), "old": "Matkhau123", "new": "Moi12345", "new2": "Moi12345"})
        self.assertIn("Đã đổi mật khẩu", html)
        st, _, _ = Browser(self.base).login("doimk@example.com", "Moi12345")
        self.assertEqual(st, 303)

    def test_13_huy_don_trong_tai_khoan(self):
        self.b.login("khach@nhipmobile.vn", "Khach@123")
        code = db.scalar(self.conn, "SELECT order_code FROM orders WHERE customer_id=1 AND status='pending' LIMIT 1")
        _, html, _ = self.b.post(f"/tai-khoan/don-hang/{code}", {"csrf": self.b.csrf(), "reason": "Tôi đặt nhầm"})
        self.assertIn("Đã hủy đơn hàng", html)
        self.assertEqual(db.scalar(self.conn, "SELECT status FROM orders WHERE order_code=?", (code,)), "cancelled")


if __name__ == "__main__":
    unittest.main(verbosity=2)
