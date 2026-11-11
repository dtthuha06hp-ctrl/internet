# Định nghĩa CSDL Nhịp Mobile: dùng để sinh tài liệu HTML (và sau này schema.sql)
# Mỗi cột: (tên, kiểu, khóa, ràng buộc, mô tả)

GROUPS = [
 ("acc", "Tài khoản & khách hàng", "#2F3FD1"),
 ("prd", "Sản phẩm", "#0F7A5C"),
 ("inv", "Kho hàng", "#B45309"),
 ("ord", "Giỏ hàng & đơn hàng", "#B4232A"),
 ("mkt", "Marketing", "#7C3AED"),
 ("cnt", "Tương tác & nội dung", "#0E7490"),
]

T = []
def t(name, group, vi, desc, cols, core=True, rows=""):
    T.append(dict(name=name, group=group, vi=vi, desc=desc, cols=cols, core=core, rows=rows))

ID = ("id", "INTEGER", "PK", "tự tăng", "Mã định danh")
CA = ("created_at", "TEXT", "", "mặc định: lúc tạo", "Thời điểm tạo (ISO 8601)")
UA = ("updated_at", "TEXT", "", "", "Thời điểm sửa gần nhất (phát hiện 2 người sửa cùng lúc)")

# ---------------- Tài khoản ----------------
t("users","acc","Tài khoản đăng nhập","Tài khoản của người mua, nhân viên và admin. Mật khẩu chỉ lưu dạng đã mã hóa.",[
 ID,
 ("email","TEXT","UQ","NOT NULL","Email đăng nhập"),
 ("phone","TEXT","UQ","10 số","Số điện thoại (cũng dùng để đăng nhập)"),
 ("password_hash","TEXT","","NOT NULL","Mật khẩu đã băm PBKDF2 + salt"),
 ("full_name","TEXT","","NOT NULL","Họ tên hiển thị"),
 ("role","TEXT","","customer / staff / admin","Vai trò, quyết định được vào trang nào"),
 ("status","TEXT","","active / locked","Khóa tài khoản khi lạm dụng"),
 ("failed_logins","INTEGER","","≥ 0","Số lần nhập sai mật khẩu liên tiếp"),
 ("locked_until","TEXT","","","Khóa tạm 15 phút sau 5 lần sai"),
 CA],rows="3 tài khoản demo + 10 khách")
t("customers","acc","Hồ sơ người mua","Mọi người từng đặt hàng, kể cả khách không đăng ký (nhận diện bằng SĐT).",[
 ID,
 ("user_id","INTEGER","FK → users","có thể rỗng","Rỗng nếu là khách vãng lai"),
 ("full_name","TEXT","","NOT NULL","Họ tên"),
 ("phone","TEXT","UQ","NOT NULL, 10 số","SĐT, dùng để tra cứu đơn"),
 ("email","TEXT","","","Email nhận xác nhận đơn"),
 ("title","TEXT","","Anh / Chị","Danh xưng"),
 ("total_spent","INTEGER","","≥ 0","Tổng chi tiêu (đơn hoàn tất), đơn vị đồng"),
 ("order_count","INTEGER","","≥ 0","Số đơn đã đặt"),
 ("consent_at","TEXT","","","Lúc đồng ý xử lý dữ liệu cá nhân (Luật 91/2025)"),
 ("consent_version","TEXT","","","Phiên bản chính sách đã đồng ý"),
 CA],rows="~15")
