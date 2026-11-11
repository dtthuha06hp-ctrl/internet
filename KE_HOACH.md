# Kế hoạch xây dựng website Nhịp Mobile

> Dự án môn Internet và Thương mại điện tử: website bán điện thoại và phụ kiện.
> Bám theo tài liệu "Nghiên cứu & Đặc tả Website Bán Điện Thoại" (Phần 9: bản thiết kế "Nhịp Mobile").
> Cập nhật: 10/11/2026

---

## 1. Những gì đã chốt

| Hạng mục | Quyết định |
|---|---|
| Tên thương hiệu | **Nhịp Mobile**, slogan "Giá rõ ràng. Chọn máy dễ dàng." |
| Màu chủ đạo | Xanh chàm `#2F3FD1`, giá màu đỏ san hô `#E5484D`, font Be Vietnam Pro |
| Mặt hàng | Điện thoại (Apple, Samsung, Xiaomi, OPPO, vivo) và phụ kiện (ốp lưng, kính cường lực, sạc, cáp, tai nghe, sạc dự phòng, đồng hồ thông minh) |
| Công nghệ | Python + cơ sở dữ liệu SQLite, không cần cài thêm thư viện |
| Cách chạy | Cài Python một lần, sau đó bấm đúp `chay_web.bat` là web tự mở trên trình duyệt. Web chạy ngay trên máy của bạn, không cần mạng |
| Ảnh sản phẩm | Hình minh họa tự vẽ (tránh vi phạm bản quyền). Có thể thay ảnh thật trong trang quản trị |
| Giao diện | Đã duyệt bản xem thử trang chủ (`xem-thu/trang-chu.html`) |
| Thanh toán, email | Mô phỏng: COD, chuyển khoản QR, ví điện tử; "email" xác nhận hiện trong hộp thư mô phỏng |

### Giải thích ngắn: "máy chủ web" là gì?
Đây là phần chạy ngầm giúp web **có tài khoản, lưu đơn hàng và cho admin thấy đơn khách vừa đặt**, giống mọi trang thương mại điện tử. Ở dự án này, phần đó chạy ngay trên máy tính của bạn: không phải thuê, không phải cấu hình. Bạn chỉ cần bấm đúp `chay_web.bat`.

---

## 2. Hai loại tài khoản

| Tài khoản | Đăng nhập | Làm được gì |
|---|---|---|
| **Người mua** | Nút "Đăng nhập" trên đầu trang (cũng có thể mua không cần đăng nhập) | Xem máy, thêm giỏ, đặt hàng, xem đơn của mình, hủy đơn đang chờ, viết đánh giá, lưu yêu thích |
| **Admin (quản trị)** | Cùng nút đăng nhập; tài khoản admin thấy thêm mục "Quản trị" | Quản lý sản phẩm, đơn hàng, kho, khách hàng, mã giảm giá, banner, xem báo cáo doanh thu |
| Nhân viên (phụ) | Như admin | Chỉ xử lý đơn hàng, không sửa giá, không xem báo cáo |

**Tài khoản demo** (tạo sẵn trong dữ liệu mẫu):

| Vai trò | Email | Mật khẩu |
|---|---|---|
| Admin | `admin@nhipmobile.vn` | `Admin@123` |
| Nhân viên | `nhanvien@nhipmobile.vn` | `Nhanvien@123` |
| Người mua | `khach@nhipmobile.vn` | `Khach@123` |

---

## 3. Danh sách chức năng

