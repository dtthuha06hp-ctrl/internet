"""Kiểm thử tự động Giai đoạn 3: giỏ hàng, mã giảm giá, đặt hàng, tra cứu, hủy đơn (mã TC theo bảng 9.6 d của tài liệu đặc tả)."""
import re
import urllib.parse  # noqa: F401
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor

from tests.test_giai_doan_1 import Browser, seed, server, db

ADDR = {"title": "Chị", "full_name": "Nguyễn Thu Trang", "email": "trang@example.com", "delivery_method": "home",
        "province": "Hà Nội", "ward": "Phường Láng", "street": "Số 10 Láng Hạ", "payment_method": "cod", "consent": "1"}


def vid(conn, product_slug, storage=None, color=None):
    sql = "SELECT v.id FROM product_variants v JOIN products p ON p.id=v.product_id WHERE p.slug=?"
    args = [product_slug]
    if storage:
        sql += " AND v.storage=?"
        args.append(storage)
    if color:
        sql += " AND v.color_name=?"
        args.append(color)
    return db.scalar(conn, sql + " ORDER BY v.id LIMIT 1", args)


def available(conn, variant_id):
    return db.scalar(conn, "SELECT on_hand-reserved FROM inventory WHERE variant_id=?", (variant_id,))


class GiaiDoan3(unittest.TestCase):
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
        self.csrf = self.b.csrf()

    # ---------- tiện ích ----------
    def add(self, variant_id, qty=1, b=None):
        b = b or self.b
        return b.post("/gio-hang/them", {"csrf": b.csrf(), "variant_id": variant_id, "qty": qty})

    def checkout(self, phone, b=None, **extra):
        b = b or self.b
        _, html, _ = b.get("/thanh-toan")
        m = re.search(r'name="idempotency_key" value="([^"]+)"', html)
        key = m.group(1) if m else "k"
        vc = re.search(r'name="voucher_code" value="([^"]*)"', html)
        data = dict(ADDR, phone=phone, csrf=b.csrf(), idempotency_key=key, voucher_code=vc.group(1) if vc else "")
        data.update(extra)
        return b.post("/thanh-toan", data), data

    def order_code(self, headers):
        m = re.search(r"/dat-hang-thanh-cong/(NM\d+)", headers.get("Location", ""))
        return m.group(1) if m else None

    # ---------- kiểm thử ----------
    def test_04_them_vao_gio(self):  # US-03
        v = vid(self.conn, "samsung-galaxy-a56-5g", "256GB")
        st, _, h = self.add(v)
        self.assertEqual(st, 303)
        _, html, _ = self.b.get("/gio-hang")
        self.assertIn("Samsung Galaxy A56 5G", html)
        self.assertIn("10.490.000₫", html)

    def test_05_toi_da_3_san_pham(self):  # TC-04
        v = vid(self.conn, "vivo-y19s")
        self.add(v, 2)
        self.add(v, 5)
        cart_qty = db.scalar(self.conn, """SELECT ci.quantity FROM cart_items ci JOIN carts c ON c.id=ci.cart_id
                                            WHERE ci.variant_id=? AND c.status='active' ORDER BY ci.id DESC LIMIT 1""", (v,))
        self.assertEqual(cart_qty, 3)
        st, _, h = self.add(v, 1)
        self.assertIn("t%E1%BB%91i%20%C4%91a", h["Location"])  # "tối đa" trong thông báo

    def test_06_ma_giam_gia_chua_du_dieu_kien(self):  # TC-05, US-04
        self.add(vid(self.conn, "cap-usb-a-to-usb-c-1m-3a"))
        self.b.post("/gio-hang/ma-giam-gia", {"csrf": self.csrf, "code": "SINHVIEN500"})
        _, html, _ = self.b.get("/gio-hang")
        self.assertIn("áp dụng cho đơn từ 5.000.000₫", html)
        self.b.post("/gio-hang/ma-giam-gia", {"csrf": self.csrf, "code": "THANG10"})
        _, html, _ = self.b.get("/gio-hang")
        self.assertIn("đã hết hạn", html)

    def test_07_ma_giam_gia_hop_le(self):  # US-04
        self.add(vid(self.conn, "samsung-galaxy-a56-5g", "256GB"))
        self.b.post("/gio-hang/ma-giam-gia", {"csrf": self.csrf, "code": "sinhvien500"})
        _, html, _ = self.b.get("/gio-hang")
        self.assertIn("−500.000₫", html)
        self.assertIn("9.990.000₫", html)  # 10.490.000 − 500.000

    def test_08_dat_hang_cod_thanh_cong(self):  # US-05
        v = vid(self.conn, "oppo-a6-pro", "128GB")
        before = available(self.conn, v)
        self.add(v)
        (st, _, h), _d = self.checkout("0911000001")
        self.assertEqual(st, 303, "đặt hàng phải chuyển sang trang thành công")
        code = self.order_code(h)
        self.assertRegex(code, r"^NM\d{10}$")
        self.assertEqual(available(self.conn, v), before - 1)  # đã giữ hàng
        o = db.one(self.conn, "SELECT * FROM orders WHERE order_code=?", (code,))
        self.assertEqual(o["status"], "pending")
        self.assertEqual(o["total"], o["subtotal"] - o["discount_amount"] + o["shipping_fee"])
        self.assertIsNotNone(db.scalar(self.conn, "SELECT consent_at FROM customers WHERE phone='0911000001'"))
        self.assertTrue(db.scalar(self.conn, "SELECT COUNT(*) FROM email_outbox WHERE order_id=?", (o["id"],)))
        st, html, _ = self.b.get(h["Location"])
        self.assertIn("Đặt hàng thành công", html)
        self.assertIn(code, html)

    def test_09_so_dien_thoai_sai(self):  # TC-07
        self.add(vid(self.conn, "oppo-a5i"))
        (st, html, _), _d = self.checkout("12345")
        self.assertEqual(st, 400)
        self.assertIn("10 chữ số", html)

    def test_09b_chua_dong_y_dieu_khoan(self):
        self.add(vid(self.conn, "oppo-a5i"))
        (st, html, _), _d = self.checkout("0911000009", consent="")
        self.assertEqual(st, 400)
        self.assertIn("đồng ý với điều khoản", html)

    def test_10_bam_dat_hang_2_lan_chi_1_don(self):  # TC-10
        self.add(vid(self.conn, "xiaomi-redmi-15c"))
        (st1, _, h1), data = self.checkout("0911000002")
        st2, _, h2 = self.b.post("/thanh-toan", dict(data, csrf=self.b.csrf()))
        self.assertEqual(self.order_code(h1), self.order_code(h2))
        n = db.scalar(self.conn, "SELECT COUNT(*) FROM orders o JOIN customers c ON c.id=o.customer_id WHERE c.phone='0911000002'")
        self.assertEqual(n, 1)

    def test_11_hai_nguoi_mua_chiec_cuoi(self):  # TC-08
        v = vid(self.conn, "samsung-galaxy-z-fold7", "512GB", "Bạc")   # còn 2 chiếc
        self.assertEqual(available(self.conn, v), 2)
        buyers = [Browser(self.base) for _ in range(2)]
        for b in buyers:
            self.add(v, 2, b)
        with ThreadPoolExecutor(2) as ex:
            results = list(ex.map(lambda ab: self.checkout(ab[1], b=ab[0])[0], [(buyers[0], "0911000003"), (buyers[1], "0911000004")]))
        ok = [r for r in results if "/dat-hang-thanh-cong/" in r[2].get("Location", "")]
        self.assertEqual(len(ok), 1, "chỉ một người đặt được")
        self.assertEqual(available(self.conn, v), 0)
        self.assertGreaterEqual(db.scalar(self.conn, "SELECT reserved FROM inventory WHERE variant_id=?", (v,)), 2)

    def test_12_tra_cuu_sai_so_dien_thoai(self):  # TC-11
        code = db.scalar(self.conn, "SELECT order_code FROM orders ORDER BY id LIMIT 1")
        _, html, _ = self.b.post("/tra-cuu-don-hang", {"csrf": self.csrf, "code": code, "phone": "0999999999"})
        self.assertIn("Không tìm thấy đơn phù hợp", html)

    def test_12b_tra_cuu_dung(self):
        o = db.one(self.conn, "SELECT * FROM orders ORDER BY id LIMIT 1")
        _, html, _ = self.b.post("/tra-cuu-don-hang", {"csrf": self.csrf, "code": o["order_code"].lower(), "phone": o["receiver_phone"]})
        self.assertIn(f"Đơn {o['order_code']}", html)

    def test_13_huy_don_tra_hang_ve_kho(self):  # FR-13
        v = vid(self.conn, "vivo-y29s")
        before = available(self.conn, v)
        self.add(v, 2)
        self.b.post("/gio-hang/ma-giam-gia", {"csrf": self.csrf, "code": "FREESHIP30"})
        (st, _, h), _d = self.checkout("0911000005")
        code = self.order_code(h)
        self.assertEqual(available(self.conn, v), before - 2)
        _, html, _ = self.b.post("/tra-cuu-don-hang", {"csrf": self.csrf, "code": code, "phone": "0911000005",
                                                       "action": "huy", "reason": "Tôi đặt nhầm"})
        self.assertIn("Đã hủy", html)
        self.assertEqual(available(self.conn, v), before)
        o = db.one(self.conn, "SELECT * FROM orders WHERE order_code=?", (code,))
        self.assertEqual((o["status"], o["cancel_reason"]), ("cancelled", "Tôi đặt nhầm"))
        seed.check(self.conn)  # tồn kho vẫn khớp nhật ký

    def test_14_khong_huy_duoc_don_da_xac_nhan(self):  # TC-12
        o = db.one(self.conn, "SELECT * FROM orders WHERE status='shipping' LIMIT 1") or \
            db.one(self.conn, "SELECT * FROM orders WHERE status='preparing' LIMIT 1")
        _, html, _ = self.b.post("/tra-cuu-don-hang", {"csrf": self.csrf, "code": o["order_code"], "phone": o["receiver_phone"],
                                                       "action": "huy", "reason": "Tôi đặt nhầm"})
        self.assertNotIn("Xác nhận hủy đơn", html)
        self.assertEqual(db.scalar(self.conn, "SELECT status FROM orders WHERE id=?", (o["id"],)), o["status"])

    def test_15_toi_da_3_don_cho_xac_nhan(self):
        for i in range(3):
            self.add(vid(self.conn, "cap-usb-a-to-usb-c-1m-3a"))
            (st, _, h), _d = self.checkout("0911000006")
            self.assertEqual(st, 303)
        self.add(vid(self.conn, "cap-usb-a-to-usb-c-1m-3a"))
        (st, html, _), _d = self.checkout("0911000006")
        self.assertEqual(st, 400)
        self.assertIn("đơn chờ xác nhận", html)

    def test_16_gia_tinh_o_may_chu(self):  # TC-09
        """Gửi kèm giá giả trong form cũng không ảnh hưởng: máy chủ tự tra giá."""
        v = vid(self.conn, "iphone-16e", "128GB")
        self.add(v)
        (st, _, h), _d = self.checkout("0911000007", total="1000", price="1000", unit_price="1000")
        o = db.one(self.conn, "SELECT * FROM orders WHERE order_code=?", (self.order_code(h),))
        self.assertEqual(o["subtotal"], 14_990_000)

    def test_17_mo_phong_chuyen_khoan(self):  # FR-20
        self.add(vid(self.conn, "oppo-a5i", "128GB"))
        (st, _, h), _d = self.checkout("0911000008", payment_method="bank_qr")
        loc = h["Location"]
        code = self.order_code(h)
        token = loc.split("t=")[1]
        _, html, _ = self.b.get(loc)
        self.assertIn("Quét mã để chuyển khoản", html)
        self.b.post(f"/dat-hang-thanh-cong/{code}/thanh-toan", {"csrf": self.b.csrf(), "t": token, "action": "ok"})
        self.assertEqual(db.scalar(self.conn, "SELECT payment_status FROM orders WHERE order_code=?", (code,)), "paid")
        # trang thành công không xem được nếu thiếu mã xác thực
        st, _, _ = self.b.get(f"/dat-hang-thanh-cong/{code}")
        self.assertEqual(st, 404)

    def test_18_so_luong_khong_hop_le_bao_loi(self):   # lỗi B3
        v = vid(self.conn, "oppo-a5i")
        cnt = lambda: db.scalar(self.conn, """SELECT COUNT(*) FROM cart_items ci JOIN carts c ON c.id=ci.cart_id
                                              WHERE ci.variant_id=? AND c.status='active'""", (v,))
        before = cnt()
        for bad in ("0", "-1", "abc"):
            st, _, h = self.b.post("/gio-hang/them", {"csrf": self.b.csrf(), "variant_id": v, "qty": bad})
            self.assertIn("Số lượng phải là số nguyên từ 1 đến 3", urllib.parse.unquote(h["Location"]), bad)
        import json
        from urllib.error import HTTPError
        from urllib.request import Request
        rq = Request(self.b.base + "/gio-hang/them", headers={"Content-Type": "application/json"},
                                    data=json.dumps({"csrf": self.b.csrf(), "variant_id": v, "qty": -2}).encode())
        with self.assertRaises(HTTPError) as cm:
            self.b.op.open(rq)
        self.assertEqual(cm.exception.code, 400)
        self.assertEqual(cnt(), before)   # không lặng lẽ thêm 1 cái nữa

    def test_19_gia_soc_tu_sang_ngay_moi(self):   # lỗi B4
        from services import promotions
        old = db.one(self.conn, "SELECT * FROM promotions WHERE is_active=1 ORDER BY id DESC LIMIT 1")
        n_items = db.scalar(self.conn, "SELECT COUNT(*) FROM promotion_items WHERE promotion_id=?", (old["id"],))
        # giả lập: đợt hôm nay đã kết thúc (như vừa qua 00:00) và web vẫn đang chạy
        self.conn.execute("UPDATE promotions SET ends_at='2000-01-01 23:59:59' WHERE id=?", (old["id"],))
        promotions._checked_day = None
        st, html, _ = self.b.get("/")
        new = db.one(self.conn, "SELECT * FROM promotions WHERE is_active=1 ORDER BY id DESC LIMIT 1")
        self.assertNotEqual(new["id"], old["id"])
        self.assertEqual(db.scalar(self.conn, "SELECT COUNT(*) FROM promotion_items WHERE promotion_id=?", (new["id"],)), n_items)
        self.assertIn("Giá sốc", html)
        self.b.get("/")   # lần sau trong ngày không tạo thêm
        self.assertEqual(db.scalar(self.conn, "SELECT COUNT(*) FROM promotions WHERE id>?", (new["id"],)), 0)

    def test_20_huy_don_tra_lai_suat_gia_soc(self):   # lỗi B5
        it = db.one(self.conn, """SELECT pi.*, v.id vid FROM promotion_items pi JOIN promotions p ON p.id=pi.promotion_id
                                  JOIN product_variants v ON v.id=pi.variant_id JOIN inventory i ON i.variant_id=v.id
                                  WHERE p.is_active=1 AND p.ends_at>=datetime('now','localtime') AND pi.quota-pi.sold>=1
                                  AND i.on_hand-i.reserved>=1 ORDER BY p.id DESC LIMIT 1""")
        sold0 = it["sold"]
        self.add(it["vid"])
        (st, _, h), _ = self.checkout("0911020020")
        code = re.search(r"/dat-hang-thanh-cong/(NM\d+)", h["Location"]).group(1)
        o = db.one(self.conn, "SELECT * FROM orders WHERE order_code=?", (code,))
        self.assertEqual(db.scalar(self.conn, "SELECT unit_price FROM order_items WHERE order_id=?", (o["id"],)), it["promo_price"])
        self.assertEqual(db.scalar(self.conn, "SELECT sold FROM promotion_items WHERE id=?", (it["id"],)), sold0 + 1)
        from services import orders
        orders.cancel(self.conn, o["id"], "Đổi ý")
        self.assertEqual(db.scalar(self.conn, "SELECT sold FROM promotion_items WHERE id=?", (it["id"],)), sold0)

    def test_21_goi_y_xet_moi_san_pham(self):   # lỗi B6
        from services import products
        n = db.scalar(self.conn, "SELECT COUNT(*) FROM products WHERE is_active=1")
        self.assertEqual(len(products.cards(self.conn, limit=None)), n)
        last = db.one(self.conn, "SELECT p.name FROM products p WHERE p.is_active=1 ORDER BY p.sold_count ASC, p.id DESC LIMIT 1")
        names = [r["name"] for r in products.suggest(self.conn, last["name"], limit=50)]
        self.assertIn(last["name"], names)


if __name__ == "__main__":
    unittest.main(verbosity=2)
