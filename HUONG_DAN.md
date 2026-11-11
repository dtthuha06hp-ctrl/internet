# Hướng dẫn chạy website Nhịp Mobile

> Website mô phỏng phục vụ học tập, môn Internet và Thương mại điện tử. Không bán hàng thật.

## 1. Cài Python (chỉ làm một lần)

1. Vào **python.org/downloads**, bấm nút vàng **Download Python 3.x.x**.
2. Mở file vừa tải về.
3. Ở màn hình đầu tiên, **tích ô "Add python.exe to PATH"** (ở dưới cùng). Bước này rất quan trọng.
4. Bấm **Install Now**, chờ xong, bấm **Close**.

Kiểm tra: nhấn **Windows + R**, gõ `cmd`, Enter, rồi gõ `py --version`. Nếu hiện `Python 3.x.x` là đã cài xong.

## 2. Chạy website

1. Mở thư mục `NhipMobile`.
2. **Bấm đúp `chay_web.bat`**.
3. Một cửa sổ đen hiện ra, sau khoảng 2 giây trình duyệt tự mở trang chủ.
   - Lần chạy đầu tiên, chương trình tự tạo cơ sở dữ liệu và ảnh sản phẩm (vài giây).
   - Nếu trình duyệt không tự mở, gõ địa chỉ in trong cửa sổ đen, thường là **http://127.0.0.1:8000**.
4. **Để tắt web:** đóng cửa sổ đen.

> Trong lúc dùng web, **không đóng cửa sổ đen**. Đó là "máy chủ" đang chạy trên máy bạn.

## 3. Tài khoản demo

| Vai trò | Email | Mật khẩu | Vào được |
|---|---|---|---|
| Quản trị viên | `admin@nhipmobile.vn` | `Admin@123` | Toàn bộ trang quản trị |
| Nhân viên | `nhanvien@nhipmobile.vn` | `Nhanvien@123` | Đơn hàng, khách hàng, hộp thư (bị che SĐT/địa chỉ khách; không vào sản phẩm, kho, marketing, báo cáo) |
| Người mua | `khach@nhipmobile.vn` | `Khach@123` | Trang mua hàng |

Ở trang Đăng nhập có sẵn nút **"Điền"** để điền nhanh các tài khoản này.

## 4. Ba file bấm đúp

| File | Dùng khi nào |
|---|---|
| `chay_web.bat` | Mỗi lần muốn mở website |
| `lam_moi_du_lieu.bat` | Trước buổi demo, để đưa dữ liệu về như ban đầu. **Tắt web trước khi chạy.** |
| `chay_kiem_thu.bat` | Chạy 101 kiểm thử tự động (gồm 17 test case của đặc tả) rồi mở bảng kết quả `tai-lieu/ket-qua-kiem-thu.html`. Dòng `OK` là tất cả đều đạt |

## 5. Những gì đã có (Giai đoạn 1)

- Cơ sở dữ liệu thật **31 bảng** (xem `tai-lieu/co-so-du-lieu.html`), với dữ liệu mẫu:
  - 30 điện thoại, 25 phụ kiện, 177 phiên bản (dung lượng × màu)
  - 12 khách hàng, 45 đơn hàng trong 60 ngày, 38 đánh giá, 4 mã giảm giá, 3 cửa hàng
- **Trang chủ** lấy dữ liệu thật: banner, giá sốc (tự làm mới mỗi ngày lúc 0 giờ), bán chạy, tầm giá, phụ kiện, mới về, chọn máy theo nhu cầu, tin tức.
- **Tìm kiếm** có gợi ý khi gõ, gõ không dấu vẫn ra (thử: `dien thoai samsung`, `op lung`).
- **Đăng nhập / đăng xuất**, sai mật khẩu 5 lần thì khóa 15 phút.
- **Trang quản trị – Tổng quan**: doanh thu 30 ngày, đơn chờ xác nhận, hàng sắp hết, đơn mới nhất.
- Các trang chưa làm hiển thị "Sẽ có ở Giai đoạn X" thay vì báo lỗi.

## 5b. Những gì có thêm ở Giai đoạn 2

