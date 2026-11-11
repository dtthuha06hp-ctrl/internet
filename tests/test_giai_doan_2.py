"""Kiểm thử tự động Giai đoạn 2: danh mục, bộ lọc, chi tiết sản phẩm, so sánh, chọn máy."""
import json
import re
import threading
import unittest
import urllib.parse

from tests.test_giai_doan_1 import Browser, seed, server, db  # dùng chung CSDL tạm


def cards(html):
    return re.findall(r'<article class="card[^"]*">.*?<h3>(.*?)</h3>.*?<div class="price num">([\d.]+)₫', html, re.S)


def money(s):
    return int(s.replace(".", ""))


class GiaiDoan2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed.build(quiet=True)
        cls.httpd = server.serve("127.0.0.1", 0)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.b = Browser(f"http://127.0.0.1:{cls.httpd.server_address[1]}")

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def test_01_danh_muc_dien_thoai_du_30_may(self):  # FR-01
        st, html, _ = self.b.get("/dien-thoai")
        self.assertEqual(st, 200)
        self.assertIn("(30 sản phẩm)", html)
        self.assertEqual(len(cards(html)), 20)          # 20 sản phẩm mỗi lần
        self.assertIn("Xem thêm 10 sản phẩm", html)
        _, html2, _ = self.b.get("/dien-thoai?trang=2")
        self.assertEqual(len(cards(html2)), 30)

    def test_02_loc_samsung_5_10_trieu(self):  # US-01, FR-02
        _, html, _ = self.b.get("/dien-thoai?hang=samsung&gia=5-10")
        items = cards(html)
        self.assertTrue(items)
        for name, price in items:
            self.assertIn("Samsung", name)
            self.assertTrue(5_000_000 <= money(price) < 10_000_000, (name, price))

    def test_03_bo_loc_nam_tren_url_va_hien_chip(self):  # TC-02
        _, html, _ = self.b.get("/dien-thoai?hang=apple,samsung&nhu-cau=pin")
        self.assertIn('value="apple" checked', html)
        self.assertIn('value="samsung" checked', html)
        self.assertIn("Xóa tất cả", html)
        for name, _p in cards(html):
            self.assertTrue("iPhone" in name or "Samsung" in name)

    def test_04_sap_xep_gia_tang(self):  # FR-03
        _, html, _ = self.b.get("/dien-thoai?sap-xep=gia-tang")
        prices = [money(p) for _n, p in cards(html)]
        self.assertEqual(prices, sorted(prices))
        _, html, _ = self.b.get("/dien-thoai?sap-xep=gia-giam")
        prices = [money(p) for _n, p in cards(html)]
        self.assertEqual(prices, sorted(prices, reverse=True))

    def test_05_loc_khong_co_ket_qua(self):
        _, html, _ = self.b.get("/dien-thoai?hang=apple&gia=0-5")
        self.assertIn("Không có sản phẩm phù hợp", html)

    def test_06_phu_kien_theo_loai_va_dong_may(self):
        _, html, _ = self.b.get("/phu-kien?loai=op-lung&dung-cho=iphone-17-pro-max")
        names = [n for n, _ in cards(html)]
        self.assertEqual(names, ["Ốp lưng MagSafe trong suốt iPhone 17 Pro Max"])

    def test_07_chi_tiet_doi_gia_theo_phien_ban(self):  # FR-05, US-02
        _, html, _ = self.b.get("/dien-thoai/samsung-galaxy-a56-5g")
        data = json.loads(re.search(r"window.PRODUCT = (.*?); window.CURRENT_SKU", html).group(1))
        p128 = {v["price"] for v in data["variants"] if v["option"] == "128GB"}
        p256 = {v["price"] for v in data["variants"] if v["option"] == "256GB"}
        self.assertEqual(p128, {8_990_000, 8_490_000})   # 8.490.000₫ là màu đang có giá sốc
        self.assertEqual(p256, {10_490_000})
        _, html, _ = self.b.get("/dien-thoai/samsung-galaxy-a56-5g?sku=SA011-256GB-XAN0")
        self.assertIn("10.490.000₫", html)

    def test_08_mau_het_hang_khong_mua_duoc(self):  # TC-03
        conn = db.connect()
        sku = db.scalar(conn, """SELECT v.sku FROM product_variants v JOIN inventory i ON i.variant_id=v.id
                                 WHERE i.on_hand-i.reserved=0 AND v.storage='1TB' AND v.color_name='Bạc'""")
        _, html, _ = self.b.get("/dien-thoai/iphone-17-pro-max?sku=" + urllib.parse.quote(sku))
        self.assertIn("Tạm hết hàng", html)
        self.assertRegex(html, r'data-buy="now" disabled')
        data = json.loads(re.search(r"window.PRODUCT = (.*?); window.CURRENT_SKU", html).group(1))
        self.assertEqual(next(v for v in data["variants"] if v["sku"] == sku)["available"], 0)

    def test_09_gia_soc_ap_dung_tren_trang_chi_tiet(self):
        _, html, _ = self.b.get("/dien-thoai/iphone-17-pro-max")
        self.assertIn("Giá sốc hôm nay", html)
        self.assertIn("33.990.000₫", html)

    def test_10_phu_kien_hien_dong_may_tuong_thich(self):
        _, html, _ = self.b.get("/phu-kien/op-lung-magsafe-trong-suot-iphone-17-pro-max")
        self.assertIn("Dùng được cho", html)
        self.assertIn("/dien-thoai/iphone-17-pro-max", html)

    def test_11_so_sanh_3_may(self):
        _, html, _ = self.b.get("/so-sanh?ids=1,7,14,20")  # chỉ lấy 3 máy đầu
        self.assertIn("iPhone 17 Pro Max", html)
        self.assertIn("Samsung Galaxy S26 Ultra", html)
        self.assertNotIn("OPPO Find X9</a>", html)
        self.assertIn("Dung lượng pin", html)
        self.assertIn("Chỉ hiện điểm khác nhau", html)

    def test_12_chon_may_theo_nhu_cau(self):
        _, html, _ = self.b.get("/chon-may?ngan-sach=5-10&nhu-cau=pin&he-dieu-hanh=android")
        names = re.findall(r'<article class="fp-card">.*?<h3>(.*?)</h3>', html, re.S)
        self.assertEqual(len(names), 3)
        self.assertTrue(all("iPhone" not in n for n in names))

    def test_13_san_pham_khong_ton_tai(self):
        st, _, _ = self.b.get("/dien-thoai/khong-co-may-nay")
        self.assertEqual(st, 404)
        st, _, _ = self.b.get("/phu-kien/iphone-17-pro-max")  # sai danh mục
        self.assertEqual(st, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
