"""Kiểm thử tự động Giai đoạn 5: trang quản trị."""
import re
import threading
import unittest
import urllib.error
import urllib.request

from tests.test_giai_doan_1 import Browser, seed, server, db

PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
       b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82")


def multipart(b, path, fields, files):
    bd = "----nhip5test"
    body = b""
    for k, v in fields.items():
        body += f'--{bd}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    for k, (fn, data, ct) in files.items():
        body += f'--{bd}\r\nContent-Disposition: form-data; name="{k}"; filename="{fn}"\r\nContent-Type: {ct}\r\n\r\n'.encode() + data + b"\r\n"
    body += f"--{bd}--\r\n".encode()
    req = urllib.request.Request(b.base + path, data=body, headers={"Content-Type": f"multipart/form-data; boundary={bd}"})
    try:
        r = b.op.open(req)
        return r.status, r.read().decode(), r.headers
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), e.headers


class GiaiDoan5(unittest.TestCase):
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

    def admin(self):
        self.b.login("admin@nhipmobile.vn", "Admin@123")
        return self.b.csrf()

    def staff(self):
        self.b.login("nhanvien@nhipmobile.vn", "Nhanvien@123")
        return self.b.csrf()

    def order(self, status, method="home"):
        return db.one(self.conn, "SELECT * FROM orders WHERE status=? AND delivery_method=? ORDER BY id DESC LIMIT 1", (status, method))

    def stock(self, vid):
        return db.one(self.conn, "SELECT on_hand, reserved FROM inventory WHERE variant_id=?", (vid,))

    def move(self, code, to, csrf, **extra):
        return self.b.post(f"/quan-tri/don-hang/{code}", dict({"csrf": csrf, "action": "chuyen", "to": to}, **extra))

    # ---------- Đơn hàng ----------
    def test_quy_trinh_don_day_du(self):
        csrf = self.admin()
        o = self.order("pending")
        it = db.one(self.conn, "SELECT * FROM order_items WHERE order_id=?", (o["id"],))
        before = self.stock(it["variant_id"])
        # không được nhảy cóc từ Chờ xác nhận sang Đang giao
        st, html, _ = self.move(o["order_code"], "shipping", csrf, carrier="GHN")
        self.assertEqual(st, 200)
        self.assertIn("đúng quy trình", html)
        for to in ("confirmed", "preparing"):
            self.assertEqual(self.move(o["order_code"], to, csrf)[0], 303)
        st, html, _ = self.move(o["order_code"], "shipping", csrf)          # thiếu đơn vị vận chuyển
        self.assertIn("đơn vị vận chuyển", html)
        self.assertEqual(self.move(o["order_code"], "shipping", csrf, carrier="GHN", tracking="GHN123")[0], 303)
        self.assertEqual(self.move(o["order_code"], "delivered", csrf)[0], 303)
        after = self.stock(it["variant_id"])
        self.assertEqual(after["on_hand"], before["on_hand"] - it["quantity"])
        self.assertEqual(after["reserved"], before["reserved"] - it["quantity"])
        row = db.one(self.conn, "SELECT * FROM orders WHERE id=?", (o["id"],))
        self.assertEqual(row["status"], "delivered")
        if row["payment_method"] == "cod":
            self.assertEqual(row["payment_status"], "paid")
        self.assertTrue(db.scalar(self.conn, "SELECT 1 FROM shipments WHERE order_id=? AND tracking_code='GHN123'", (o["id"],)))
        n_hist = db.scalar(self.conn, "SELECT COUNT(*) FROM order_status_history WHERE order_id=?", (o["id"],))
        self.assertGreaterEqual(n_hist, 5)
        # trả hàng → hoàn tiền: hàng quay về kho
        self.assertEqual(self.move(o["order_code"], "returning", csrf)[0], 303)
        self.assertEqual(self.move(o["order_code"], "refunded", csrf)[0], 303)
        self.assertEqual(self.stock(it["variant_id"])["on_hand"], before["on_hand"])
        seed.check(self.conn)  # báo lỗi nếu tồn kho lệch nhật ký

    def test_nhan_tai_cua_hang_khong_qua_van_chuyen(self):
        csrf = self.admin()
        o = self.order("preparing", "store") or self.order("confirmed", "store")
        if not o:
            self.skipTest("Dữ liệu mẫu không có đơn nhận tại cửa hàng ở trạng thái phù hợp")
        if o["status"] == "confirmed":
            self.move(o["order_code"], "preparing", csrf)
        st, html, _ = self.move(o["order_code"], "shipping", csrf, carrier="GHN")
        self.assertIn("đúng quy trình", html)
        self.assertEqual(self.move(o["order_code"], "delivered", csrf)[0], 303)

    def test_admin_huy_don_nha_hang_giu(self):
        csrf = self.admin()
        o = self.order("pending")
        self.move(o["order_code"], "confirmed", csrf)
        it = db.one(self.conn, "SELECT * FROM order_items WHERE order_id=?", (o["id"],))
        before = self.stock(it["variant_id"])
        st, _, _ = self.b.post(f"/quan-tri/don-hang/{o['order_code']}", {"csrf": csrf, "action": "huy", "reason": "Khách đổi ý"})
        self.assertEqual(st, 303)
        self.assertEqual(self.stock(it["variant_id"])["reserved"], before["reserved"] - it["quantity"])
        self.assertEqual(db.scalar(self.conn, "SELECT status FROM orders WHERE id=?", (o["id"],)), "cancelled")

    def test_nhan_vien_bi_che_sdt_va_khong_vao_trang_quan_tri_cao(self):   # TC-14
        self.staff()
        st, html, _ = self.b.get("/quan-tri/khach-hang")
        self.assertEqual(st, 200)
        phones = [r["phone"] for r in db.all(self.conn, "SELECT phone FROM customers LIMIT 5")]
        self.assertFalse(any(p in html for p in phones))
        for p in ("/quan-tri/san-pham", "/quan-tri/kho", "/quan-tri/ma-giam-gia", "/quan-tri/banner", "/quan-tri/danh-gia",
                  "/quan-tri/bao-cao", "/quan-tri/bao-cao/xuat"):
            self.assertEqual(self.b.get(p)[0], 403, p)
        self.assertNotIn("/quan-tri/san-pham", self.b.get("/quan-tri")[1])     # menu không hiện mục chỉ dành cho admin

    def test_khach_mua_khong_vao_duoc_quan_tri(self):
        self.b.login("khach@nhipmobile.vn", "Khach@123")
        self.assertEqual(self.b.get("/quan-tri/don-hang")[0], 403)
        self.assertEqual(Browser(self.base).get("/quan-tri/san-pham")[0], 302)

    # ---------- Sản phẩm ----------
    def test_tao_san_pham_phien_ban_anh(self):
        csrf = self.admin()
        cat = db.scalar(self.conn, "SELECT id FROM categories WHERE kind='phone' LIMIT 1")
        st, html, _ = self.b.post("/quan-tri/san-pham/moi", {"csrf": csrf, "name": "Nhịp Phone X1", "category_id": cat, "brand_id": "1",
                                                            "specs": "Màn hình | Kích thước | 6.5 inch\nsai dòng"})
        self.assertEqual(st, 200)
        self.assertIn("Dòng thông số số 2", html)
        st, _, h = self.b.post("/quan-tri/san-pham/moi", {"csrf": csrf, "name": "Nhịp Phone X1", "category_id": cat, "brand_id": "1",
                                                         "specs": "Màn hình | Kích thước | 6.5 inch", "needs": "pin", "is_active": "1"})
        self.assertEqual(st, 303)
        pid = int(re.search(r"/san-pham/(\d+)", h["Location"]).group(1))
        p = db.one(self.conn, "SELECT * FROM products WHERE id=?", (pid,))
        self.assertEqual(p["slug"], "nhip-phone-x1")
        url = f"/quan-tri/san-pham/{pid}"
        st, html, _ = self.b.post(url, {"csrf": csrf, "action": "them-pb", "storage": "128GB", "color_name": "Xanh",
                                        "color_hex": "#2F3FD1", "list_price": "5.000.000", "sale_price": "6.000.000"})
        self.assertIn("không được cao hơn giá gốc", html)
        st, _, _ = self.b.post(url, {"csrf": csrf, "action": "them-pb", "storage": "128GB", "color_name": "Xanh",
                                     "color_hex": "#2F3FD1", "list_price": "5.990.000", "sale_price": "5.490.000", "initial_stock": "7"})
        self.assertEqual(st, 303)
        v = db.one(self.conn, "SELECT * FROM product_variants WHERE product_id=?", (pid,))
        self.assertEqual(self.stock(v["id"])["on_hand"], 7)
        # đổi giá → ghi lịch sử
        self.b.post(url, {"csrf": csrf, "action": "sua-pb", "vid": v["id"], "storage": "128GB", "color_name": "Xanh",
                          "color_hex": "#2F3FD1", "list_price": "5990000", "sale_price": "5290000", "is_active": "1"})
        hist = db.all(self.conn, "SELECT * FROM price_history WHERE variant_id=? ORDER BY id", (v["id"],))
        self.assertEqual([(h["old_price"], h["new_price"]) for h in hist], [(None, 5490000), (5490000, 5290000)])
        # tải ảnh: chặn tệp không phải ảnh, nhận PNG
        st, html, _ = multipart(self.b, url, {"csrf": csrf, "action": "anh"}, {"image": ("virus.png", b"MZ\x90\x00 not image", "image/png")})
        self.assertIn("Chỉ nhận ảnh PNG, JPG hoặc WEBP", html)
        st, _, _ = multipart(self.b, url, {"csrf": csrf, "action": "anh", "main": "1"}, {"image": ("anh.png", PNG, "image/png")})
        self.assertEqual(st, 303)
        img = db.one(self.conn, "SELECT * FROM product_images WHERE product_id=? AND is_main=1", (pid,))
        self.assertTrue(img["url"].startswith("/uploads/products/nhip-phone-x1-"))
        r = self.b.op.open(self.base + img["url"])
        self.assertEqual((r.status, r.read()), (200, PNG))
        import os
        import config
        os.remove(os.path.join(config.UPLOAD_DIR, img["url"][len("/uploads/"):]))   # dọn ảnh thử
        # sản phẩm mới hiện trên website
        self.assertEqual(Browser(self.base).get("/dien-thoai/nhip-phone-x1")[0], 200)
        # ẩn sản phẩm → khách không xem được
        self.b.post(url, {"csrf": csrf, "action": "an"})
        self.assertEqual(Browser(self.base).get("/dien-thoai/nhip-phone-x1")[0], 404)

    # ---------- Kho ----------
    def test_kho_nhap_dieu_chinh(self):
        csrf = self.admin()
        r = db.one(self.conn, "SELECT * FROM inventory WHERE reserved>0 LIMIT 1")
        vid = r["variant_id"]
        st, html, _ = self.b.post("/quan-tri/kho", {"csrf": csrf, "action": "nhap", "variant_id": vid, "qty": "5"})
        self.assertEqual(self.stock(vid)["on_hand"], r["on_hand"] + 5)
        st, html, _ = self.b.post("/quan-tri/kho", {"csrf": csrf, "action": "dieu-chinh", "variant_id": vid, "qty": "-1"})
        self.assertIn("lý do", html.lower())
        self.assertEqual(self.stock(vid)["on_hand"], r["on_hand"] + 5)
        cur = self.stock(vid)
        st, html, _ = self.b.post("/quan-tri/kho", {"csrf": csrf, "action": "dieu-chinh", "variant_id": vid,
                                                    "qty": str(-(cur["on_hand"] - cur["reserved"] + 1)), "reason": "Kiểm kê"})
        self.assertEqual(self.stock(vid)["on_hand"], cur["on_hand"])           # không cho tồn thấp hơn số đang giữ
        self.b.post("/quan-tri/kho", {"csrf": csrf, "action": "dieu-chinh", "variant_id": vid, "qty": "-1", "reason": "Máy trưng bày lỗi"})
        self.assertEqual(self.stock(vid)["on_hand"], cur["on_hand"] - 1)
        self.assertTrue(db.scalar(self.conn, "SELECT 1 FROM inventory_transactions WHERE variant_id=? AND reason='Máy trưng bày lỗi'", (vid,)))
        seed.check(self.conn)  # báo lỗi nếu tồn kho lệch nhật ký

    # ---------- Marketing ----------
    def test_ma_giam_gia(self):
        csrf = self.admin()
        st, html, _ = self.b.post("/quan-tri/ma-giam-gia", {"csrf": csrf, "action": "tao", "code": "SINHVIEN500", "type": "fixed", "value": "1000"})
        self.assertIn("đã tồn tại", html)
        st, html, _ = self.b.post("/quan-tri/ma-giam-gia", {"csrf": csrf, "action": "tao", "code": "TET2027", "type": "percent", "value": "150"})
        self.assertIn("tối đa 100", html)
        st, _, _ = self.b.post("/quan-tri/ma-giam-gia", {"csrf": csrf, "action": "tao", "code": "tet2027", "type": "percent", "value": "5",
                                                        "max_discount": "200.000", "min_order": "1.000.000", "is_active": "1"})
        self.assertEqual(st, 303)
        v = db.one(self.conn, "SELECT * FROM vouchers WHERE code='TET2027'")
        self.assertEqual((v["value"], v["max_discount"], v["min_order"], v["is_active"]), (5, 200000, 1000000, 1))
        self.b.post("/quan-tri/ma-giam-gia", {"csrf": csrf, "action": "tat", "vid": v["id"]})
        self.assertEqual(db.scalar(self.conn, "SELECT is_active FROM vouchers WHERE id=?", (v["id"],)), 0)

    def test_duyet_danh_gia_cap_nhat_diem(self):
        csrf = self.admin()
        r = db.one(self.conn, "SELECT * FROM reviews WHERE status='pending' LIMIT 1")
        cnt = db.scalar(self.conn, "SELECT rating_count FROM products WHERE id=?", (r["product_id"],))
        st, _, _ = self.b.post("/quan-tri/danh-gia", {"csrf": csrf, "rid": r["id"], "action": "approved"})
        self.assertEqual(st, 303)
        self.assertEqual(db.scalar(self.conn, "SELECT rating_count FROM products WHERE id=?", (r["product_id"],)), cnt + 1)
        self.b.post("/quan-tri/danh-gia", {"csrf": csrf, "rid": r["id"], "action": "hidden"})
        self.assertEqual(db.scalar(self.conn, "SELECT rating_count FROM products WHERE id=?", (r["product_id"],)), cnt)

    def test_gia_soc_va_banner(self):
        csrf = self.admin()
        it = db.one(self.conn, """SELECT pi.*, v.sale_price FROM promotion_items pi JOIN product_variants v ON v.id=pi.variant_id
                                  JOIN promotions p ON p.id=pi.promotion_id WHERE p.is_active=1 ORDER BY p.id DESC LIMIT 1""")
        st, html, _ = self.b.post("/quan-tri/banner", {"csrf": csrf, "action": "gs-sua", "item_id": it["id"],
                                                       "promo_price": str(it["sale_price"] + 1), "quota": "10"})
        self.assertIn("thấp hơn giá bán thường", html)
        self.b.post("/quan-tri/banner", {"csrf": csrf, "action": "gs-sua", "item_id": it["id"], "promo_price": str(it["sale_price"] - 1000), "quota": "20"})
        self.assertEqual(db.scalar(self.conn, "SELECT quota FROM promotion_items WHERE id=?", (it["id"],)), 20)
        st, _, _ = self.b.post("/quan-tri/banner", {"csrf": csrf, "action": "banner", "bid": "1", "title": "Banner thử nghiệm",
                                                    "link_url": "/dien-thoai", "bg_color": "#112233", "sort_order": "0", "is_active": "1"})
        self.assertEqual(st, 303)
        self.assertIn("Banner thử nghiệm", Browser(self.base).get("/")[1])
        st, html, _ = self.b.post("/quan-tri/banner", {"csrf": csrf, "action": "banner", "bid": "1", "title": "Xấu",
                                                       "link_url": "https://lua-dao.com", "bg_color": "#112233"})
        self.assertIn("bắt đầu bằng /", html)

    # ---------- Báo cáo ----------
    def test_bao_cao_va_csv(self):
        self.admin()
        st, html, _ = self.b.get("/quan-tri/bao-cao?ky=90")
        self.assertEqual(st, 200)
        self.assertIn("Sản phẩm bán chạy", html)
        st, body, h = self.b.get("/quan-tri/bao-cao/xuat?ky=90&loai=don-hang")
        self.assertEqual(st, 200)
        self.assertIn("text/csv", h["Content-Type"])
        self.assertIn("attachment", h["Content-Disposition"])
        self.assertTrue(body.startswith("﻿Mã đơn,"))
        self.assertGreater(body.count("\n"), 5)
        # doanh thu báo cáo 30 ngày khớp với trang tổng quan
        from services import reports
        d1, d2 = reports.period(30)
        rev = reports.summary(self.conn, d1, d2)["revenue"]
        dash = self.b.get("/quan-tri")[1]
        self.assertIn(f"{rev:,}".replace(",", ".") + "₫", dash)

    def test_tao_nhanh_2_dung_luong_3_mau(self):   # US-07
        csrf = self.admin()
        cat = db.scalar(self.conn, "SELECT id FROM categories WHERE kind='phone' LIMIT 1")
        h = self.b.post("/quan-tri/san-pham/moi", {"csrf": csrf, "name": "Nhịp Phone Ma Trận", "category_id": cat, "brand_id": "2"})[2]
        url = re.search(r"(/quan-tri/san-pham/\d+)", h["Location"]).group(1)
        pid = int(url.rsplit("/", 1)[1])
        base = {"csrf": csrf, "action": "ma-tran", "m_storage1": "128GB", "m_list1": "9990000", "m_sale1": "8990000",
                "m_storage2": "256GB", "m_list2": "11990000", "m_sale2": "", "m_colors": "Đen #111111\nTrắng #FFFFFF\nXanh"}
        st, html, _ = self.b.post(url, base)
        self.assertIn("Thiếu giá bán", html)
        self.assertIn('class="cell bad" name="m_sale2"', html)
        self.assertEqual(db.scalar(self.conn, "SELECT COUNT(*) FROM product_variants WHERE product_id=?", (pid,)), 0)
        st, _, h = self.b.post(url, dict(base, m_sale2="10990000", m_stock="2"))
        self.assertIn("tb=mt6", h["Location"])
        skus = [r["sku"] for r in db.all(self.conn, "SELECT sku FROM product_variants WHERE product_id=?", (pid,))]
        self.assertEqual(len(skus), 6)
        self.assertEqual(len(set(skus)), 6)
        seed.check(self.conn)

    def test_sap_het_hien_o_tong_quan(self):   # US-10
        self.admin()
        r = db.one(self.conn, """SELECT i.*, v.sku FROM inventory i JOIN product_variants v ON v.id=i.variant_id
                                 WHERE i.on_hand-i.reserved > i.low_threshold ORDER BY i.variant_id LIMIT 1""")
        self.assertNotIn(r["sku"], self.b.get("/quan-tri")[1])
        self.conn.execute("UPDATE inventory SET low_threshold=? WHERE variant_id=?", (r["on_hand"] - r["reserved"], r["variant_id"]))
        try:
            self.assertIn(r["sku"], self.b.get("/quan-tri")[1])
        finally:
            self.conn.execute("UPDATE inventory SET low_threshold=? WHERE variant_id=?", (r["low_threshold"], r["variant_id"]))

    def test_banner_khung_gia_theo_duong_dan(self):   # lỗi B7
        csrf = self.admin()
        b3 = db.one(self.conn, "SELECT * FROM banners WHERE id=3")
        count = lambda: Browser(self.base).get("/")[1].count("Giá phải trả")
        n0 = count()
        base = {"csrf": csrf, "action": "banner", "bid": "3", "link_url": b3["link_url"], "bg_color": b3["bg_color"] or "#2F3FD1",
                "product_id": str(b3["product_id"]), "sort_order": str(b3["sort_order"]), "is_active": "1"}
        self.b.post("/quan-tri/banner", dict(base, title="Sinh vien giam them 500.000d"))   # đổi tiêu đề: bố cục không đổi
        self.assertEqual(count(), n0)
        slug = db.scalar(self.conn, "SELECT slug FROM products WHERE id=?", (b3["product_id"],))
        self.b.post("/quan-tri/banner", dict(base, title=b3["title"], link_url="/dien-thoai/" + slug))   # trỏ tới trang SP: hiện giá
        self.assertEqual(count(), n0 + 1)
        self.b.post("/quan-tri/banner", dict(base, title=b3["title"]))
        self.assertEqual(count(), n0)

    # ---------- Hãng & danh mục (FR-15) ----------
    def test_hang_va_danh_muc(self):
        csrf = self.admin()
        st, _, _ = self.b.post("/quan-tri/danh-muc", {"csrf": csrf, "action": "them-hang", "name": "Realme", "sort_order": "9"})
        self.assertEqual(st, 303)
        self.assertEqual(db.scalar(self.conn, "SELECT slug FROM brands WHERE name='Realme'"), "realme")
        self.assertIn("đã có", self.b.post("/quan-tri/danh-muc", {"csrf": csrf, "action": "them-hang", "name": "realme"})[1])
        self.assertIn('value="Realme"', self.b.get("/quan-tri/danh-muc")[1])
        self.b.post("/quan-tri/danh-muc", {"csrf": csrf, "action": "them-loai", "name": "Giá đỡ điện thoại"})
        cid = db.scalar(self.conn, "SELECT id FROM categories WHERE slug='gia-do-dien-thoai'")
        self.assertIsNotNone(cid)
        busy = db.scalar(self.conn, "SELECT id FROM categories WHERE slug='op-lung'")
        self.assertIn("còn", self.b.post("/quan-tri/danh-muc", {"csrf": csrf, "action": "an-loai", "id": busy})[1])
        self.b.post("/quan-tri/danh-muc", {"csrf": csrf, "action": "an-loai", "id": cid})
        self.assertEqual(db.scalar(self.conn, "SELECT is_active FROM categories WHERE id=?", (cid,)), 0)
        self.staff()
        self.assertEqual(self.b.get("/quan-tri/danh-muc")[0], 403)


if __name__ == "__main__":
    unittest.main()
