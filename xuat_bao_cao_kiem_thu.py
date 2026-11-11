"""Chạy toàn bộ kiểm thử tự động rồi xuất bảng kết quả ra tai-lieu/ket-qua-kiem-thu.html.

Cách dùng: bấm đúp chay_kiem_thu.bat (hoặc gõ: python xuat_bao_cao_kiem_thu.py)
"""
import html
import os
import platform
import sys
import time
import unittest
import webbrowser
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
OUT = os.path.join(BASE, "tai-lieu", "ket-qua-kiem-thu.html")

GROUPS = {
    "test_giai_doan_1": "GĐ1 – Nền móng: CSDL, trang chủ, tìm kiếm, đăng nhập",
    "test_giai_doan_2": "GĐ2 – Xem và chọn sản phẩm",
    "test_giai_doan_3": "GĐ3 – Giỏ hàng, mã giảm giá, đặt hàng, tra cứu",
    "test_giai_doan_4": "GĐ4 – Tài khoản người mua",
    "test_giai_doan_5": "GĐ5 – Trang quản trị",
    "test_giai_doan_6": "GĐ6 – Tin tức, hỗ trợ, chính sách",
    "test_tc_dac_ta": "17 test case theo tài liệu đặc tả (Phần 9.6 d)",
}

# Yêu cầu phi chức năng: cách đáp ứng + bằng chứng (đánh giá trung thực, cập nhật tay khi làm thêm)
NFR = [
    ("NFR-01", "Hiệu năng", "Trang chủ, PLP, PDP < 3 giây trên 4G; Lighthouse ≥ 70",
     "Trang nhẹ (ảnh SVG, không thư viện JS ngoài). Đo thử bằng Chromium giả lập 4G: xem dòng đo bên dưới.", "Một phần",
     "Chưa chạy Lighthouse chính thức; có thể tự đo: Chrome → F12 → Lighthouse."),
    ("NFR-02", "Bảo mật", "Mật khẩu băm chậm; HTTPS; CSRF mọi form; không lưu số thẻ",
     "PBKDF2-SHA256 có muối riêng; mã CSRF ở mọi form POST; không có ô nhập số thẻ.", "Đạt (trừ HTTPS)",
     "HTTPS chỉ cần khi đưa lên mạng; bản chạy trên máy cá nhân dùng http://localhost."),
    ("NFR-03", "Bảo mật", "/quan-tri chỉ cho staff/admin; khóa 15 phút sau 5 lần sai",
     "Kiểm tra quyền ở mọi trang quản trị; nhân viên bị chặn trang của admin.", "Đạt", "TC-14, TC-15"),
    ("NFR-04", "Toàn vẹn dữ liệu", "Không âm kho khi 2 người cùng đặt SKU cuối",
     "Giữ hàng bằng câu lệnh cập nhật có điều kiện trong transaction BEGIN IMMEDIATE.", "Đạt", "TC-08"),
    ("NFR-05", "Khả dụng", "Mua hàng ≤ 5 bước từ PDP; ≤ 3 phút với 5 người",
     "Luồng: PDP → Thêm vào giỏ → Giỏ hàng → Thanh toán → Đặt hàng = 4 bước.", "Một phần",
     "Cần nhờ 5 người thử và ghi thời gian (mẫu phiếu trong kịch bản demo)."),
    ("NFR-06", "Responsive", "Đúng ở 360px, 768px, 1280px; không cuộn ngang",
     "Đã rà 27 trang khách ở 390px và 1366px; TC-17 ở 360px.", "Đạt", "TC-17"),
    ("NFR-07", "Truy cập", "Ảnh có alt; tương phản ≥ 4.5:1; dùng bàn phím ở form thanh toán",
     "Ô nhập có nhãn, viền focus rõ, lỗi hiện dưới ô và tự focus ô sai.", "Một phần",
     "Ảnh trang trí để alt rỗng có chủ đích; chưa đo tương phản bằng công cụ."),
    ("NFR-08", "Tương thích", "Chrome, Edge, Safari, Firefox bản mới",
     "Chỉ dùng HTML/CSS/JS chuẩn, không cần cài thêm.", "Một phần",
     "Kiểm thử tự động chạy trên Chromium (cùng lõi với Chrome, Edge); Safari, Firefox cần thử tay."),
    ("NFR-09", "Pháp lý", "Trang Bảo mật, Đổi trả, Giao hàng, Điều khoản; lưu thời điểm đồng ý; nhãn mô phỏng",
     "Có đủ 4 trang (GĐ6); lưu consent_at + phiên bản khi đặt hàng/đăng ký; nhãn \"Website mô phỏng\" ở đầu mọi trang.", "Đạt",
     "test_giai_doan_6, test_giai_doan_3"),
    ("NFR-10", "Bảo trì", "Mã nguồn GitHub + README; nạp dữ liệu mẫu bằng một lệnh",
     "HUONG_DAN.md; lam_moi_du_lieu.bat nạp lại dữ liệu mẫu bằng một cú bấm.", "Một phần",
     "Chưa đưa lên GitHub."),
]