- **Danh mục Điện thoại** (`/dien-thoai`): lọc theo hãng, mức giá (hoặc tự nhập khoảng giá), nhu cầu, RAM, bộ nhớ, tính năng (5G, 120Hz, sạc nhanh); 6 kiểu sắp xếp; "Xem thêm"; mỗi lựa chọn có số sản phẩm còn lại. Bộ lọc nằm trên địa chỉ trang nên bấm vào máy rồi bấm Quay lại vẫn giữ nguyên.
- **Danh mục Phụ kiện** (`/phu-kien`): lọc theo loại, hãng, giá và **"Dùng cho máy"**.
- **Trang chi tiết**: chọn dung lượng và màu thì giá, ảnh, tồn kho, mã SKU đổi ngay; màu hết hàng bị gạch và không bấm được; tab Mô tả / Thông số / Đánh giá (lọc theo số sao); phụ kiện dùng được cho máy; sản phẩm tương tự; câu hỏi thường gặp; trên điện thoại có thanh "Mua ngay" dính đáy màn hình.
- **So sánh** (`/so-sanh`): tối đa 3 máy, ô xanh là máy nổi trội ở tiêu chí đó, nút "Chỉ hiện điểm khác nhau".
- **Chọn máy theo nhu cầu** (`/chon-may`): 3 câu hỏi, gợi ý 3 máy còn hàng kèm lý do.

**Thử nhanh:** vào Điện thoại → bấm Samsung + "5 – 10 triệu" → bấm một máy → bấm Quay lại (bộ lọc vẫn còn). Vào iPhone 17 Pro Max → chọn 1TB → màu Bạc bị gạch vì hết hàng.

## 5c. Những gì có thêm ở Giai đoạn 3 – website đã bán được hàng

- **Giỏ hàng** (`/gio-hang`): nút "Thêm vào giỏ" và "Mua ngay" đã hoạt động thật; mỗi phiên bản tối đa 3 cái; xóa có nút **Hoàn tác**; gợi ý phụ kiện dùng được cho máy trong giỏ; cảnh báo nếu sản phẩm vừa hết hàng.
- **Mã giảm giá**: `SINHVIEN500` (−500.000₫, đơn từ 5 triệu, mỗi khách 1 lần), `PHUKIEN10` (−10%, tối đa 200.000₫), `FREESHIP30` (trừ phí giao), `THANG10` (đã hết hạn, để thử báo lỗi).
- **Thanh toán** (`/thanh-toan`): không cần tài khoản; giao tận nơi (34 tỉnh/thành mới) hoặc nhận tại 3 cửa hàng; COD, chuyển khoản QR, ví điện tử (mô phỏng); bắt buộc tích ô đồng ý điều khoản.
- **Đặt hàng thành công**: mã đơn dạng `NM2611110001`; với chuyển khoản có mã QR minh họa và nút **"Thanh toán thành công / thất bại"** để mô phỏng.
- **Tra cứu đơn** (`/tra-cuu-don-hang`): nhập mã đơn + số điện thoại, xem dòng thời gian trạng thái, **hủy đơn** khi còn "Chờ xác nhận" (hàng tự trả về kho).
- **Hộp thư mô phỏng** (trang quản trị → Hộp thư mô phỏng): xem các email xác nhận / hủy đơn / thanh toán mà hệ thống "gửi" cho khách.

**Quy tắc chạy ngầm đã có:** máy chủ tự tính tiền (sửa giá trên trình duyệt vô tác dụng), tồn kho không bao giờ âm, bấm Đặt hàng 2 lần vẫn 1 đơn, 2 người cùng mua chiếc cuối chỉ 1 người được, mỗi SĐT tối đa 3 đơn chờ xác nhận.

**Thử nhanh:** thêm 1 điện thoại vào giỏ → nhập `SINHVIEN500` → Tiến hành đặt hàng → điền thông tin, chọn Chuyển khoản QR → Đặt hàng → bấm "Thanh toán thành công" → vào Tra cứu đơn hàng, nhập mã đơn + SĐT → Hủy đơn → đăng nhập admin xem Hộp thư mô phỏng.

## 5d. Những gì có thêm ở Giai đoạn 4 – tài khoản người mua