t("addresses","acc","Sổ địa chỉ","Địa chỉ giao hàng đã lưu của khách thành viên.",[
 ID,
 ("customer_id","INTEGER","FK → customers","NOT NULL",""),
 ("receiver_name","TEXT","","NOT NULL","Tên người nhận"),
 ("receiver_phone","TEXT","","NOT NULL","SĐT người nhận"),
 ("province","TEXT","","NOT NULL","Tỉnh / thành phố"),
 ("ward","TEXT","","NOT NULL","Phường / xã"),
 ("street","TEXT","","NOT NULL","Số nhà, đường"),
 ("is_default","INTEGER","","0 / 1","Địa chỉ mặc định"),
],rows="~12")
t("sessions","acc","Phiên truy cập","Ghi nhớ ai đang đăng nhập và giỏ hàng của khách vãng lai qua cookie.",[
 ("token","TEXT","PK","ngẫu nhiên 32 byte","Mã phiên lưu trong cookie trình duyệt"),
 ("user_id","INTEGER","FK → users","có thể rỗng","Rỗng nếu chưa đăng nhập"),
 ("csrf_token","TEXT","","","Mã chống giả mạo form"),
 ("expires_at","TEXT","","","Hết hạn sau 7 ngày"),
 CA],core=False,rows="tự sinh")

# ---------------- Sản phẩm ----------------
t("categories","prd","Danh mục","Cây danh mục cha – con, ví dụ Phụ kiện > Ốp lưng.",[
 ID,
 ("parent_id","INTEGER","FK → categories","có thể rỗng","Danh mục cha (rỗng = gốc)"),
 ("name","TEXT","","NOT NULL","Tên hiển thị"),
 ("slug","TEXT","UQ","NOT NULL","Đường dẫn, ví dụ dien-thoai, op-lung"),
 ("kind","TEXT","","phone / accessory","Loại hàng, quyết định bộ lọc"),
 ("sort_order","INTEGER","","","Thứ tự trên menu"),
 ("is_active","INTEGER","","0 / 1","Ẩn / hiện"),
],rows="2 gốc + 8 con")
t("brands","prd","Hãng","Hãng sản xuất điện thoại và phụ kiện.",[
 ID,("name","TEXT","","NOT NULL","Apple, Samsung…"),("slug","TEXT","UQ","NOT NULL","apple, samsung…"),
 ("logo_url","TEXT","","","Ảnh logo"),("sort_order","INTEGER","","",""),
],rows="5 hãng ĐT + 4 hãng phụ kiện")
t("products","prd","Sản phẩm","Thông tin chung của một mẫu máy hoặc phụ kiện. Giá và tồn kho nằm ở từng phiên bản.",[
 ID,
 ("category_id","INTEGER","FK → categories","NOT NULL",""),
 ("brand_id","INTEGER","FK → brands","NOT NULL",""),
 ("name","TEXT","","NOT NULL","Galaxy A56 5G"),
 ("slug","TEXT","UQ","NOT NULL","galaxy-a56-5g"),
 ("short_desc","TEXT","","","Mô tả ngắn trên thẻ"),
 ("description","TEXT","","","Bài mô tả chi tiết"),
 ("needs","TEXT","","","Nhu cầu: cam, game, pin, slim (lọc + chọn máy)"),
 ("art","TEXT","","","Kiểu ảnh minh họa tự vẽ"),
 ("is_featured","INTEGER","","0 / 1","Hiện ở khối nổi bật"),
 ("is_new","INTEGER","","0 / 1","Nhãn \"Mới\""),
 ("is_active","INTEGER","","0 / 1","Ẩn thay vì xóa cứng"),
 ("rating_avg","REAL","","0 – 5","Điểm đánh giá trung bình"),
 ("rating_count","INTEGER","","≥ 0","Số đánh giá"),
 ("sold_count","INTEGER","","≥ 0","Số đã bán (xếp Bán chạy)"),
 CA,UA],rows="30 ĐT + 25 phụ kiện")