### A. Phía người mua
1. **Trang chủ:** banner tự chuyển, logo hãng, Giá sốc hôm nay (đếm ngược), Bán chạy, Tầm giá, Phụ kiện, Mới về, Chọn máy theo nhu cầu, cam kết, tin tức.
2. **Danh mục điện thoại:** lọc theo hãng, giá, RAM, bộ nhớ, nhu cầu; sắp xếp; giữ bộ lọc khi quay lại.
3. **Danh mục phụ kiện:** lọc theo loại, giá, dòng máy tương thích.
4. **Tìm kiếm** có gợi ý, gõ không dấu vẫn ra.
5. **Trang chi tiết sản phẩm:** chọn dung lượng và màu (giá, tồn kho đổi theo), màu hết hàng bị làm mờ, Mua ngay / Thêm vào giỏ, tab Mô tả / Thông số / Đánh giá, phụ kiện mua kèm, sản phẩm tương tự, câu hỏi thường gặp.
6. **So sánh** tối đa 3 máy.
7. **Chọn máy theo nhu cầu:** 3 câu hỏi, gợi ý 3 máy.
8. **Giỏ hàng:** 1–3 cái mỗi món, xóa, mã giảm giá, phí giao.
9. **Thanh toán không cần tài khoản:** thông tin người nhận, giao tận nơi hoặc nhận tại cửa hàng, COD / chuyển khoản QR / ví (mô phỏng), ô đồng ý điều khoản.
10. **Đặt hàng thành công:** mã đơn (ví dụ NM2611100001), mã QR nếu chuyển khoản.
11. **Tra cứu đơn** bằng mã đơn + SĐT, xem dòng thời gian trạng thái, hủy khi còn "Chờ xác nhận".
12. **Tài khoản:** đăng ký, đăng nhập, quên mật khẩu (mô phỏng), đơn của tôi, sổ địa chỉ, yêu thích, đánh giá sau khi nhận hàng.
13. **Trang thông tin:** giới thiệu, cửa hàng, chính sách giao hàng, đổi trả và bảo hành, bảo mật, điều khoản, hướng dẫn mua hàng, tin tức. Nhãn "Website mô phỏng phục vụ học tập".

### B. Phía admin
1. **Tổng quan:** doanh thu hôm nay, đơn mới, đơn chờ xác nhận, hàng sắp hết, biểu đồ doanh thu 30 ngày.
2. **Sản phẩm:** thêm, sửa, ẩn; phiên bản dung lượng × màu; ảnh; thông số; danh mục; hãng.
3. **Đơn hàng:** lọc theo trạng thái; Xác nhận → Chuẩn bị → Đang giao → Đã giao → Đã thu tiền → Hoàn tất; hủy phải có lý do (hàng tự trả về kho).
4. **Khách hàng:** danh sách, lịch sử mua, tổng chi tiêu.
5. **Kho:** nhập kho, điều chỉnh có lý do, lịch sử, cảnh báo sắp hết.
6. **Marketing:** mã giảm giá, banner trang chủ, chương trình giá sốc, duyệt đánh giá.
7. **Báo cáo:** doanh thu, sản phẩm bán chạy, tỷ lệ hủy; xuất file mở bằng Excel.
8. **Hộp thư mô phỏng:** xem các "email" đã gửi cho khách.

### C. Quy tắc chạy ngầm (theo Phần 6.6 của tài liệu)
- Tổng tiền luôn do máy chủ tính, không thể sửa giá từ trình duyệt.
- Tồn kho không bao giờ âm, kể cả khi 2 người cùng mua chiếc máy cuối cùng.
- Bấm "Đặt hàng" 2 lần vẫn chỉ ra 1 đơn.
- Mỗi SĐT tối đa 3 đơn đang chờ xác nhận; mỗi món tối đa 3 cái/đơn.
- Đơn hàng lưu giá tại thời điểm mua, nên đổi giá sau này không làm sai báo cáo.
- Trạng thái đơn chỉ đi theo đúng quy trình, không nhảy cóc. Mọi thay đổi đều ghi lịch sử (ai, lúc nào).
- Mật khẩu được mã hóa; sai 5 lần thì khóa 15 phút.
- Lưu thời điểm khách đồng ý điều khoản xử lý dữ liệu cá nhân.

### D. Phần mô phỏng, không làm thật
Cổng VNPay/MoMo, gửi email/SMS thật, chat trực tuyến (thay bằng nút Zalo), trả góp thật.

---

## 4. Cấu trúc thư mục