- **Đăng ký** (`/dang-ky`): họ tên, SĐT, email, mật khẩu (≥ 8 ký tự, có chữ và số), đồng ý điều khoản. Nếu SĐT + email này từng đặt hàng khi chưa có tài khoản, các đơn cũ **tự gắn vào tài khoản**.
- **Quên mật khẩu**: nhập email → liên kết đặt lại nằm trong **Hộp thư mô phỏng** (trang quản trị). Liên kết hiệu lực 30 phút, dùng 1 lần.
- **Trang tài khoản** (bấm tên của bạn trên đầu trang → Tài khoản của tôi):
  - **Tổng quan**: số đơn, tổng chi tiêu, sửa họ tên, 3 đơn gần nhất.
  - **Đơn hàng của tôi**: lọc theo tab (Chờ xác nhận / Đang xử lý / Đã giao / Đã hủy), xem chi tiết, hủy đơn đang chờ.
  - **Đánh giá**: danh sách sản phẩm chờ đánh giá (chỉ đơn đã giao), viết đánh giá 1–5 sao, đánh giá chờ admin duyệt.
  - **Yêu thích**: bấm ♡ ở trang sản phẩm để lưu (cần đăng nhập).
  - **Sổ địa chỉ**: tối đa 5 địa chỉ, 1 địa chỉ mặc định được điền sẵn khi thanh toán.
  - **Đổi mật khẩu**: đổi xong các thiết bị khác tự đăng xuất.
- **Giỏ hàng theo tài khoản**: đăng xuất thì giỏ được cất lại; đăng nhập lại vẫn còn. Nếu trước khi đăng nhập bạn đã chọn thêm sản phẩm, hai giỏ được **gộp** lại.

**Thử nhanh:** đăng nhập `khach@nhipmobile.vn` → Đánh giá → Viết đánh giá cho 1 sản phẩm → vào Đơn hàng của tôi → mở trang một điện thoại, bấm ♡ → Yêu thích. Thử Đăng ký bằng SĐT `0987654321` + email `lan.tran@example.com` để thấy đơn cũ tự gắn vào.

## 5e. Những gì có thêm ở Giai đoạn 5 – trang quản trị

Đăng nhập `admin@nhipmobile.vn` → bấm tên → **Vào trang quản trị** (hoặc gõ `localhost:8000/quan-tri`).

- **Đơn hàng**: lọc theo trạng thái, tìm theo mã/tên/SĐT, lọc ngày. Mở một đơn để bấm nút bước tiếp theo: Xác nhận → Đóng gói → Bàn giao vận chuyển (chọn hãng, mã vận đơn) → Giao thành công → Hoàn tất. Web **không cho nhảy cóc**. Đơn nhận tại cửa hàng thì bỏ qua bước vận chuyển. Có hủy đơn (chọn lý do, tự nhả hàng giữ), ghi chú nội bộ, đổi/trả → hoàn tiền (hàng tự về kho). Mỗi bước gửi email vào Hộp thư mô phỏng.
- **Sản phẩm**: thêm/sửa/ẩn; thông số gõ theo dòng `Nhóm | Tên | Giá trị`; bảng phiên bản (đổi giá → có **lịch sử giá**); tải ảnh PNG/JPG/WEBP ≤ 3 MB (tệp giả ảnh bị chặn); phụ kiện chọn được "dùng cho máy nào".
- **Kho hàng**: nhập kho, điều chỉnh ± (bắt buộc ghi lý do, không được giảm dưới số đang giữ cho đơn), đặt ngưỡng cảnh báo, xem nhật ký kho.
- **Khách hàng**: danh sách, chi tiêu, lịch sử đơn, đánh giá đã viết.
- **Mã giảm giá**: tạo/sửa/tắt mã, xem đã dùng bao nhiêu lần, đã giảm bao nhiêu tiền.
- **Banner & giá sốc**: sửa chữ, màu, ảnh, đường dẫn của banner trang chủ; sửa giá sốc, số suất, thêm/gỡ sản phẩm.
- **Duyệt đánh giá**: duyệt cho hiện hoặc ẩn; điểm sao của sản phẩm tự tính lại.
- **Báo cáo**: 7/30/90 ngày, doanh thu theo ngày, bán chạy, theo nhóm hàng, thanh toán, lý do hủy; **xuất CSV** (mở bằng Excel, đúng tiếng Việt).
- Quy ước: **doanh thu = đơn đã hoàn tất**, tính theo ngày hoàn tất (Tổng quan và Báo cáo cùng một con số).

**Thử nhanh:** (1) Ở trang khách đặt một đơn. (2) Vào Quản trị → Đơn hàng → mở đơn vừa đặt → bấm lần lượt các bước đến **Hoàn tất** → về Tổng quan thấy doanh thu tăng. (3) Sản phẩm → Thêm sản phẩm → tạo máy mới, thêm 2 phiên bản, tải 1 ảnh → bấm "Xem trên website". (4) Đăng xuất, đăng nhập `nhanvien@nhipmobile.vn` → thấy SĐT khách bị che, vào `/quan-tri/bao-cao` bị chặn.

## 5f. Những gì có thêm ở Giai đoạn 6 – hoàn thiện

