"""17 trường hợp kiểm thử (TC-01 → TC-17) đúng như bảng ở Phần 9.6 d) của tài liệu đặc tả.

Mỗi hàm kiểm thử ứng với đúng một TC, cùng số thứ tự. Các bước cần trình duyệt thật
(bấm Back, khổ màn hình 360px, form không gửi đi) chạy bằng Playwright nếu máy có cài;
nếu không có, phần đó được bỏ qua và báo rõ trong bảng kết quả.
"""
import json
import re
import threading
import unittest
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

from tests.test_giai_doan_1 import Browser, seed, server, db
from tests.test_giai_doan_3 import ADDR, vid, available

try:
    from playwright.sync_api import sync_playwright
    HAS_PW = True
except Exception:  # máy chưa cài Playwright
    HAS_PW = False

# Mã · liên kết yêu cầu · bước · dữ liệu · kết quả mong đợi (chép từ tài liệu đặc tả)
TC = {
    "TC-01": ("FR-04", "Tìm kiếm không dấu", "\"dien thoai samsung\"", "Hiện SP Samsung"),
    "TC-02": ("FR-02", "Lọc giá rồi bấm vào SP, bấm Back", "5–10 triệu", "Quay lại vẫn giữ bộ lọc"),
    "TC-03": ("FR-05", "Chọn màu hết hàng", "Màu có tồn = 0", "Không chọn được, nút mua không bật"),
    "TC-04": ("FR-06", "Tăng số lượng vượt giới hạn", "Bấm + lần thứ 4", "Báo \"Tối đa 3 sản phẩm\""),
    "TC-05": ("FR-07", "Áp mã khi đơn chưa đủ tối thiểu", "Giỏ 4,8tr, mã tối thiểu 5tr", "Báo lỗi, tổng không đổi"),
    "TC-06": ("FR-07", "Một khách dùng mã 2 lần", "Mã giới hạn 1 lần/khách", "Lần 2 bị từ chối"),
    "TC-07": ("FR-08", "Đặt hàng với SĐT sai định dạng", "\"09123\"", "Báo lỗi dưới ô, không gửi form"),
    "TC-08": ("FR-09, NFR-04", "Hai trình duyệt cùng đặt SKU còn 1 máy, bấm gần như cùng lúc", "Tồn = 1",
              "Chỉ một đơn thành công; đơn còn lại báo hết hàng; tồn không âm"),
    "TC-09": ("FR-09", "Sửa giá trong trình duyệt (DevTools) trước khi đặt", "total = 1000", "Đơn vẫn tính đúng giá ở server"),
    "TC-10": ("FR-10", "Bấm \"Đặt hàng\" hai lần liên tiếp", "—", "Chỉ tạo một đơn"),
    "TC-11": ("FR-11", "Tra cứu với mã đúng, SĐT sai", "—", "\"Không tìm thấy đơn phù hợp\""),
    "TC-12": ("FR-13", "Khách hủy đơn đang giao", "Trạng thái Đang giao", "Không có nút hủy; gọi trực tiếp API bị từ chối"),
    "TC-13": ("FR-16", "Admin chuyển Chờ xác nhận → Đã giao bỏ qua bước", "—", "Bị từ chối"),
    "TC-14": ("NFR-03", "Khách thường truy cập /quan-tri", "Tài khoản role customer", "Bị chuyển về đăng nhập / lỗi 403"),
    "TC-15": ("FR-12", "Đăng nhập sai 5 lần", "—", "Tài khoản bị khóa tạm 15 phút"),
    "TC-16": ("FR-20", "Gửi IPN giả có chữ ký sai", "—", "Đơn không đổi sang paid; ghi log cảnh báo"),
    "TC-17": ("NFR-06", "Mở PDP ở 360px", "—", "Không cuộn ngang, thanh mua dính đáy hiển thị"),
}

# Ghi chú "kết quả thực tế" để in vào bảng báo cáo (mỗi test tự điền)
ACTUAL = {}