t("product_specs","prd","Thông số kỹ thuật","Thông số dạng nhóm – tên – giá trị, dùng cho tab Thông số và trang So sánh.",[
 ID,("product_id","INTEGER","FK → products","NOT NULL",""),
 ("spec_group","TEXT","","","Màn hình, Camera, Pin…"),("spec_name","TEXT","","","Kích thước"),
 ("spec_value","TEXT","","","6.7 inch"),("sort_order","INTEGER","","",""),
],rows="~600")
t("product_variants","prd","Phiên bản (SKU)","Một tổ hợp dung lượng × màu cụ thể. Đây là thứ khách thực sự mua.",[
 ID,("product_id","INTEGER","FK → products","NOT NULL",""),
 ("sku","TEXT","UQ","NOT NULL","SS-A56-128-DEN"),
 ("storage","TEXT","","","128GB (rỗng với phụ kiện)"),
 ("ram","TEXT","","","8GB"),
 ("color_name","TEXT","","","Xanh đậm"),
 ("color_hex","TEXT","","","#2B3A55 (chấm màu)"),
 ("list_price","INTEGER","","> 0","Giá gốc (đồng)"),
 ("sale_price","INTEGER","","> 0, ≤ list_price","Giá bán"),
 ("is_active","INTEGER","","0 / 1",""),
],rows="~100 ĐT + ~40 phụ kiện")
t("product_images","prd","Ảnh sản phẩm","Nhiều ảnh mỗi sản phẩm; ảnh có thể gắn với một màu cụ thể.",[
 ID,("product_id","INTEGER","FK → products","NOT NULL",""),
 ("variant_id","INTEGER","FK → product_variants","có thể rỗng","Rỗng = ảnh chung"),
 ("url","TEXT","","NOT NULL","Đường dẫn ảnh trong uploads/"),
 ("alt_text","TEXT","","","Mô tả ảnh (hỗ trợ đọc màn hình)"),
 ("sort_order","INTEGER","","",""),("is_main","INTEGER","","0 / 1","Ảnh đại diện"),
],rows="~150")
t("price_history","prd","Lịch sử giá","Mỗi lần admin đổi giá một SKU đều được ghi lại.",[
 ID,("variant_id","INTEGER","FK → product_variants","NOT NULL",""),
 ("old_price","INTEGER","","",""),("new_price","INTEGER","","",""),
 ("changed_by","INTEGER","FK → users","",""),("changed_at","TEXT","","",""),
],core=False,rows="tự sinh")
t("accessory_compat","prd","Phụ kiện tương thích","Phụ kiện nào dùng được cho máy nào: để gợi ý \"phụ kiện mua kèm\" ở trang điện thoại.",[
 ("accessory_id","INTEGER","PK, FK → products","","Sản phẩm phụ kiện"),
 ("phone_id","INTEGER","PK, FK → products","","Mẫu điện thoại dùng được"),
],core=False,rows="~60")

# ---------------- Kho ----------------
t("inventory","inv","Tồn kho","Số lượng hiện tại của từng SKU. Có thể bán = tồn thực − đang giữ cho đơn chưa giao.",[
 ID,("variant_id","INTEGER","FK → product_variants, UQ","NOT NULL","1 SKU – 1 dòng"),
 ("on_hand","INTEGER","","≥ 0","Tồn thực trong kho"),
 ("reserved","INTEGER","","≥ 0, ≤ on_hand","Đang giữ cho đơn chưa giao"),
 ("low_threshold","INTEGER","","mặc định 5","Ngưỡng cảnh báo sắp hết"),
 UA],rows="= số SKU")
t("inventory_transactions","inv","Nhật ký kho","Mọi biến động kho đều qua đây; không sửa tay con số tồn.",[
 ID,("variant_id","INTEGER","FK → product_variants","NOT NULL",""),
 ("type","TEXT","","import / reserve / release / sale / return / adjust","Loại biến động"),
 ("qty_change","INTEGER","","≠ 0","Số lượng (+ cộng, − trừ)"),
 ("reason","TEXT","","bắt buộc với adjust","Lý do"),
 ("order_id","INTEGER","FK → orders","có thể rỗng","Đơn liên quan"),
 ("created_by","INTEGER","FK → users","",""),CA],rows="tự sinh")