```
NhipMobile/
├── chay_web.bat            ← Bấm đúp để chạy web
├── lam_moi_du_lieu.bat     ← Đưa dữ liệu về như ban đầu (dùng trước buổi demo)
├── HUONG_DAN.md            ← Hướng dẫn cài đặt, chạy, tài khoản demo
├── KE_HOACH.md             ← File này
├── app.py                  ← Điểm khởi động
├── config.py               ← Cấu hình: tên shop, phí giao, giới hạn số lượng…
├── core/                   ← Bộ khung web: định tuyến, giao diện, phiên đăng nhập, bảo mật, kết nối dữ liệu
├── database/               ← schema.sql (các bảng), seed.py (dữ liệu mẫu), nhipmobile.db (tự sinh)
├── services/               ← Quy tắc nghiệp vụ: sản phẩm, giỏ, đơn hàng, kho, mã giảm giá, khách, đánh giá, báo cáo, hộp thư
├── routes/shop/            ← Xử lý các trang người mua
├── routes/admin/           ← Xử lý các trang quản trị
├── templates/              ← Khuôn giao diện HTML (shop, admin, email)
├── static/                 ← CSS, JavaScript, logo, banner
├── uploads/products/       ← Ảnh sản phẩm
├── chay_kiem_thu.bat       ← Chạy kiểm thử tự động
├── tests/                  ← Kiểm thử tự động (Phần 9.6 tài liệu)
└── xem-thu/                ← Bản xem thử giao diện đã duyệt
```

---

## 5. Lộ trình 7 giai đoạn

Hết mỗi giai đoạn sẽ có bản chạy được để bạn bấm thử và góp ý trước khi làm tiếp.

| # | Giai đoạn | Nội dung | Bạn kiểm tra | Trạng thái |
|---|---|---|---|---|
| 0 | Chuẩn bị | Đọc tài liệu, chốt chức năng, chốt công nghệ, duyệt giao diện trang chủ | Xem `xem-thu/trang-chu.html` | ✅ Xong |
| 1 | **Nền móng** | Bộ khung web; cơ sở dữ liệu (20 bảng + bảng phụ); dữ liệu mẫu: ~30 điện thoại (~100 phiên bản), 25 phụ kiện, 10 khách, 20 đơn cũ, mã giảm giá, 3 tài khoản demo; `chay_web.bat`; `HUONG_DAN.md` | Bấm đúp `chay_web.bat` → trang chủ hiện dữ liệu từ kho | ✅ Xong (11/11) |
| 2 | **Xem và chọn hàng** | Trang chủ thật, danh mục điện thoại và phụ kiện + bộ lọc, tìm kiếm, trang chi tiết sản phẩm, so sánh, chọn máy theo nhu cầu | Lọc theo hãng và giá; chọn màu hết hàng (không bấm được) | ✅ Xong (11/11) |
| 3 | **Mua hàng** | Giỏ hàng, mã giảm giá, thanh toán, đặt hàng thành công + QR, tra cứu và hủy đơn, hộp thư mô phỏng, các quy tắc chạy ngầm | Đặt trọn một đơn; thử mã SINHVIEN500 khi giỏ dưới 5 triệu | ✅ Xong (11/11) |
| 4 | **Tài khoản người mua** | Đăng ký, đăng nhập, khóa khi sai 5 lần, quên mật khẩu, đơn của tôi, sổ địa chỉ, yêu thích, đánh giá, gộp giỏ khi đăng nhập | Đăng nhập tài khoản khách, xem đơn, viết đánh giá | ✅ Xong (11/11) |
| 5 | **Trang quản trị** | Tổng quan + biểu đồ, sản phẩm, đơn hàng, khách hàng, kho, mã giảm giá, banner, giá sốc, duyệt đánh giá, báo cáo + xuất Excel, phân quyền admin/nhân viên | Đặt 1 đơn ở trang khách, vào admin xử lý đến khi hoàn tất, thấy doanh thu tăng | ✅ Xong (11/11) |
| 6 | **Hoàn thiện** | Trang giới thiệu, cửa hàng, 4 trang chính sách, hướng dẫn mua hàng, câu hỏi thường gặp, 3–5 bài tin tức; rà giao diện điện thoại; thông báo lỗi rõ ràng | Mở web trên điện thoại hoặc thu nhỏ cửa sổ | ✅ Xong (11/11) |
| 7 | **Kiểm thử và bàn giao** | Chạy 17 test case + bảng kết quả Đạt/Không đạt; hoàn thiện hướng dẫn; kịch bản demo 5 phút; bảng đối chiếu chức năng ↔ trang ↔ file code cho báo cáo | Tập demo theo kịch bản | ✅ Xong (11/11) |

