"""Nội dung đầy đủ của 5 bài tin tức mẫu (cùng thứ tự với POSTS trong seed_data.py).

Viết bằng HTML đơn giản: <h2>, <p>, <ul>, <ol>, <table>, <a>. Các liên kết tới /dien-thoai/... và
/phu-kien/... sẽ tự hiện thành khối "Sản phẩm nhắc tới trong bài" ở cuối bài.
"""

BODIES = [
# 1. iPhone 17 vs 17 Air
"""
<p>Năm nay Apple có hai lựa chọn ở cùng tầm giá khiến nhiều người phân vân: <a href="/dien-thoai/iphone-17">iPhone 17</a> bản tiêu chuẩn và <a href="/dien-thoai/iphone-17-air">iPhone 17 Air</a> siêu mỏng. Bài này không chấm điểm máy nào "tốt hơn", mà giúp bạn biết máy nào hợp với cách mình dùng.</p>

<h2>Khác biệt chính trong một bảng</h2>
<table>
<tr><th></th><th>iPhone 17</th><th>iPhone 17 Air</th></tr>
<tr><td>Chip</td><td>Apple A19</td><td>Apple A19 Pro</td></tr>
<tr><td>Camera sau</td><td>2 camera 48MP (chính + góc rộng)</td><td>1 camera 48MP</td></tr>
<tr><td>Pin</td><td>3.692 mAh</td><td>3.149 mAh</td></tr>
<tr><td>Sạc nhanh có dây</td><td>40W</td><td>20W</td></tr>
<tr><td>Trọng lượng</td><td>177 g</td><td>165 g</td></tr>
<tr><td>Giá tại Nhịp Mobile</td><td>từ 24.490.000₫</td><td>từ 29.990.000₫</td></tr>
</table>

<h2>Chọn iPhone 17 nếu bạn…</h2>
<ul>
<li><b>Dùng máy cả ngày ngoài đường.</b> Pin lớn hơn và sạc 40W giúp bạn ít phải lo hết pin giữa buổi.</li>
<li><b>Hay chụp phong cảnh, chụp nhóm.</b> Camera góc rộng thứ hai lấy được nhiều khung cảnh hơn trong một bức ảnh.</li>
<li><b>Muốn tiết kiệm.</b> Rẻ hơn khoảng 5,5 triệu, đủ để mua thêm <a href="/phu-kien/op-lung-silicon-magsafe-iphone-17">ốp lưng MagSafe</a> và <a href="/phu-kien/cu-sac-nhanh-usb-c-35w-hai-cong">củ sạc 35W</a>.</li>
</ul>

<h2>Chọn iPhone 17 Air nếu bạn…</h2>
<ul>
<li><b>Ưu tiên cảm giác cầm.</b> Máy rất mỏng và nhẹ, bỏ túi áo sơ mi không bị xệ.</li>
<li><b>Chủ yếu chụp chân dung, đồ ăn, ảnh mạng xã hội.</b> Một camera 48MP vẫn cho ảnh đẹp ở điều kiện đủ sáng.</li>
<li><b>Có sẵn sạc dự phòng.</b> Kết hợp với <a href="/phu-kien/sac-du-phong-magsafe-10-000mah">sạc dự phòng MagSafe</a> sẽ bù được phần pin nhỏ hơn.</li>
</ul>

<h2>Lời khuyên của chúng tôi</h2>
<p>Với học sinh, sinh viên và người dùng phổ thông, iPhone 17 là lựa chọn cân bằng hơn: pin tốt hơn, camera linh hoạt hơn và giá dễ chịu hơn. iPhone 17 Air dành cho người coi trọng thiết kế và đã quen mang theo sạc dự phòng.</p>
<p>Bạn có thể đặt hai máy cạnh nhau trong trang <a href="/so-sanh">So sánh</a> để xem đủ thông số, hoặc thử công cụ <a href="/chon-may">Chọn máy theo nhu cầu</a>.</p>
""",

# 2. Mẹo pin
"""
<p>Pin lithium-ion trong điện thoại sẽ chai dần theo thời gian, đó là điều không tránh được. Tin tốt là cách bạn sạc và sử dụng hằng ngày có thể quyết định pin còn khỏe sau 2 năm hay phải thay sớm. Dưới đây là 5 thói quen đơn giản nhất.</p>

<h2>1. Giữ pin trong khoảng 20% – 80%</h2>
<p>Pin "mệt" nhất khi bị xả cạn về 0% hoặc giữ ở 100% trong nhiều giờ. Phần lớn điện thoại mới đã có tùy chọn <b>giới hạn sạc ở 80%</b> hoặc <b>sạc tối ưu</b> (học thói quen của bạn để sạc đầy ngay trước giờ thức dậy). Hãy bật nó trong mục Cài đặt → Pin.</p>

<h2>2. Tránh nhiệt độ cao</h2>
<p>Nhiệt là kẻ thù số một của pin. Đừng để máy trên táp-lô ô tô giữa trưa, đừng vừa sạc vừa chơi game nặng, và tháo ốp dày nếu thấy máy nóng lên khi sạc. Nếu máy nóng bất thường, hãy dừng sạc và để máy nghỉ.</p>

<h2>3. Dùng củ sạc và cáp đạt chuẩn</h2>
<p>Sạc nhanh không làm hỏng pin nếu củ sạc và điện thoại "nói chuyện" được với nhau qua chuẩn USB Power Delivery (PD). Cái đáng lo là sạc trôi nổi không rõ nguồn gốc, thiếu mạch bảo vệ. Một <a href="/phu-kien/cap-usb-c-to-usb-c-boc-du-1m-60w">cáp USB-C bọc dù 60W</a> và một củ sạc chính hãng là khoản đầu tư rẻ hơn nhiều so với thay pin.</p>

<h2>4. Giảm những thứ "ăn pin ngầm"</h2>
<ul>
<li>Hạ độ sáng màn hình hoặc bật độ sáng tự động.</li>
<li>Tắt định vị chạy nền cho những ứng dụng không cần.</li>
<li>Dùng chế độ tối nếu máy có màn hình OLED.</li>
<li>Tắt làm mới ứng dụng trong nền với mạng xã hội ít dùng.</li>
</ul>

<h2>5. Cất máy đúng cách khi không dùng lâu</h2>
<p>Nếu bạn cất một chiếc máy cũ trong vài tháng, hãy để pin khoảng 50% rồi tắt nguồn. Cất ở 0% có thể khiến pin xả sâu và không sạc lại được.</p>

<h2>Khi nào nên thay pin?</h2>
<p>Khi dung lượng tối đa (xem trong Cài đặt → Pin) xuống dưới khoảng 80%, máy tự tắt khi còn 10–20%, hoặc pin phồng làm hở màn hình. Pin phồng cần mang đi kiểm tra ngay, không tiếp tục sạc. Các cửa hàng Nhịp Mobile kiểm tra pin miễn phí, xem địa chỉ ở trang <a href="/ho-tro/cua-hang">Hệ thống cửa hàng</a>.</p>
""",

# 3. Củ sạc bao nhiêu W
"""
<p>Hộp điện thoại ngày nay thường không kèm củ sạc, và trên kệ có đủ loại 20W, 25W, 45W, 65W. Mua củ to nhất có tốt nhất không? Câu trả lời ngắn: <b>điện thoại chỉ nhận đúng công suất nó hỗ trợ</b>, phần dư không làm sạc nhanh hơn, nhưng cũng không gây hại.</p>

<h2>Hiểu hai chuẩn quan trọng: PD và PPS</h2>
<ul>
<li><b>USB Power Delivery (PD)</b>: chuẩn sạc nhanh qua cổng USB-C, iPhone và phần lớn điện thoại Android đều dùng.</li>
<li><b>PPS</b> (một phần mở rộng của PD): điện áp được điều chỉnh liên tục theo nhiệt độ và mức pin. Dòng Samsung Galaxy cần củ sạc có PPS mới đạt mức "Sạc siêu nhanh".</li>
</ul>
<p>Một số hãng như Xiaomi, OPPO, vivo có chuẩn sạc riêng (67W, 80W, 90W, 100W). Muốn đạt đúng con số quảng cáo, bạn cần dùng củ sạc và cáp đi kèm của hãng. Dùng củ PD thông thường máy vẫn sạc nhanh, chỉ ở mức thấp hơn.</p>

<h2>Bảng chọn nhanh</h2>
<table>
<tr><th>Bạn dùng</th><th>Củ sạc nên chọn</th></tr>
<tr><td>iPhone 16, 16e, 17 Air</td><td>20W PD trở lên</td></tr>
<tr><td>iPhone 17, 17 Pro, 17 Pro Max</td><td>Từ 35W PD để tận dụng sạc 40W</td></tr>
<tr><td>Samsung Galaxy A, S (25W)</td><td><a href="/phu-kien/cu-sac-nhanh-25w-samsung-chinh-hang">Củ 25W có PPS</a></td></tr>
<tr><td>Samsung Galaxy A56, A36, S26 Ultra (45W)</td><td>Củ 45W có PPS</td></tr>
<tr><td>Điện thoại + máy tính bảng / laptop</td><td><a href="/phu-kien/cu-sac-gan-65w-ba-cong">Củ GaN 65W nhiều cổng</a></td></tr>
</table>

<h2>Đừng quên sợi cáp</h2>
<p>Cáp quyết định trần công suất. Cáp USB-C thông thường chịu được 60W; muốn trên 60W cần cáp có chip E-marker ghi rõ 100W như <a href="/phu-kien/cap-usb-c-to-usb-c-2m-100w">cáp USB-C 2m 100W</a>. Cáp USB-A sang USB-C chỉ dùng được với củ sạc cổng USB-A, thường dưới 18W.</p>

<h2>GaN là gì, có đáng tiền không?</h2>
<p>GaN (gallium nitride) là vật liệu bán dẫn giúp củ sạc nhỏ và mát hơn ở cùng công suất. Nếu bạn hay mang sạc đi học, đi làm, một củ GaN nhiều cổng thay được 2–3 củ sạc riêng lẻ.</p>
<p>Ở trang chi tiết mỗi điện thoại, mục <b>Phụ kiện mua kèm</b> đã lọc sẵn những củ sạc phù hợp với máy đó.</p>
""",

# 4. Dưới 5 triệu
"""
<p>Với ngân sách dưới 5 triệu đồng, bạn không thể có mọi thứ. Nhưng nếu biết ưu tiên đúng, đặc biệt là <b>pin</b>, <b>độ bền</b> và <b>màn hình</b>, bạn vẫn có một chiếc máy dùng tốt 2–3 năm cho việc học. Đây là bốn lựa chọn đang có tại Nhịp Mobile.</p>

<h2>1. OPPO A5i: pin 6.000 mAh, giá thấp nhất</h2>
<p><a href="/dien-thoai/oppo-a5i">OPPO A5i</a> (từ 2.990.000₫) là lựa chọn an toàn cho người lần đầu dùng smartphone hoặc cần máy phụ. Pin 6.000 mAh dư sức dùng hai ngày với nhu cầu nhắn tin, học online, xem video. Điểm trừ là sạc 15W khá chậm, nên sạc qua đêm.</p>

<h2>2. Xiaomi Redmi 15C: camera 50MP, sạc 33W</h2>
<p><a href="/dien-thoai/xiaomi-redmi-15c">Redmi 15C</a> (từ 3.190.000₫) nhỉnh hơn ở camera chính 50MP và sạc 33W, nhanh gấp đôi A5i. Hợp với bạn hay chụp tài liệu, bảng viết trên lớp.</p>

<h2>3. vivo Y29s: thiết kế đẹp, loa to</h2>
<p><a href="/dien-thoai/vivo-y29s">vivo Y29s</a> (từ 4.490.000₫) có ngoại hình trẻ trung, pin 5.500 mAh. Phù hợp với người dùng thích nghe nhạc, xem phim ngoài loa.</p>

<h2>4. Samsung Galaxy A17: cập nhật phần mềm lâu</h2>
<p><a href="/dien-thoai/samsung-galaxy-a17">Galaxy A17</a> (từ 4.990.000₫) chạm sát mức 5 triệu nhưng bù lại có ba camera, sạc 25W và chính sách cập nhật phần mềm dài của Samsung. Nếu bạn định dùng máy trên 3 năm, đây là lựa chọn đáng cân nhắc nhất.</p>

<h2>Tóm tắt</h2>
<table>
<tr><th>Ưu tiên</th><th>Nên chọn</th></tr>
<tr><td>Giá thấp nhất, pin trâu</td><td>OPPO A5i</td></tr>
<tr><td>Sạc nhanh, chụp tài liệu</td><td>Xiaomi Redmi 15C</td></tr>
<tr><td>Giải trí, thiết kế</td><td>vivo Y29s</td></tr>
<tr><td>Dùng lâu dài</td><td>Samsung Galaxy A17</td></tr>
</table>
<p>Nhớ mua kèm kính cường lực và ốp lưng ngay từ đầu, vì thay màn hình máy giá rẻ đôi khi tốn tới một nửa giá máy. Sinh viên nhập mã <b>SINHVIEN500</b> để được giảm 500.000₫ cho đơn từ 5 triệu.</p>
""",

# 5. Kính chống nhìn trộm
"""
<p>Kính cường lực chống nhìn trộm (privacy) đang rất được ưa chuộng vì giúp người bên cạnh không đọc được tin nhắn của bạn trên xe buýt hay quán cà phê. Câu hỏi chúng tôi nhận nhiều nhất: <b>loại kính này có hại mắt không?</b></p>

<h2>Kính chống nhìn trộm hoạt động thế nào?</h2>
<p>Bên trong kính có một lớp vi rèm (micro-louver) giống những thanh mành rất nhỏ. Nhìn thẳng thì ánh sáng đi qua bình thường; nhìn nghiêng quá khoảng 30° thì các "thanh mành" chặn ánh sáng nên màn hình tối đen.</p>

<h2>Có hại mắt không?</h2>
<p>Kính không phát ra tia hay hóa chất nào nên <b>không trực tiếp gây hại</b>. Tuy nhiên, vì chặn bớt ánh sáng, màn hình sẽ tối hơn khoảng 20–40%. Nhiều người phản xạ bằng cách tăng độ sáng hoặc nheo mắt, nhìn lâu sẽ mỏi mắt hơn. Cách khắc phục:</p>
<ul>
<li>Tăng độ sáng màn hình lên một nấc thay vì nheo mắt.</li>
<li>Giữ máy ngay trước mặt, không cầm lệch.</li>
<li>Áp dụng quy tắc 20-20-20: cứ 20 phút, nhìn xa 6 mét (20 feet) trong 20 giây.</li>
</ul>

<h2>Ai nên và không nên dùng?</h2>
<table>
<tr><th>Nên dùng</th><th>Cân nhắc</th></tr>
<tr><td>Hay dùng điện thoại nơi đông người</td><td>Hay chia sẻ màn hình cho bạn bè xem cùng</td></tr>
<tr><td>Làm việc với thông tin nhạy cảm (ngân hàng, công việc)</td><td>Thường chụp ảnh, chỉnh màu (màu sắc có thể lệch nhẹ)</td></tr>
<tr><td>Muốn kính dày, chống va đập tốt</td><td>Máy có màn hình độ sáng thấp</td></tr>
</table>

<h2>Chọn kính thế nào cho chuẩn?</h2>
<p>Hãy chọn kính đúng model máy để không bị hở viền hay che cảm biến. Ví dụ <a href="/phu-kien/kinh-cuong-luc-chong-nhin-trom-iphone-17-pro-max">kính chống nhìn trộm cho iPhone 17 Pro Max</a>. Nếu không cần tính năng riêng tư, kính trong suốt full màn như <a href="/phu-kien/kinh-cuong-luc-galaxy-s26-ultra">kính cường lực Galaxy S26 Ultra</a> cho màu sắc trung thực hơn.</p>
<p>Mua kính tại cửa hàng Nhịp Mobile được dán miễn phí. Mua online, bạn có thể ghé bất kỳ cửa hàng nào để được dán lại miễn phí trong 7 ngày.</p>
""",
]