# ---------------- Đơn hàng ----------------
t("stores","ord","Cửa hàng","Cửa hàng giả lập để khách chọn \"Nhận tại cửa hàng\".",[
 ID,("name","TEXT","","",""),("address","TEXT","","",""),("province","TEXT","","",""),
 ("phone","TEXT","","",""),("open_hours","TEXT","","","8:00 – 21:30"),("is_active","INTEGER","","0 / 1",""),
],core=False,rows="3")
t("carts","ord","Giỏ hàng","Giỏ của khách vãng lai (theo phiên) hoặc của thành viên.",[
 ID,("customer_id","INTEGER","FK → customers","có thể rỗng",""),
 ("session_token","TEXT","FK → sessions","có thể rỗng","Giỏ khách chưa đăng nhập"),
 ("voucher_code","TEXT","","","Mã giảm giá đang áp"),
 ("status","TEXT","","active / ordered / merged",""),UA],rows="tự sinh")
t("cart_items","ord","Món trong giỏ","",[
 ID,("cart_id","INTEGER","FK → carts","NOT NULL",""),
 ("variant_id","INTEGER","FK → product_variants","NOT NULL",""),
 ("quantity","INTEGER","","1 – 3","Tối đa 3 cái/món"),
 ("added_at","TEXT","","",""),
],rows="UQ (cart_id, variant_id)")
t("orders","ord","Đơn hàng","Đơn đã đặt. Địa chỉ và giá được \"chụp lại\" để sau này đổi cũng không ảnh hưởng đơn cũ.",[
 ID,("order_code","TEXT","UQ","NOT NULL","NM + yyMMdd + số thứ tự, ví dụ NM2611100001"),
 ("customer_id","INTEGER","FK → customers","NOT NULL",""),
 ("status","TEXT","","10 trạng thái (xem sơ đồ)","Trạng thái đơn"),
 ("receiver_name","TEXT","","NOT NULL",""),("receiver_phone","TEXT","","NOT NULL",""),("receiver_title","TEXT","","Anh / Chị",""),
 ("delivery_method","TEXT","","home / store","Giao tận nơi hay nhận tại cửa hàng"),
 ("shipping_address","TEXT","","","Địa chỉ dạng văn bản (chụp lại)"),
 ("store_id","INTEGER","FK → stores","có thể rỗng","Nếu nhận tại cửa hàng"),
 ("subtotal","INTEGER","","≥ 0","Tạm tính"),("discount_amount","INTEGER","","≥ 0","Giảm giá"),
 ("shipping_fee","INTEGER","","≥ 0","Phí giao"),("total","INTEGER","","= subtotal − discount + ship","Tổng phải trả"),
 ("voucher_id","INTEGER","FK → vouchers","có thể rỗng",""),
 ("payment_method","TEXT","","cod / bank_qr / ewallet",""),
 ("payment_status","TEXT","","unpaid / pending / paid / refunded",""),
 ("note","TEXT","","","Ghi chú của khách"),("internal_note","TEXT","","","Ghi chú nội bộ của admin"),
 ("cancel_reason","TEXT","","bắt buộc khi hủy",""),
 ("idempotency_key","TEXT","UQ","","Chống bấm Đặt hàng 2 lần"),
 CA,UA],rows="20 đơn mẫu")
t("order_items","ord","Dòng hàng trong đơn","Lưu giá tại thời điểm mua, nên báo cáo doanh thu không bị sai khi đổi giá.",[
 ID,("order_id","INTEGER","FK → orders","NOT NULL",""),
 ("variant_id","INTEGER","FK → product_variants","NOT NULL",""),
 ("product_name","TEXT","","","Tên lúc mua"),("variant_label","TEXT","","","256GB · Xanh"),
 ("sku","TEXT","","",""),("unit_price","INTEGER","","> 0","Đơn giá lúc mua"),
 ("quantity","INTEGER","","1 – 3",""),("line_total","INTEGER","","= unit_price × quantity",""),
],rows="~35")
t("order_status_history","ord","Lịch sử trạng thái","Mỗi lần đơn đổi trạng thái: từ đâu, sang đâu, ai làm, lúc nào.",[
 ID,("order_id","INTEGER","FK → orders","NOT NULL",""),
 ("from_status","TEXT","","",""),("to_status","TEXT","","",""),
 ("note","TEXT","","",""),("changed_by","INTEGER","FK → users","có thể rỗng","Rỗng = khách / hệ thống"),
 ("changed_at","TEXT","","",""),
],rows="tự sinh")
t("payments","ord","Giao dịch thanh toán","Một đơn có thể có nhiều lần thanh toán (thử lại, hoàn tiền).",[
 ID,("order_id","INTEGER","FK → orders","NOT NULL",""),
 ("method","TEXT","","cod / bank_qr / ewallet",""),("amount","INTEGER","","> 0",""),
 ("status","TEXT","","pending / paid / failed / refunded",""),
 ("provider_txn_id","TEXT","UQ","có thể rỗng","Mã giao dịch phía cổng (chống ghi nhận 2 lần)"),
 ("paid_at","TEXT","","",""),CA],rows="tự sinh")