**Mốc quan trọng:** hết Giai đoạn 3 là web đã **bán được hàng** từ đầu đến cuối (đúng "lát cắt dọc" Phần 10 của tài liệu).

### Để sau, chỉ làm nếu cần
- Đưa web lên mạng để có link online cho giảng viên.
- Cổng thanh toán VNPay thử nghiệm.
- Xuất hóa đơn PDF.
- Tích điểm thành viên.

---

## 6. Việc bạn cần làm

1. **Cài Python** (chỉ một lần): vào python.org → Downloads → tải bản cho Windows → chạy file cài. Ở màn hình đầu tiên, **tích ô "Add python.exe to PATH"**, rồi bấm Install Now.
2. Sau mỗi giai đoạn: chạy thử theo cột "Bạn kiểm tra", rồi nhắn lại những chỗ muốn chỉnh.
3. Trước buổi demo: bấm `lam_moi_du_lieu.bat` để dữ liệu sạch.

## 7. Nhật ký thay đổi

| Ngày | Nội dung |
|---|---|
| 12/11/2026 | Đưa web lên mạng: https://nhip-mobile.onrender.com (Render, gói miễn phí, tự cập nhật từ GitHub dtthuha06hp-ctrl/internet). Sửa 2 lỗi chỉ xuất hiện trên máy chủ: máy chủ chạy giờ UTC nên đồng hồ giá sốc về 00:00 và trang chủ tự tải lại liên tục sau 00:00 giờ Việt Nam → đặt giờ Việt Nam cho máy chủ, đồng hồ dùng số giây còn lại do máy chủ gửi; giá trên banner chưa tính giá sốc → dùng giá phải trả. 101 kiểm thử đạt |
| 11/11/2026 | Sửa 3 lỗi theo báo cáo kiểm thử lượt 3: **B5** hủy đơn mua giá sốc giờ trả lại suất giá sốc; **B6** gợi ý tìm kiếm, so sánh, chọn máy không còn giới hạn 200 sản phẩm; **B7** khung giá trên banner dựa vào đường dẫn thay vì tiêu đề. Thêm kiểm thử: đánh giá chờ duyệt không hiện trên trang sản phẩm (TC-66). 99 kiểm thử đạt trên SQLite 3.45 và 3.53 |
| 11/11/2026 | Sửa 4 lỗi do bạn kiểm thử trên máy Windows phát hiện: **B1** (nghiêm trọng) câu SQL ở chi tiết đơn không chạy trên SQLite bản cũ đi kèm Python Windows → 500 ở trang đặt hàng thành công, tra cứu, tài khoản, quản trị đơn; **B2** khóa đăng nhập theo thiết bị thay vì cả tài khoản; **B3** số lượng không hợp lệ báo lỗi thay vì tự thành 1; **B4** giá sốc tự sang ngày mới. Từ nay kiểm thử chạy trên cả SQLite 3.45 và 3.53 và duyệt tự động mọi trang bằng 4 vai trò; 96 kiểm thử đạt |
| 11/11/2026 | Xong Giai đoạn 7 – kiểm thử và bàn giao: 17 test case của đặc tả thành bộ kiểm thử tự động riêng (17/17 đạt, có chạy trình duyệt thật cho TC-02, TC-07, TC-17); bảng kết quả kiểm thử tự xuất (kèm 10 NFR và 16 lỗi đã sửa); kịch bản demo 5 phút (đã chạy thử trọn vòng bằng trình duyệt tự động); bảng đối chiếu FR/US ↔ trang ↔ code ↔ kiểm thử; bổ sung IPN có chữ ký (TC-16), kiểm tra SĐT trên trình duyệt (TC-07), tạo nhanh phiên bản theo ma trận (US-07), trang Hãng & danh mục (FR-15); 94 kiểm thử đạt. **Hoàn thành 7/7 giai đoạn** |
| 11/11/2026 | Xong Giai đoạn 6 – hoàn thiện: 5 bài tin tức viết đầy đủ (tự hiện sản phẩm được nhắc tới), trung tâm hỗ trợ với 9 trang (hướng dẫn mua hàng, câu hỏi thường gặp có ô lọc, giao hàng, đổi trả & bảo hành kèm tra cứu hạn bảo hành, bảo mật dữ liệu theo NĐ 13/2023, điều khoản, giới thiệu, cửa hàng, liên hệ gửi vào hộp thư mô phỏng); trang lỗi 404/403 có lối đi tiếp; rà toàn bộ trang ở khổ điện thoại 390px (không tràn ngang, vùng bấm đủ lớn); sửa lỗi ảnh bìa tin tức bị thu nhỏ; 74 kiểm thử đạt |
| 11/11/2026 | Xong Giai đoạn 5 – trang quản trị: xử lý đơn theo đúng quy trình (không nhảy cóc, nhận tại cửa hàng không qua vận chuyển, giao xong mới trừ kho, hoàn tiền thì nhập lại kho), sản phẩm + phiên bản + lịch sử giá + tải ảnh (chặn tệp không phải ảnh), kho (nhập, điều chỉnh bắt buộc lý do, không xuống dưới số đang giữ, nhật ký), khách hàng (nhân viên bị che SĐT/địa chỉ), mã giảm giá, banner, giá sốc, duyệt đánh giá (tự tính lại điểm sao), báo cáo 7/30/90 ngày + xuất CSV mở bằng Excel; doanh thu Tổng quan và Báo cáo dùng chung một cách tính; 65 kiểm thử đạt |
| 10/11/2026 | Chốt chức năng, công nghệ, cấu trúc thư mục; duyệt giao diện trang chủ; lập kế hoạch 7 giai đoạn |
| 11/11/2026 | Xong Giai đoạn 4: đăng ký (đơn cũ đặt bằng cùng SĐT + email tự gắn vào tài khoản), quên mật khẩu qua hộp thư mô phỏng (liên kết ký số, 30 phút, dùng 1 lần), đổi mật khẩu (đăng xuất thiết bị khác), đơn của tôi theo tab + hủy đơn, sổ địa chỉ (tối đa 5, 1 mặc định, tự điền khi thanh toán), yêu thích, viết đánh giá chỉ khi đã nhận hàng (chờ duyệt), giỏ hàng được giữ theo tài khoản và gộp khi đăng nhập; 54 kiểm thử đạt |
| 11/11/2026 | Xong Giai đoạn 3 – website bán được hàng: giỏ hàng (tối đa 3/phiên bản, hoàn tác khi xóa, gợi ý phụ kiện), 4 mã giảm giá, thanh toán không cần tài khoản (COD / chuyển khoản QR / ví mô phỏng), đặt hàng trong 1 transaction (giữ hàng, chống bấm 2 lần, tối đa 3 đơn chờ/SĐT, 2 người mua chiếc cuối chỉ 1 người được), tra cứu & hủy đơn, hộp thư mô phỏng; 41 kiểm thử đạt |
| 11/11/2026 | Xong Giai đoạn 2: danh mục điện thoại & phụ kiện có bộ lọc (lọc không tải lại trang, giữ trên URL), trang chi tiết chọn dung lượng/màu, so sánh 3 máy, chọn máy theo nhu cầu; giá sốc áp dụng đúng trên thẻ và trang chi tiết; 25 kiểm thử đạt |
| 11/11/2026 | Xong Giai đoạn 1: CSDL 31 bảng + dữ liệu mẫu, trang chủ từ dữ liệu thật, tìm kiếm không dấu, đăng nhập (khóa sau 5 lần sai), tổng quan quản trị, 12 kiểm thử tự động đạt |