# Lỗi phát hiện trong quá trình làm và đã sửa (đáp ứng mục "danh sách lỗi đã sửa" của Phần 10.2)
BUGS = [
    ("GĐ1", "Trang con kế thừa bố cục bị mất nội dung các khối", "Bộ ghép giao diện xóa thẻ block quá sớm", "Chỉ xóa thẻ block ở bước hiển thị cuối"),
    ("GĐ1", "Tên vai trò ở đầu trang hiện chữ \"viên\" với admin", "Cắt chuỗi sai", "Hiện đúng \"Quản trị viên\" / \"Nhân viên\""),
    ("GĐ2", "Trang So sánh lặp nhóm thông số", "Thông số không được sắp theo nhóm", "Sắp theo thứ tự nhóm cố định"),
    ("GĐ2", "Trùng mã SKU khi sinh dữ liệu mẫu", "Mã SKU chỉ dựa vào tên hãng", "Thêm mã sản phẩm vào SKU"),
    ("GĐ3", "Trang giỏ hàng, thanh toán tràn ngang trên điện thoại", "Cột lưới không co được", "Đặt min-width:0 cho các cột"),
    ("GĐ3", "Hai lớp CSS trùng tên (.f-grid, .pay) làm vỡ chân trang và banner", "Đặt tên lớp trùng nhau", "Đổi tên thành .f-tiles, .paym"),
    ("GĐ5", "Trang /quan-tri/hop-thu bị trang \"sắp có\" chặn", "Thứ tự nạp đường dẫn", "Nạp trang dự phòng sau cùng"),
    ("GĐ5", "Doanh thu ở Tổng quan khác Báo cáo", "Hai trang dùng hai cách tính", "Dùng chung một hàm: chỉ đơn hoàn tất, theo ngày hoàn tất"),
    ("GĐ5", "Dữ liệu mẫu có đơn nhận tại cửa hàng ở trạng thái \"Đang giao\"", "Bộ sinh dữ liệu không phân biệt cách nhận", "Đơn nhận tại cửa hàng bỏ qua bước vận chuyển"),
    ("GĐ5", "Ô nhập trong bảng phiên bản không gửi được", "Thẻ form đặt trong hàng của bảng (HTML không hợp lệ)", "Dùng thuộc tính form=\"…\" cho từng ô"),
    ("GĐ6", "Ảnh bìa tin tức ở trang chủ bị thu nhỏ thành ô vuông 68px", "Lớp .thumb của thư viện ảnh sản phẩm ghi đè", "Thêm quy tắc riêng cho ảnh bìa bài viết"),
    ("GĐ6", "Trang Hỗ trợ tràn ngang 7px ở khổ điện thoại", "Cột trong khối đầu trang không co", "min-width:0 cho các cột"),
    ("GĐ6", "Nút chuyển banner, nút So sánh quá nhỏ để bấm trên điện thoại", "Vùng bấm 10px", "Tăng vùng bấm lên ≥ 26–32px"),
    ("GĐ7", "SĐT sai vẫn gửi form lên máy chủ (TC-07)", "Chỉ kiểm tra ở máy chủ", "Thêm kiểm tra ngay trên trình duyệt, báo dưới ô"),
    ("GĐ7", "Người mua chậm hơn ở chiếc cuối nhận thông báo chung chung (TC-08)", "Thông báo không nêu sản phẩm", "Báo rõ \"…vừa được người khác mua hết\""),
    ("GĐ7", "Chưa có bước xác minh chữ ký thanh toán (TC-16)", "Thanh toán mô phỏng gọi thẳng", "Thêm IPN có chữ ký HMAC-SHA512, kiểm tra số tiền, ghi log"),
    ("Sau bàn giao", "B1 · Trên máy Windows: đặt hàng xong, tra cứu đơn, Tài khoản, chi tiết đơn quản trị đều lỗi 500 (11 kiểm thử hỏng)",
     "Một câu SQL dùng cột bảng ngoài trong ORDER BY của truy vấn con: SQLite mới chấp nhận, SQLite đi kèm Python trên Windows thì không",
     "Viết lại bằng JOIN thường + truy vấn ảnh riêng; từ nay chạy kiểm thử trên cả SQLite 3.45 và 3.53, và duyệt tự động mọi trang bằng cả 4 vai trò"),
    ("Sau bàn giao", "B2 · Ai biết email cũng khóa được tài khoản người khác 15 phút", "Khóa tính theo tài khoản",
     "Đếm lần sai theo cặp (thiết bị, tài khoản): chỉ máy gõ sai bị chặn; một máy sai 20 lần thì bị chặn mọi tài khoản; email không tồn tại nhận cùng thông báo"),
    ("Sau bàn giao", "B3 · Số lượng 0, âm hoặc chữ bị lặng lẽ đổi thành 1", "Hàm thêm giỏ tự gán mặc định", "Báo lỗi \"Số lượng phải là số nguyên từ 1 đến 3\" (mã 400 với yêu cầu JSON)"),
    ("Sau bàn giao", "B4 · Giá sốc không tự sang ngày mới nếu web chạy qua nửa đêm", "Chỉ tạo đợt giá sốc lúc bật web",
     "Kiểm tra ngày ở mỗi yêu cầu (mỗi ngày làm một lần, có khóa luồng); có kiểm thử giả lập sang ngày"),
    ("Sau bàn giao", "B5 · Hủy đơn mua giá sốc không trả lại suất giá sốc", "Hàm hủy đơn trả kho, trả lượt mã giảm giá nhưng quên suất giá sốc",
     "Khi hủy, tìm đúng suất giá sốc của đợt lúc đặt (cùng phiên bản, cùng giá) và trả lại số suất"),
    ("Sau bàn giao", "B6 · Gợi ý tìm kiếm, danh sách so sánh chỉ xét 200 sản phẩm đầu (lỗi tiềm ẩn)", "Đặt giới hạn cố định limit=200",
     "Bỏ giới hạn ở gợi ý, so sánh, chọn máy, sản phẩm tương tự"),
    ("Sau bàn giao", "B7 · Khung \"Giá phải trả\" trên banner phụ thuộc tiêu đề banner", "So sánh với một câu tiêu đề cố định",
     "Chỉ hiện khung giá khi đường dẫn của banner trỏ tới đúng trang sản phẩm đó; ghi chú quy tắc ở trang quản trị Banner"),
]