t("shipments","ord","Vận chuyển","Thông tin giao hàng của đơn.",[
 ID,("order_id","INTEGER","FK → orders, UQ","NOT NULL","1 đơn – 1 vận đơn"),
 ("carrier","TEXT","","","GHN, GHTK… (giả lập)"),("tracking_code","TEXT","","","Mã vận đơn"),
 ("shipped_at","TEXT","","",""),("delivered_at","TEXT","","",""),
],rows="tự sinh")

# ---------------- Marketing ----------------
t("vouchers","mkt","Mã giảm giá","Mã khách tự nhập ở giỏ hàng.",[
 ID,("code","TEXT","UQ","NOT NULL","SINHVIEN500"),("description","TEXT","","","Mô tả hiển thị cho khách"),
 ("type","TEXT","","fixed / percent","Giảm số tiền hay %"),("value","INTEGER","","> 0","500000 hoặc 10 (%)"),
 ("max_discount","INTEGER","","","Giảm tối đa (với %)"),("min_order","INTEGER","","≥ 0","Đơn tối thiểu"),
 ("usage_limit","INTEGER","","","Tổng số lượt"),("used_count","INTEGER","","≤ usage_limit","Đã dùng"),
 ("per_customer_limit","INTEGER","","mặc định 1","Lượt mỗi khách"),
 ("starts_at","TEXT","","",""),("ends_at","TEXT","","",""),("is_active","INTEGER","","0 / 1",""),
],rows="4 mã")
t("voucher_usages","mkt","Lượt dùng mã","Ai đã dùng mã nào, ở đơn nào: để chặn dùng quá lượt.",[
 ID,("voucher_id","INTEGER","FK → vouchers","NOT NULL",""),
 ("customer_id","INTEGER","FK → customers","NOT NULL",""),
 ("order_id","INTEGER","FK → orders","NOT NULL",""),("used_at","TEXT","","",""),
],rows="tự sinh")
t("promotions","mkt","Chương trình giá sốc","Giảm giá tự động theo khung giờ, có đếm ngược và giới hạn suất.",[
 ID,("name","TEXT","","","Giá sốc hôm nay"),("starts_at","TEXT","","",""),("ends_at","TEXT","","",""),
 ("is_active","INTEGER","","0 / 1",""),
],core=False,rows="1")
t("promotion_items","mkt","SKU trong giá sốc","",[
 ID,("promotion_id","INTEGER","FK → promotions","NOT NULL",""),
 ("variant_id","INTEGER","FK → product_variants","NOT NULL",""),
 ("promo_price","INTEGER","","< sale_price","Giá sốc"),("quota","INTEGER","","> 0","Số suất"),
 ("sold","INTEGER","","≤ quota","Đã bán"),
],core=False,rows="5")
t("banners","mkt","Banner trang chủ","Ảnh quảng cáo do admin quản lý.",[
 ID,("title","TEXT","","",""),("subtitle","TEXT","","",""),("image_url","TEXT","","",""),
 ("link_url","TEXT","","",""),("position","TEXT","","hero / side",""),
 ("product_id","INTEGER","FK → products","có thể rỗng","Sản phẩm hiện trên banner"),
 ("bg_color","TEXT","","",""),("sort_order","INTEGER","","",""),
 ("starts_at","TEXT","","",""),("ends_at","TEXT","","",""),("is_active","INTEGER","","0 / 1",""),
],core=False,rows="5")

