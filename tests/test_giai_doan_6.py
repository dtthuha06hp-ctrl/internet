"""Kiểm thử tự động Giai đoạn 6: tin tức, hỗ trợ, chính sách, trang lỗi."""
import re
import threading
import unittest

from tests.test_giai_doan_1 import Browser, seed, server, db

HELP = ["huong-dan-mua-hang", "cau-hoi-thuong-gap", "giao-hang", "doi-tra-bao-hanh", "bao-mat", "dieu-khoan",
        "gioi-thieu", "cua-hang", "lien-he"]


class GiaiDoan6(unittest.TestCase):
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

    def test_tin_tuc(self):
        st, html, _ = self.b.get("/tin-tuc")
        self.assertEqual(st, 200)
        posts = db.all(self.conn, "SELECT * FROM posts ORDER BY published_at DESC")
        self.assertEqual(len(posts), 5)
        for p in posts:
            self.assertIn(f'/tin-tuc/{p["slug"]}', html)
            self.assertGreater(len(p["content"]), 1500)          # bài viết đầy đủ, không chỉ tóm tắt
        st, html, _ = self.b.get(f"/tin-tuc/{posts[0]['slug']}")
        self.assertEqual(st, 200)
        self.assertIn("<h2>", html)                               # nội dung HTML được hiển thị, không bị escape
        self.assertIn("Sản phẩm nhắc tới trong bài", html)
        self.assertIn('href="/dien-thoai/iphone-17"', html)
        self.assertIn("Đọc thêm", html)
        self.assertEqual(self.b.get("/tin-tuc/khong-ton-tai")[0], 404)

    def test_bai_an_khong_xem_duoc(self):
        p = db.one(self.conn, "SELECT * FROM posts ORDER BY id DESC LIMIT 1")
        self.conn.execute("UPDATE posts SET is_published=0 WHERE id=?", (p["id"],))
        try:
            self.assertEqual(self.b.get(f"/tin-tuc/{p['slug']}")[0], 404)
            self.assertNotIn(p["slug"], self.b.get("/tin-tuc")[1])
        finally:
            self.conn.execute("UPDATE posts SET is_published=1 WHERE id=?", (p["id"],))

    def test_trang_ho_tro_va_chinh_sach(self):
        st, html, _ = self.b.get("/ho-tro")
        self.assertEqual(st, 200)
        for s in HELP:
            self.assertIn(f"/ho-tro/{s}", html)
            st, page, _ = self.b.get(f"/ho-tro/{s}")
            self.assertEqual(st, 200, s)
            self.assertNotIn("Sẽ có ở Giai đoạn", page)
        self.assertEqual(self.b.get("/ho-tro/khong-co")[0], 404)

    def test_chinh_sach_khop_cau_hinh(self):
        import config
        html = self.b.get("/ho-tro/giao-hang")[1]
        self.assertIn(f"{config.FREE_SHIP_FROM:,}".replace(",", ".") + "₫", html)
        self.assertIn(f"{config.SHIPPING_FEE:,}".replace(",", ".") + "₫", html)
        html = self.b.get("/ho-tro/cua-hang")[1]
        for s in db.all(self.conn, "SELECT name FROM stores"):
            self.assertIn(s["name"], html)

    def test_moi_lien_ket_trong_footer_va_bai_viet_deu_mo_duoc(self):
        html = self.b.get("/")[1] + "".join(self.b.get(f"/tin-tuc/{p['slug']}")[1] for p in db.all(self.conn, "SELECT slug FROM posts"))
        links = set(re.findall(r'href="(/[^"#?]*)', html)) - {"/dang-xuat"}
        bad = [u for u in links if not u.startswith(("/static", "/uploads")) and self.b.get(u)[0] not in (200, 302)]
        self.assertEqual(bad, [])

    def test_lien_he(self):
        csrf = self.b.csrf()
        st, html, _ = self.b.post("/ho-tro/lien-he", {"csrf": csrf, "name": "A", "email": "sai", "topic": "", "message": "ngắn"})
        self.assertEqual(st, 200)
        for msg in ("Vui lòng nhập họ tên", "Email chưa đúng", "Chọn chủ đề", "tối thiểu 10 ký tự"):
            self.assertIn(msg, html)
        n = db.scalar(self.conn, "SELECT COUNT(*) FROM email_outbox")
        st, _, h = self.b.post("/ho-tro/lien-he", {"csrf": csrf, "name": "Trần Văn <b>An</b>", "email": "an@example.com", "topic": "bh",
                                                  "order_code": "NM1", "message": "Máy của tôi bị lỗi loa sau 5 ngày."})
        self.assertEqual(st, 303)
        self.assertIn("da-gui=1", h["Location"])
        mails = db.all(self.conn, "SELECT * FROM email_outbox ORDER BY id DESC LIMIT 2")
        self.assertEqual(db.scalar(self.conn, "SELECT COUNT(*) FROM email_outbox"), n + 2)
        self.assertEqual({m["to_email"] for m in mails}, {"hotro@nhipmobile.vn", "an@example.com"})
        self.assertTrue(all("<b>An</b>" not in m["body_html"] for m in mails))     # chống chèn mã HTML
        self.assertEqual(self.b.post("/ho-tro/lien-he", {"name": "x"})[0], 403)     # thiếu mã chống giả mạo

    def test_tra_cuu_bao_hanh(self):
        o = db.one(self.conn, "SELECT * FROM orders WHERE status='completed' ORDER BY id DESC LIMIT 1")
        csrf = self.b.csrf()
        st, html, _ = self.b.post("/ho-tro/doi-tra-bao-hanh", {"csrf": csrf, "code": o["order_code"].lower(), "phone": o["receiver_phone"]})
        self.assertEqual(st, 200)
        self.assertRegex(html, r"(Còn bảo hành đến|Hết bảo hành từ) \d\d/\d\d/\d{4}")
        st, html, _ = self.b.post("/ho-tro/doi-tra-bao-hanh", {"csrf": csrf, "code": o["order_code"], "phone": "0900000999"})
        self.assertIn("Không tìm thấy đơn", html)
        p = db.one(self.conn, "SELECT * FROM orders WHERE status='pending' LIMIT 1")
        html = self.b.post("/ho-tro/doi-tra-bao-hanh", {"csrf": csrf, "code": p["order_code"], "phone": p["receiver_phone"]})[1]
        self.assertIn("Chưa kích hoạt", html)

    def test_trang_loi_than_thien(self):
        st, html, _ = self.b.get("/khong-co-trang-nay")
        self.assertEqual(st, 404)
        self.assertIn('action="/tim-kiem"', html)
        self.b.login("khach@nhipmobile.vn", "Khach@123")
        st, html, _ = self.b.get("/quan-tri")
        self.assertEqual(st, 403)
        self.assertIn("Đăng nhập tài khoản khác", html)

    def test_moi_trang_co_mo_ta(self):
        for u in ("/", "/tin-tuc", f"/tin-tuc/{db.scalar(self.conn, 'SELECT slug FROM posts LIMIT 1')}", "/ho-tro/bao-mat"):
            self.assertIn('<meta name="description"', self.b.get(u)[1], u)

    def test_dong_ho_gia_soc_va_gia_banner(self):
        """Đồng hồ nhận số giây còn lại từ máy chủ; banner hiện đúng giá phải trả (đã tính giá sốc)."""
        from datetime import datetime
        html = self.b.get("/")[1]
        left = int(re.search(r'class="timer num" data-left="(\d+)"', html).group(1))
        end = db.scalar(self.conn, "SELECT MAX(ends_at) FROM promotions WHERE is_active=1")
        expect = (datetime.fromisoformat(end) - datetime.now()).total_seconds()
        self.assertLessEqual(abs(left - expect), 5)
        self.assertGreater(left, 0)
        from services import pricing
        b1 = db.one(self.conn, "SELECT * FROM banners WHERE id=1")
        vs = [v for v in pricing.variants_of(self.conn, [b1["product_id"]])[b1["product_id"]] if v["available"] > 0]
        cheapest = min(v["price"] for v in vs)
        self.assertIn(f"{cheapest:,}".replace(",", ".") + "₫</strong>", html)

    def test_gio_viet_nam_khi_chay_online(self):
        import subprocess
        import sys
        import os
        out = subprocess.run([sys.executable, "-c", "import config, datetime, time; print(time.strftime('%z'))"],
                             capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             env=dict(os.environ, NHIP_ONLINE="1", TZ=""))
        self.assertEqual(out.stdout.strip(), "+0700", out.stderr)


if __name__ == "__main__":
    unittest.main()