class Result(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.rows = []
        self._t = 0

    def startTest(self, test):
        self._t = time.perf_counter()
        super().startTest(test)

    def _add(self, test, status, info=""):
        self.rows.append((test, status, info, time.perf_counter() - self._t))

    def addSuccess(self, test):
        super().addSuccess(test)
        self._add(test, "pass")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._add(test, "fail", str(err[1]).splitlines()[0][:300])

    def addError(self, test, err):
        super().addError(test, err)
        self._add(test, "fail", f"{err[0].__name__}: {str(err[1])[:300]}")

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._add(test, "skip", reason)


def measure_4g():
    """Đo thời gian tải 3 trang chính bằng Chromium giả lập mạng 4G (nếu có Playwright)."""
    try:
        import threading
        from playwright.sync_api import sync_playwright
        from core import server
        from database import seed
    except Exception:
        return None
    seed.build(quiet=True)
    httpd = server.serve("127.0.0.1", 0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    out = []
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        page = br.new_page(viewport={"width": 390, "height": 844})
        page.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        cdp = page.context.new_cdp_session(page)
        cdp.send("Network.enable")
        cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": 150,
                                                      "downloadThroughput": 9_000_000 / 8, "uploadThroughput": 3_000_000 / 8})
        for name, url in (("Trang chủ", "/"), ("Danh mục (PLP)", "/dien-thoai"), ("Chi tiết (PDP)", "/dien-thoai/iphone-17-pro-max")):
            page.goto(base + url, wait_until="load")
            t = page.evaluate("performance.getEntriesByType('navigation')[0].loadEventEnd")
            out.append((name, t / 1000))
        br.close()
    httpd.shutdown()
    return out