# ---------------- Tương tác ----------------
t("reviews","cnt","Đánh giá","Chỉ khách có đơn \"Đã giao\" chứa sản phẩm mới được viết; admin duyệt trước khi hiện.",[
 ID,("product_id","INTEGER","FK → products","NOT NULL",""),
 ("customer_id","INTEGER","FK → customers","NOT NULL",""),
 ("order_id","INTEGER","FK → orders","NOT NULL","UQ (order_id, product_id)"),
 ("rating","INTEGER","","1 – 5","Số sao"),("content","TEXT","","",""),
 ("status","TEXT","","pending / approved / hidden",""),CA],rows="~30")
t("wishlists","cnt","Yêu thích","Sản phẩm khách thành viên đã lưu.",[
 ("customer_id","INTEGER","PK, FK → customers","",""),
 ("product_id","INTEGER","PK, FK → products","",""),CA],core=False,rows="tự sinh")
t("posts","cnt","Tin tức","Bài viết tin tức, mẹo hay (hỗ trợ SEO).",[
 ID,("title","TEXT","","",""),("slug","TEXT","UQ","",""),("summary","TEXT","","",""),
 ("content","TEXT","","",""),("cover_url","TEXT","","",""),("is_published","INTEGER","","0 / 1",""),
 ("published_at","TEXT","","",""),
],core=False,rows="5")
t("email_outbox","cnt","Hộp thư mô phỏng","Thay cho gửi email thật: mọi \"email\" xác nhận đơn, đổi trạng thái được lưu ở đây để xem trong admin.",[
 ID,("to_email","TEXT","","",""),("subject","TEXT","","",""),("body_html","TEXT","","",""),
 ("order_id","INTEGER","FK → orders","có thể rỗng",""),CA],core=False,rows="tự sinh")

# Quan hệ cho ERD: (A, card, B, nhãn)
REL = [
 ("users","||--o|","customers","là"),
 ("users","||--o{","sessions","đăng nhập"),
 ("customers","||--o{","addresses","có"),
 ("customers","||--o{","orders","đặt"),
 ("customers","||--o{","carts","sở hữu"),
 ("customers","||--o{","reviews","viết"),
 ("customers","||--o{","wishlists","lưu"),
 ("categories","||--o{","categories","cha của"),
 ("categories","||--o{","products","chứa"),
 ("brands","||--o{","products","sản xuất"),
 ("products","||--|{","product_variants","có SKU"),
 ("products","||--o{","product_images","có ảnh"),
 ("products","||--o{","product_specs","có thông số"),
 ("products","||--o{","reviews","được đánh giá"),
 ("products","||--o{","wishlists","được lưu"),
 ("products","||--o{","accessory_compat","tương thích"),
 ("product_variants","||--||","inventory","tồn kho"),
 ("product_variants","||--o{","inventory_transactions","biến động"),
 ("product_variants","||--o{","price_history","đổi giá"),
 ("product_variants","||--o{","cart_items","nằm trong"),
 ("product_variants","||--o{","order_items","được bán"),
 ("product_variants","||--o{","promotion_items","giá sốc"),
 ("carts","||--o{","cart_items","chứa"),
 ("orders","||--|{","order_items","gồm"),
 ("orders","||--o{","payments","thanh toán"),
 ("orders","||--o|","shipments","giao bởi"),
 ("orders","||--o{","order_status_history","lịch sử"),
 ("orders","||--o{","email_outbox","thông báo"),
 ("stores","||--o{","orders","nhận tại"),
 ("vouchers","||--o{","orders","áp dụng"),
 ("vouchers","||--o{","voucher_usages","ghi nhận"),
 ("promotions","||--o{","promotion_items","gồm"),
 ("products","||--o{","banners","quảng bá"),
]