class KiemThuDacTa(unittest.TestCase):
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

    # ---------- tiện ích ----------
    def add(self, variant_id, qty=1, b=None):
        b = b or self.b
        return b.post("/gio-hang/them", {"csrf": b.csrf(), "variant_id": variant_id, "qty": qty})

    def checkout(self, phone, b=None, **extra):
        b = b or self.b
        _, html, _ = b.get("/thanh-toan")
        key = re.search(r'name="idempotency_key" value="([^"]+)"', html).group(1)
        vc = re.search(r'name="voucher_code" value="([^"]*)"', html)
        data = dict(ADDR, phone=phone, csrf=b.csrf(), idempotency_key=key, voucher_code=vc.group(1) if vc else "")
        data.update(extra)
        return b.post("/thanh-toan", data), data

    @staticmethod
    def code_of(h):
        m = re.search(r"/dat-hang-thanh-cong/(NM\d+)", h.get("Location", ""))
        return m.group(1) if m else None

    def cart_total(self, b=None):
        _, html, _ = (b or self.b).get("/gio-hang")
        m = re.search(r'<div class="total"><dt>Tổng tiền</dt><dd class="num">([\d.]+)₫', html)
        return int(m.group(1).replace(".", "")), html

    def page(self, pw, width=1280, height=800):
        br = pw.chromium.launch()
        return br, br.new_page(viewport={"width": width, "height": height})

    # ---------- 17 trường hợp ----------
    def test_tc01_tim_kiem_khong_dau(self):
        _, body, _ = self.b.get("/api/goi-y?q=" + urllib.parse.quote("dien thoai samsung"))
        names = [i["name"] for i in json.loads(body)]
        self.assertTrue(names)
        self.assertTrue(all("Samsung" in n for n in names))
        _, html, _ = self.b.get("/tim-kiem?q=" + urllib.parse.quote("dien thoai samsung"))
        found = re.findall(r"<h3>([^<]+)</h3>", html)
        self.assertTrue(found and all("Samsung" in n for n in found), found[:3])
        ACTUAL["TC-01"] = f"Gợi ý trả về {len(names)} SP, trang kết quả {len(found)} SP – tất cả là Samsung"

    def test_tc02_loc_roi_bam_back_van_giu_bo_loc(self):
        url = "/dien-thoai?gia=5-10"
        _, html, _ = self.b.get(url)
        self.assertIn('value="5-10" checked', html.replace("checked ", "checked "))
        note = "Bộ lọc nằm trên URL (?gia=5-10), tải lại trang vẫn được chọn"
        if HAS_PW:
            with sync_playwright() as pw:
                br, p = self.page(pw)
                p.goto(self.base + "/dien-thoai")
                p.check('input[name="gia"][value="5-10"]', force=True)
                p.wait_for_url(re.compile(r"gia=5-10"), timeout=5000)
                p.wait_for_timeout(400)
                n_before = p.locator(".grid .card, .p-grid .card, .cards .card").count()
                p.locator("a.card-link, .card a").first.click()
                p.wait_for_load_state()
                self.assertIn("/dien-thoai/", p.url)
                p.go_back()
                p.wait_for_load_state()
                self.assertIn("gia=5-10", p.url)
                self.assertTrue(p.is_checked('input[name="gia"][value="5-10"]'))
                n_after = p.locator(".grid .card, .p-grid .card, .cards .card").count()
                self.assertEqual(n_before, n_after)
                br.close()
            note = "Trên Chromium: lọc 5–10 triệu → mở SP → Back: URL còn ?gia=5-10, ô lọc vẫn tích, số SP không đổi"
        ACTUAL["TC-02"] = note

    def test_tc03_mau_het_hang_khong_mua_duoc(self):
        v = db.one(self.conn, """SELECT v.sku FROM product_variants v JOIN inventory i ON i.variant_id=v.id
                                 JOIN products p ON p.id=v.product_id WHERE p.slug='iphone-17-pro-max' AND i.on_hand-i.reserved=0""")
        self.assertIsNotNone(v, "dữ liệu mẫu cần 1 phiên bản hết hàng")
        _, html, _ = self.b.get("/dien-thoai/iphone-17-pro-max?sku=" + urllib.parse.quote(v["sku"]))
        self.assertIn("Tạm hết hàng", html)
        self.assertRegex(html, r'data-buy="now" disabled')
        # gọi thẳng API thêm vào giỏ cũng bị chặn
        vid_ = db.scalar(self.conn, "SELECT id FROM product_variants WHERE sku=?", (v["sku"],))
        st, _, h = self.add(vid_)
        self.assertEqual(db.scalar(self.conn, """SELECT COUNT(*) FROM cart_items ci JOIN carts c ON c.id=ci.cart_id
                                                 WHERE ci.variant_id=? AND c.status='active'""", (vid_,)), 0)
        ACTUAL["TC-03"] = f"SKU {v['sku']}: hiện \"Tạm hết hàng\", nút Mua ngay bị khóa; gửi thẳng yêu cầu thêm giỏ cũng bị từ chối"

    def test_tc04_toi_da_3_san_pham(self):
        v = vid(self.conn, "vivo-y19s")
        self.add(v, 3)
        st, _, h = self.b.post("/gio-hang/cap-nhat", {"csrf": self.b.csrf(), "variant_id": v, "qty": 4})
        msg = urllib.parse.unquote(h.get("Location", "")) if st in (302, 303) else ""
        _, html, _ = self.b.get("/gio-hang")
        qty = db.scalar(self.conn, """SELECT ci.quantity FROM cart_items ci JOIN carts c ON c.id=ci.cart_id
                                      WHERE ci.variant_id=? AND c.status='active' ORDER BY ci.id DESC LIMIT 1""", (v,))
        self.assertEqual(qty, 3)
        st, _, h = self.add(v, 1)
        self.assertIn("tối đa 3 sản phẩm", urllib.parse.unquote(h["Location"]))
        self.assertIn('aria-label="Tăng số lượng" disabled', html)
        ACTUAL["TC-04"] = "Ở 3 sản phẩm nút + bị khóa, ghi \"Tối đa 3/đơn\"; yêu cầu thứ 4 bị từ chối với thông báo \"…chỉ mua tối đa 3 sản phẩm…\", giỏ giữ nguyên 3"

    def test_tc05_ma_chua_du_toi_thieu(self):
        self.add(vid(self.conn, "samsung-galaxy-a17"))        # 4.990.000₫ < 5 triệu
        before, _ = self.cart_total()
        self.b.post("/gio-hang/ma-giam-gia", {"csrf": self.b.csrf(), "code": "SINHVIEN500"})
        after, html = self.cart_total()
        self.assertIn("áp dụng cho đơn từ 5.000.000₫", html)
        self.assertEqual(before, after)
        ACTUAL["TC-05"] = f"Giỏ {before:,}₫ + mã SINHVIEN500 → báo \"Mã chỉ áp dụng cho đơn từ 5.000.000₫\", tổng vẫn {after:,}₫".replace(",", ".")

    def test_tc06_mot_khach_dung_ma_2_lan(self):
        phone = "0911006006"
        self.add(vid(self.conn, "samsung-galaxy-a56-5g", "256GB"))
        (st, _, h), _ = self.checkout(phone, voucher_code="SINHVIEN500")
        self.assertEqual(st, 303)
        o = db.one(self.conn, "SELECT * FROM orders WHERE order_code=?", (self.code_of(h),))
        self.assertEqual(o["discount_amount"], 500_000)
        b2 = Browser(self.base)
        self.add(vid(self.conn, "samsung-galaxy-a56-5g", "256GB"), b=b2)
        (st, html, _), _ = self.checkout(phone, b=b2, voucher_code="SINHVIEN500")
        self.assertEqual(st, 400)
        self.assertIn("đã dùng mã SINHVIEN500 rồi", html)
        ACTUAL["TC-06"] = "Lần 1 giảm 500.000₫; lần 2 (cùng SĐT, trình duyệt khác) bị từ chối: \"Bạn đã dùng mã SINHVIEN500 rồi\""

    def test_tc07_so_dien_thoai_sai(self):
        self.add(vid(self.conn, "oppo-a5i"))
        n = db.scalar(self.conn, "SELECT COUNT(*) FROM orders")
        (st, html, _), _ = self.checkout("09123")
        self.assertEqual(st, 400)
        self.assertRegex(html, r'field bad"><label for="phone">')
        self.assertIn("10 chữ số", html)
        self.assertEqual(db.scalar(self.conn, "SELECT COUNT(*) FROM orders"), n)
        note = "Máy chủ từ chối (mã 400), báo lỗi ngay dưới ô SĐT, không tạo đơn"
        if HAS_PW:
            with sync_playwright() as pw:
                br, p = self.page(pw)
                p.goto(self.base + "/dien-thoai/oppo-a5i")
                p.evaluate("""async () => { const v = window.PRODUCT.variants.find(x => x.sku === window.CURRENT_SKU) || window.PRODUCT.variants[0];
                    await fetch('/gio-hang/them', {method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: 'csrf=' + encodeURIComponent(NM.csrf) + '&variant_id=' + v.id + '&qty=1'}); }""")
                p.goto(self.base + "/thanh-toan")
                sent = []
                p.on("request", lambda r: sent.append(r) if r.method == "POST" and r.url.endswith("/thanh-toan") else None)
                p.fill("#full_name", "Nguyễn Văn A")
                p.fill("#phone", "09123")
                p.click("#placeBtn")
                p.wait_for_timeout(500)
                self.assertEqual(sent, [], "form không được gửi lên máy chủ")
                self.assertIn("/thanh-toan", p.url)
                err = p.locator("#phone").locator("xpath=..").locator(".field-err").inner_text()
                self.assertIn("10 chữ số", err)
                br.close()
            note = "Trên Chromium: bấm Đặt hàng → lỗi hiện ngay dưới ô SĐT, form KHÔNG gửi đi; máy chủ cũng tự chặn (400) nếu bị vượt qua"
        ACTUAL["TC-07"] = note

    def test_tc08_hai_nguoi_cung_mua_chiec_cuoi(self):
        v = vid(self.conn, "samsung-galaxy-z-fold7", "512GB", "Bạc")
        left = available(self.conn, v)
        if left > 1:  # đưa về đúng 1 chiếc như kịch bản
            from services import inventory
            with db.transaction(self.conn):
                inventory.move(self.conn, v, "adjust", -(left - 1), "Chuẩn bị TC-08", None, None)
        self.assertEqual(available(self.conn, v), 1)
        buyers = [Browser(self.base) for _ in range(2)]
        for b in buyers:
            self.add(v, 1, b)
        with ThreadPoolExecutor(2) as ex:
            res = list(ex.map(lambda a: self.checkout(a[1], b=a[0])[0], [(buyers[0], "0911008001"), (buyers[1], "0911008002")]))
        ok = [r for r in res if "/dat-hang-thanh-cong/" in r[2].get("Location", "")]
        fail = [r for r in res if r not in ok]
        self.assertEqual(len(ok), 1)
        self.assertTrue(any("vừa được người khác mua hết" in urllib.parse.unquote(r[2].get("Location", "")) + r[1] for r in fail))
        self.assertEqual(available(self.conn, v), 0)
        self.assertGreaterEqual(db.scalar(self.conn, "SELECT on_hand FROM inventory WHERE variant_id=?", (v,)), 0)
        seed.check(self.conn)
        ACTUAL["TC-08"] = "2 luồng đặt cùng lúc: 1 đơn thành công, 1 đơn báo \"vừa được người khác mua hết\"; có thể bán = 0, không âm"

    def test_tc09_sua_gia_tren_trinh_duyet(self):
        self.add(vid(self.conn, "iphone-16e", "128GB"))
        (st, _, h), _ = self.checkout("0911009009", total="1000", price="1000", unit_price="1000", subtotal="1000")
        o = db.one(self.conn, "SELECT * FROM orders WHERE order_code=?", (self.code_of(h),))
        self.assertEqual(o["subtotal"], 14_990_000)
        self.assertEqual(o["total"], 14_990_000)
        ACTUAL["TC-09"] = "Gửi kèm total=1000, price=1000: đơn vẫn lưu 14.990.000₫ (giá tra từ CSDL)"

    def test_tc10_bam_dat_hang_hai_lan(self):
        self.add(vid(self.conn, "xiaomi-redmi-15c"))
        (st1, _, h1), data = self.checkout("0911010010")
        st2, _, h2 = self.b.post("/thanh-toan", dict(data, csrf=self.b.csrf()))
        self.assertEqual(self.code_of(h1), self.code_of(h2))
        n = db.scalar(self.conn, "SELECT COUNT(*) FROM orders o JOIN customers c ON c.id=o.customer_id WHERE c.phone='0911010010'")
        self.assertEqual(n, 1)
        self.add(vid(self.conn, "xiaomi-redmi-15c"))
        self.assertIn("b.disabled = true", self.b.get("/thanh-toan")[1])   # nút cũng tự khóa sau lần bấm đầu
        ACTUAL["TC-10"] = f"Gửi 2 lần cùng mã chống trùng → cả 2 trả về đơn {self.code_of(h1)}, chỉ 1 đơn trong CSDL; nút cũng tự khóa"

    def test_tc11_tra_cuu_sai_sdt(self):
        code = db.scalar(self.conn, "SELECT order_code FROM orders ORDER BY id LIMIT 1")
        _, html, _ = self.b.post("/tra-cuu-don-hang", {"csrf": self.b.csrf(), "code": code, "phone": "0999999999"})
        self.assertIn("Không tìm thấy đơn phù hợp", html)
        self.assertNotIn("Lịch sử đơn hàng", html)
        ACTUAL["TC-11"] = f"Mã {code} + SĐT sai → \"Không tìm thấy đơn phù hợp\", không lộ thông tin đơn"

    def test_tc12_khong_huy_duoc_don_dang_giao(self):
        o = db.one(self.conn, "SELECT * FROM orders WHERE status='shipping' LIMIT 1")
        self.assertIsNotNone(o)
        csrf = self.b.csrf()
        _, html, _ = self.b.post("/tra-cuu-don-hang", {"csrf": csrf, "code": o["order_code"], "phone": o["receiver_phone"]})
        self.assertIn("Đang giao", html)
        self.assertNotIn('value="huy"', html)
        _, html, _ = self.b.post("/tra-cuu-don-hang", {"csrf": csrf, "code": o["order_code"], "phone": o["receiver_phone"],
                                                       "action": "huy", "reason": "Tôi đặt nhầm"})
        self.assertEqual(db.scalar(self.conn, "SELECT status FROM orders WHERE id=?", (o["id"],)), "shipping")
        from services import orders
        with self.assertRaises(orders.OrderError):
            orders.cancel(self.conn, o["id"], "Thử hủy", by_user=True)
        ACTUAL["TC-12"] = f"Đơn {o['order_code']} (Đang giao): không có nút hủy; gửi thẳng yêu cầu hủy bị từ chối, trạng thái giữ nguyên"

    def test_tc13_admin_khong_nhay_coc_trang_thai(self):
        self.b.login("admin@nhipmobile.vn", "Admin@123")
        o = db.one(self.conn, "SELECT * FROM orders WHERE status='pending' ORDER BY id DESC LIMIT 1")
        _, html, _ = self.b.get(f"/quan-tri/don-hang/{o['order_code']}")
        self.assertNotIn('value="delivered"', html)
        _, html, _ = self.b.post(f"/quan-tri/don-hang/{o['order_code']}", {"csrf": self.b.csrf(), "action": "chuyen", "to": "delivered"})
        self.assertIn("đúng quy trình", html)
        self.assertEqual(db.scalar(self.conn, "SELECT status FROM orders WHERE id=?", (o["id"],)), "pending")
        ACTUAL["TC-13"] = "Đơn Chờ xác nhận chỉ có nút Xác nhận / Hủy; gửi thẳng yêu cầu → Đã giao bị từ chối, trạng thái không đổi"

    def test_tc14_khach_khong_vao_quan_tri(self):
        st, _, h = self.b.get("/quan-tri")
        self.assertEqual(st, 302)
        self.assertIn("/dang-nhap", h["Location"])
        self.b.login("khach@nhipmobile.vn", "Khach@123")
        for u in ("/quan-tri", "/quan-tri/don-hang", "/quan-tri/san-pham", "/quan-tri/bao-cao/xuat"):
            self.assertEqual(self.b.get(u)[0], 403, u)
        ACTUAL["TC-14"] = "Chưa đăng nhập → chuyển về /dang-nhap; tài khoản khách → lỗi 403 ở mọi trang /quan-tri"

    def test_tc15_sai_5_lan_bi_khoa(self):
        from services import accounts, login_guard
        email = "khach@nhipmobile.vn"
        try:
            for _ in range(5):
                st, html, _ = self.b.login(email, "sai-mat-khau")
            self.assertIn("tạm khóa 15 phút", html)
            st, html, _ = self.b.login(email, "Khach@123")       # đúng mật khẩu vẫn chưa vào được
            self.assertEqual(st, 400)
            self.assertIn("thử lại sau 15 phút", html)
            # B2: người khác gõ sai không khóa được chủ tài khoản đang ở máy khác
            self.assertEqual(accounts.authenticate(self.conn, email, "Khach@123", ip="10.0.0.9")["email"], email)
            # email không tồn tại nhận cùng thông báo như email có thật (không lộ ai đã đăng ký)
            login_guard.reset()
            msgs = []
            for who in (email, "khongco@example.com"):
                try:
                    accounts.authenticate(self.conn, who, "sai", ip="10.0.0.7")
                except accounts.LoginError as e:
                    msgs.append(str(e))
            self.assertEqual(msgs[0], msgs[1])
            ACTUAL["TC-15"] = ("Sai lần 5 → \"Đăng nhập tạm khóa 15 phút trên thiết bị này\"; nhập đúng mật khẩu vẫn bị chặn 15 phút. "
                               "Chủ tài khoản ở máy khác vẫn đăng nhập được (kẻ xấu không khóa được người khác)")
        finally:
            login_guard.reset()

    def test_tc16_ipn_chu_ky_sai(self):
        import os
        import config
        from services import payment_gateway as pg
        self.add(vid(self.conn, "oppo-a5i", "128GB"))
        (st, _, h), _ = self.checkout("0911016016", payment_method="bank_qr")
        o = db.one(self.conn, "SELECT * FROM orders WHERE order_code=?", (self.code_of(h),))
        log = os.path.join(os.path.dirname(config.DB_PATH), "thanh-toan.log")
        size = os.path.getsize(log) if os.path.exists(log) else 0
        fake = {"order_code": o["order_code"], "amount": str(o["total"]), "result": "00", "txn_ref": "FAKE1", "sig": "0" * 128}
        st, body, _ = self._post_json("/thanh-toan/ipn", fake)
        self.assertEqual(json.loads(body)["RspCode"], "97")
        self.assertEqual(db.scalar(self.conn, "SELECT payment_status FROM orders WHERE id=?", (o["id"],)), "pending")
        self.assertGreater(os.path.getsize(log), size)
        with open(log, encoding="utf-8") as f:
            self.assertIn("Chữ ký IPN không hợp lệ", f.read()[size:])
        # đúng chữ ký nhưng sửa số tiền → cũng bị từ chối
        good = pg.build_ipn(dict(o), True)
        bad_amount = dict(good, amount="1000")
        self.assertEqual(json.loads(self._post_json("/thanh-toan/ipn", bad_amount)[1])["RspCode"], "97")
        # IPN hợp lệ → đã thanh toán; gửi lại lần 2 không cộng 2 lần
        self.assertEqual(json.loads(self._post_json("/thanh-toan/ipn", good)[1])["RspCode"], "00")
        self.assertEqual(db.scalar(self.conn, "SELECT payment_status FROM orders WHERE id=?", (o["id"],)), "paid")
        self.assertEqual(json.loads(self._post_json("/thanh-toan/ipn", good)[1])["RspCode"], "02")
        ACTUAL["TC-16"] = "IPN chữ ký giả → mã 97, đơn vẫn \"chờ thanh toán\", ghi cảnh báo vào database/thanh-toan.log; IPN thật → mã 00; gửi lặp → mã 02"

    def _post_json(self, path, data):
        import urllib.request
        import urllib.error
        req = urllib.request.Request(self.base + path, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"})
        try:
            r = urllib.request.urlopen(req)
            return r.status, r.read().decode(), r.headers
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode(), e.headers

    @unittest.skipUnless(HAS_PW, "cần Playwright để mở trình duyệt khổ 360px")
    def test_tc17_trang_chi_tiet_o_360px(self):
        with sync_playwright() as pw:
            br, p = self.page(pw, 360, 740)
            p.goto(self.base + "/dien-thoai/iphone-17-pro-max")
            over = p.evaluate("document.documentElement.scrollWidth - window.innerWidth")
            self.assertLessEqual(over, 0, "có cuộn ngang")
            p.evaluate("window.scrollTo(0, 1800)")
            p.wait_for_timeout(600)
            bar = p.locator("#stickyBuy")
            self.assertTrue(bar.is_visible(), "thanh mua dính đáy chưa hiện")
            box = bar.bounding_box()
            self.assertAlmostEqual(box["y"] + box["height"], 740, delta=2)
            import os
            import config
            os.makedirs(os.path.join(config.BASE_DIR, "tai-lieu", "anh"), exist_ok=True)
            p.screenshot(path=os.path.join(config.BASE_DIR, "tai-lieu", "anh", "tc17-360px.png"))
            br.close()
        ACTUAL["TC-17"] = "Chromium 360×740: chiều rộng trang = màn hình (không cuộn ngang); cuộn xuống thấy thanh giá + nút mua dính sát đáy"


if __name__ == "__main__":
    unittest.main()