def main():
    started = datetime.now()
    loader = unittest.TestLoader()
    suite = loader.discover(os.path.join(BASE, "tests"), top_level_dir=BASE)
    runner = unittest.TextTestRunner(resultclass=Result, verbosity=2)
    res = runner.run(suite)
    from tests import test_tc_dac_ta as tc
    try:
        perf = measure_4g()
    except Exception as e:  # đo hiệu năng là phần phụ, lỗi thì bỏ qua
        print("Không đo được hiệu năng:", e)
        perf = None

    by_name = {}
    for test, status, info, sec in res.rows:
        by_name[test.id()] = (status, info, sec)

    e = html.escape
    lab = {"pass": ("Đạt", "ok"), "fail": ("Không đạt", "bad"), "skip": ("Chưa chạy", "skip")}

    # bảng 17 TC
    tc_rows = []
    for i, (code, (link, step, data, expect)) in enumerate(tc.TC.items(), 1):
        tid = next((k for k in by_name if f".test_tc{i:02d}_" in k), None)
        status, info, sec = by_name.get(tid, ("skip", "không tìm thấy hàm kiểm thử", 0))
        actual = tc.ACTUAL.get(code) or info or ("" if status == "pass" else "—")
        if status == "fail":
            actual = f"{tc.ACTUAL.get(code, '')} Lỗi: {info}".strip()
        t, cls = lab[status]
        tc_rows.append(f"<tr><td class='code'>{code}</td><td>{e(link)}</td><td>{e(step)}</td><td>{e(data)}</td><td>{e(expect)}</td>"
                       f"<td>{e(actual)}</td><td><span class='st {cls}'>{t}</span></td></tr>")
    n_tc = len(tc.TC)
    tc_pass = sum(1 for k, v in by_name.items() if ".test_tc" in k and v[0] == "pass")
    tc_skip = sum(1 for k, v in by_name.items() if ".test_tc" in k and v[0] == "skip")

    # nhóm kiểm thử
    grp_rows = []
    for mod, title in GROUPS.items():
        items = [(k, v) for k, v in by_name.items() if k.split(".")[1] == mod]
        if not items:
            continue
        p = sum(1 for _, v in items if v[0] == "pass")
        f_ = [k.split(".")[-1] for k, v in items if v[0] == "fail"]
        s = sum(1 for _, v in items if v[0] == "skip")
        grp_rows.append(f"<tr><td>{e(title)}</td><td class='n'>{len(items)}</td><td class='n'>{p}</td><td class='n'>{len(f_)}</td>"
                        f"<td class='n'>{s}</td><td>{e(', '.join(f_)) or '—'}</td></tr>")

    nfr_rows = "".join(f"<tr><td class='code'>{a}</td><td>{e(b)}</td><td>{e(c)}</td><td>{e(d)}</td>"
                       f"<td><span class='st {'ok' if s_.startswith('Đạt') else 'part'}'>{e(s_)}</span></td><td>{e(n)}</td></tr>"
                       for a, b, c, d, s_, n in NFR)
    bug_rows = "".join(f"<tr><td class='n'>{i}</td><td>{e(p)}</td><td>{e(a)}</td><td>{e(b)}</td><td>{e(c)}</td></tr>"
                       for i, (p, a, b, c) in enumerate(BUGS, 1))
    perf_html = ""
    if perf:
        perf_html = "<p class='perf'>Đo thử (Chromium, khổ điện thoại, giả lập 4G: 9 Mbps, trễ 150 ms): " + " · ".join(
            f"{e(n)} <b>{s:.2f} giây</b>".replace(".", ",") for n, s in perf) + ". Mục tiêu &lt; 3 giây.</p>"
    img = ""
    if os.path.exists(os.path.join(BASE, "tai-lieu", "anh", "tc17-360px.png")):
        img = "<figure><img src='anh/tc17-360px.png' alt='Trang chi tiết sản phẩm ở khổ 360px, thanh mua dính đáy'><figcaption>Ảnh chụp tự động khi chạy TC-17 (360 × 740)</figcaption></figure>"
    try:
        import playwright  # noqa: F401
        pw_note = "có Playwright (chạy được các bước cần trình duyệt)"
    except Exception:
        pw_note = "không có Playwright: các bước cần trình duyệt được bỏ qua"

    total = res.testsRun
    fails = len(res.failures) + len(res.errors)
    skips = len(res.skipped)
    verdict = "Tất cả kiểm thử đều đạt" if not fails else f"Có {fails} kiểm thử không đạt"
    page = TEMPLATE.format(
        when=started.strftime("%H:%M ngày %d/%m/%Y"), py=platform.python_version(), sqlite=__import__("sqlite3").sqlite_version, os=e(platform.platform(terse=True)),
        pw=pw_note, total=total, passed=total - fails - skips, fails=fails, skips=skips, verdict=verdict,
        vcls="ok" if not fails else "bad", n_tc=n_tc, tc_pass=tc_pass,
        tc_skip_txt=f" ({tc_skip} chưa chạy vì máy chưa cài Playwright)" if tc_skip else "",
        tc_rows="".join(tc_rows), grp_rows="".join(grp_rows), nfr_rows=nfr_rows, bug_rows=bug_rows,
        perf=perf_html, img=img, n_bug=len(BUGS))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"\nĐã ghi bảng kết quả: {OUT}")
    if "--khong-mo" not in sys.argv:
        webbrowser.open("file://" + OUT.replace("\\", "/"))
    return 0 if not fails else 1