- **Tin tức** (`/tin-tuc`): 5 bài viết đầy đủ (so sánh iPhone 17 và 17 Air, mẹo giữ pin, chọn củ sạc, điện thoại dưới 5 triệu, kính chống nhìn trộm). Cuối mỗi bài tự hiện các sản phẩm được nhắc tới, bấm "Thêm vào giỏ" ngay được.
- **Trung tâm hỗ trợ** (`/ho-tro`, menu "Hỗ trợ"): ô tìm câu hỏi và 9 trang:
  - Hướng dẫn mua hàng, Câu hỏi thường gặp (gõ từ khóa để lọc, không cần dấu).
  - Chính sách giao hàng, Đổi trả và bảo hành (có **Tra cứu bảo hành**: nhập mã đơn + SĐT để xem còn bảo hành đến ngày nào), Bảo mật dữ liệu cá nhân, Điều khoản sử dụng.
  - Giới thiệu, Hệ thống cửa hàng (có nút xem bản đồ), Liên hệ (form gửi câu hỏi: báo lỗi từng ô; gửi xong có email xác nhận trong Hộp thư mô phỏng).
- Phí giao hàng, giới hạn số lượng... trong các trang chính sách **đọc thẳng từ `config.py`**, đổi cấu hình là trang tự đổi theo.
- **Trang lỗi** dễ dùng hơn: không tìm thấy trang thì có ô tìm kiếm và lối tắt; không có quyền thì có nút đăng nhập tài khoản khác.
- **Điện thoại**: đã rà toàn bộ trang ở khổ 390px; không trang nào bị tràn ngang; nút chuyển banner và nút So sánh to hơn cho dễ bấm.

**Thử nhanh:** bấm "Hỗ trợ" trên menu → gõ "huy" vào ô tìm → mở Đổi trả và bảo hành → tra cứu bảo hành bằng một đơn trong trang quản trị (mã đơn + SĐT) → vào Liên hệ, bấm Gửi khi để trống để xem báo lỗi, rồi gửi thật và mở Hộp thư mô phỏng. Để xem giao diện điện thoại ngay trên máy tính: trong Chrome bấm F12, rồi bấm Ctrl + Shift + M và chọn một mẫu điện thoại ở thanh trên cùng.

## 5g. Giai đoạn 7 – kiểm thử và bàn giao

Các tài liệu trong thư mục `tai-lieu/` (bấm đúp để mở bằng trình duyệt, in ra PDF bằng Ctrl + P):

| Tài liệu | Dùng để |
|---|---|
| `ket-qua-kiem-thu.html` | **Bảng kết quả kiểm thử**: 17 test case (mong đợi / thực tế / Đạt), toàn bộ kiểm thử theo giai đoạn, đánh giá 10 yêu cầu phi chức năng, danh sách lỗi đã sửa. Tự tạo lại mỗi lần chạy `chay_kiem_thu.bat` |
| `kich-ban-demo.html` | **Kịch bản demo 5 phút**: chuẩn bị, từng bước kèm lời nói, xử lý sự cố, câu hỏi thường gặp, phiếu thử nghiệm 5 người dùng |
| `doi-chieu-chuc-nang.html` | **Bảng đối chiếu**: FR-01 → FR-20 và US-01 → US-10 ↔ trang ↔ file code ↔ bài kiểm thử; tài khoản demo |
| `co-so-du-lieu.html`, `lo-trinh.html` | Sơ đồ CSDL và lộ trình (đã có từ trước) |

Thêm ở giai đoạn này:
- **Thanh toán trực tuyến mô phỏng theo VNPay**: cổng giả lập gửi thông báo có chữ ký về máy chủ; chữ ký sai hoặc số tiền bị sửa thì đơn không đổi trạng thái và cảnh báo được ghi vào `database/thanh-toan.log` (TC-16).
- **Ô SĐT ở trang thanh toán báo lỗi ngay trên trình duyệt**, form không gửi đi khi sai (TC-07).
- Người mua chậm hơn ở chiếc máy cuối nhận thông báo rõ: "…vừa được người khác mua hết" (TC-08).
- Quản trị → Sản phẩm: **Tạo nhanh nhiều phiên bản** (2 dung lượng × 3 màu = 6 SKU; thiếu giá thì không tạo và tô đỏ ô) (US-07).
- Quản trị → **Hãng & danh mục**: thêm/sửa hãng, thêm/ẩn loại phụ kiện (FR-15).

Máy chưa cài Playwright thì 1 test case cần trình duyệt (TC-17, khổ 360px) hiện "Chưa chạy"; hai TC-02, TC-07 vẫn kiểm tra phần máy chủ. Muốn chạy đủ: mở cửa sổ dòng lệnh, gõ `py -m pip install playwright` rồi `py -m playwright install chromium`.

## 6. Gặp sự cố?

| Hiện tượng | Cách xử lý |
|---|---|
| Cửa sổ đen báo "CHUA TIM THAY PYTHON" | Cài lại Python, nhớ tích "Add python.exe to PATH" |
| Gõ `python` lại mở Microsoft Store | Dùng `chay_web.bat`, file này ưu tiên lệnh `py` nên không bị lỗi đó |
| Trang báo "Có lỗi xảy ra" | Chụp màn hình cửa sổ đen (có chi tiết lỗi) và gửi cho Claude |
| Muốn xóa hết dữ liệu đã thử | Tắt web → bấm `lam_moi_du_lieu.bat` → gõ `C` → Enter |
| Chữ hiển thị font khác bản xem thử | Máy đang không có mạng, web dùng font dự phòng của Windows. Không ảnh hưởng chức năng |

## 7. Cấu trúc thư mục

```
NhipMobile/
├── chay_web.bat, lam_moi_du_lieu.bat, chay_kiem_thu.bat
├── app.py              ← khởi động máy chủ
├── config.py           ← cấu hình (phí giao, giới hạn số lượng...)
├── core/               ← bộ khung web
├── database/           ← schema.sql (31 bảng), seed.py + seed_data.py + post_content.py (dữ liệu mẫu, bài viết)
├── services/           ← quy tắc nghiệp vụ
├── routes/shop, admin/ ← xử lý từng trang
├── templates/          ← giao diện HTML
├── static/             ← CSS, JavaScript, logo
├── uploads/            ← ảnh sản phẩm (tự sinh)
├── tests/              ← kiểm thử tự động (test_tc_dac_ta.py = 17 test case)
├── xuat_bao_cao_kiem_thu.py ← chạy kiểm thử + xuất bảng kết quả
├── tai-lieu/           ← sơ đồ CSDL, lộ trình, kết quả kiểm thử, kịch bản demo, bảng đối chiếu
└── xem-thu/            ← bản xem thử giao diện đã duyệt
```

## 8. Đưa web lên mạng để máy khác truy cập (Render, miễn phí)

Web được đặt trên máy chủ của Render, có địa chỉ dạng `https://nhip-mobile.onrender.com` mở được từ mọi máy, mọi điện thoại. Code lấy từ GitHub của bạn; mỗi lần đẩy code mới lên GitHub, Render tự cập nhật web.

**Làm một lần:**
1. Vào https://render.com → **Get Started** → chọn **GitHub** để đăng nhập bằng tài khoản GitHub.
2. Khi Render hỏi quyền truy cập GitHub, cho phép repo chứa dự án (chọn "Only select repositories" → chọn repo đó).
3. Trên Render bấm **New** → **Blueprint** → chọn repo → Render đọc file `render.yaml` và hiện dịch vụ `nhip-mobile`.
4. Render hỏi 2 giá trị **ADMIN_PASSWORD** và **STAFF_PASSWORD**: tự đặt 2 mật khẩu riêng (ví dụ `NhipAdmin#2026`), ghi lại. Đây là mật khẩu của `admin@nhipmobile.vn` và `nhanvien@nhipmobile.vn` trên bản online; trang đăng nhập online sẽ không hiện mật khẩu này.
5. Bấm **Apply / Deploy**. Đợi 2–4 phút đến khi thấy chữ **Live**, bấm vào địa chỉ `...onrender.com` ở đầu trang.

**Cần biết về gói miễn phí:**
- Không ai vào web 15 phút thì web "ngủ". Lần mở tiếp theo chờ khoảng 30–60 giây. Trước buổi demo, mở web trước vài phút.
- Mỗi lần web ngủ dậy hoặc cập nhật code, **dữ liệu trở về dữ liệu mẫu ban đầu** (đơn, tài khoản đăng ký mới… mất). Với web demo môn học điều này lại tiện: luôn sạch sẵn.
- Tài khoản khách demo `khach@nhipmobile.vn / Khach@123` vẫn hiện ở trang đăng nhập để người xem thử.
- Bản trên máy của bạn (`chay_web.bat`) không bị ảnh hưởng, vẫn dùng mật khẩu demo như cũ.