TEMPLATE = """<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kết quả kiểm thử – Nhịp Mobile</title>
<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
:root{{--p:#2F3FD1;--ink:#111827;--mut:#6B7280;--line:#E5E7EB;--bg:#F6F7FB;--ok:#166534;--okb:#DCFCE7;--bad:#B42318;--badb:#FEE4E2;--part:#92400E;--partb:#FEF3C7}}
*{{box-sizing:border-box}}body{{margin:0;font:15px/1.55 'Be Vietnam Pro',system-ui,sans-serif;color:var(--ink);background:var(--bg)}}
.wrap{{max-width:1200px;margin:0 auto;padding:32px 20px 60px}}
h1{{font-size:30px;margin:0 0 4px;letter-spacing:-.02em}}h2{{font-size:20px;margin:36px 0 12px}}
.sub{{color:var(--mut);margin:0 0 20px}}
.kpi{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}
.kpi div{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px}}
.kpi span{{display:block;color:var(--mut);font-size:13px}}.kpi b{{font-size:26px}}
.verdict{{margin:16px 0 0;padding:12px 16px;border-radius:12px;font-weight:700}}
.verdict.ok{{background:var(--okb);color:var(--ok)}}.verdict.bad{{background:var(--badb);color:var(--bad)}}
.box{{background:#fff;border:1px solid var(--line);border-radius:14px;overflow-x:auto}}
table{{border-collapse:collapse;width:100%;font-size:14px}}
th,td{{text-align:left;vertical-align:top;padding:10px 12px;border-bottom:1px solid var(--line)}}
th{{background:#F8F9FB;font-size:13px;color:#374151;white-space:nowrap}}
tr:last-child td{{border-bottom:0}}
td.code{{font-weight:700;white-space:nowrap;color:var(--p)}}td.n{{text-align:right;font-variant-numeric:tabular-nums}}
.st{{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;font-weight:700;white-space:nowrap}}
.st.ok{{background:var(--okb);color:var(--ok)}}.st.bad{{background:var(--badb);color:var(--bad)}}
.st.skip{{background:#F3F4F6;color:var(--mut)}}.st.part{{background:var(--partb);color:var(--part)}}
.meta{{font-size:13px;color:var(--mut)}}.perf{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:12px 16px}}
figure{{margin:16px 0 0;display:inline-block;background:#fff;border:1px solid var(--line);border-radius:12px;padding:10px}}
figure img{{width:240px;display:block;border-radius:6px}}figcaption{{font-size:12px;color:var(--mut);margin-top:6px}}
@media(max-width:700px){{.kpi{{grid-template-columns:1fr 1fr}}h1{{font-size:24px}}}}
@media print{{body{{background:#fff}}.box{{border:0}}}}
</style></head><body><div class="wrap">
<h1>Kết quả kiểm thử – Nhịp Mobile</h1>
<p class="sub">Chạy lúc {when} · Python {py} · SQLite {sqlite} · {os} · {pw}</p>
<div class="kpi">
  <div><span>Tổng số kiểm thử tự động</span><b>{total}</b></div>
  <div><span>Đạt</span><b style="color:var(--ok)">{passed}</b></div>
  <div><span>Không đạt</span><b style="color:var(--bad)">{fails}</b></div>
  <div><span>Chưa chạy</span><b>{skips}</b></div>
</div>
<p class="verdict {vcls}">{verdict}. 17 test case theo đặc tả: {tc_pass}/{n_tc} đạt{tc_skip_txt}.</p>

<h2>1. Bảng 17 test case (Phần 9.6 d tài liệu đặc tả)</h2>
<div class="box"><table>
<tr><th>Mã</th><th>Yêu cầu</th><th>Bước thực hiện</th><th>Dữ liệu</th><th>Kết quả mong đợi</th><th>Kết quả thực tế</th><th>Kết luận</th></tr>
{tc_rows}
</table></div>
{img}

<h2>2. Toàn bộ kiểm thử tự động theo giai đoạn</h2>
<div class="box"><table>
<tr><th>Nhóm</th><th>Số kiểm thử</th><th>Đạt</th><th>Không đạt</th><th>Chưa chạy</th><th>Kiểm thử không đạt</th></tr>
{grp_rows}
</table></div>
<p class="meta">Mã nguồn kiểm thử nằm trong thư mục tests/. Mỗi lần chạy, dữ liệu mẫu được tạo lại trong một tệp tạm, không ảnh hưởng dữ liệu đang dùng.</p>

<h2>3. Yêu cầu phi chức năng</h2>
{perf}
<div class="box" style="margin-top:12px"><table>
<tr><th>Mã</th><th>Nhóm</th><th>Yêu cầu</th><th>Cách đáp ứng</th><th>Đánh giá</th><th>Ghi chú / bằng chứng</th></tr>
{nfr_rows}
</table></div>

<h2>4. Danh sách lỗi đã phát hiện và sửa ({n_bug} lỗi)</h2>
<div class="box"><table>
<tr><th>#</th><th>Giai đoạn</th><th>Lỗi</th><th>Nguyên nhân</th><th>Cách sửa</th></tr>
{bug_rows}
</table></div>
<p class="meta">Tạo tự động bởi xuat_bao_cao_kiem_thu.py. Chạy lại: bấm đúp chay_kiem_thu.bat.</p>
</div></body></html>
"""

if __name__ == "__main__":
    sys.exit(main())
