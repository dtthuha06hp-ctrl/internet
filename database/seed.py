"""Tạo cơ sở dữ liệu mới và nạp dữ liệu mẫu.

Chạy: python -m database.seed   (hoặc bấm lam_moi_du_lieu.bat)
Dữ liệu sinh ngẫu nhiên nhưng cố định (random.seed) để lần nào nạp cũng giống nhau.
"""
import os
import random
import re
import shutil
import sys
import unicodedata
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402
from core import db, security  # noqa: E402
from database import artwork  # noqa: E402
from database.seed_data import (PHONES, ACCESSORIES, BRANDS, ACC_CATEGORIES, STORES,  # noqa: E402
                                CUSTOMERS, VOUCHERS, POSTS)
from database.post_content import BODIES  # noqa: E402

IMG_DIR = os.path.join(config.UPLOAD_DIR, "products")
POST_DIR = os.path.join(config.UPLOAD_DIR, "posts")


def slugify(s):
    s = s.replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    s = s.replace("+", " plus ")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def code(s, n=4):
    return re.sub(r"[^A-Z0-9]", "", slugify(s).upper().replace("-", ""))[:n] or "X"


def ts(d):
    return d.isoformat(sep=" ", timespec="seconds")


def build(path=None, quiet=False):
    path = path or config.DB_PATH
    for p in (path, path + "-wal", path + "-shm"):
        if os.path.exists(p):
            os.remove(p)
    for d in (IMG_DIR, POST_DIR):
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d, exist_ok=True)

    rnd = random.Random(2026)
    conn = db.connect(path)
    with open(config.SCHEMA_PATH, encoding="utf-8") as f:
        conn.executescript(f.read())
    now = datetime.now().replace(microsecond=0)
    conn.execute("BEGIN")

    # ---------- Tài khoản ----------
    def add_user(email, phone, pw, name, role):
        cur = conn.execute("INSERT INTO users(email,phone,password_hash,full_name,role,created_at) VALUES(?,?,?,?,?,?)",
                           (email, phone, security.hash_password(pw), name, role, ts(now - timedelta(days=90))))
        return cur.lastrowid
    admin_id = add_user("admin@nhipmobile.vn", "0900000001", config.ADMIN_PASSWORD, "Quản trị viên", "admin")
    staff_id = add_user("nhanvien@nhipmobile.vn", "0900000002", config.STAFF_PASSWORD, "Nhân viên bán hàng", "staff")

    # ---------- Danh mục, hãng, cửa hàng ----------
    conn.execute("INSERT INTO categories(name,slug,kind,sort_order) VALUES('Điện thoại','dien-thoai','phone',1)")
    cur = conn.execute("INSERT INTO categories(name,slug,kind,sort_order) VALUES('Phụ kiện','phu-kien','accessory',2)")
    acc_root = cur.lastrowid
    cat_id = {"dien-thoai": 1}
    for i, (slug, name) in enumerate(ACC_CATEGORIES):
        cat_id[slug] = conn.execute("INSERT INTO categories(parent_id,name,slug,kind,sort_order) VALUES(?,?,?,?,?)",
                                    (acc_root, name, slug, "accessory", i + 1)).lastrowid
    brand_id = {}
    for i, (slug, name) in enumerate(BRANDS):
        brand_id[slug] = conn.execute("INSERT INTO brands(name,slug,sort_order) VALUES(?,?,?)", (name, slug, i + 1)).lastrowid
    for s in STORES:
        conn.execute("INSERT INTO stores(name,address,province,phone,open_hours) VALUES(?,?,?,?,'8:00 – 21:30')", s)

    # ---------- Điện thoại ----------
    spec_layout = [("Màn hình", "Kích thước màn hình"), ("Màn hình", "Công nghệ màn hình"), ("Màn hình", "Tần số quét"),
                   ("Hiệu năng", "Chip xử lý"), ("Camera", "Camera sau"), ("Camera", "Camera trước"),
                   ("Pin & sạc", "Dung lượng pin"), ("Pin & sạc", "Sạc nhanh"), ("Thiết kế", "Trọng lượng"),
                   ("Hệ điều hành", "Phiên bản")]
    variant_ids, phone_ids, all_variants = {}, {}, []
    for pi, p in enumerate(PHONES):
        slug = slugify(p["name"])
        created = now - timedelta(days=(5 + pi * 3) if p.get("new") else 60 + pi)
        pid = conn.execute("""INSERT INTO products(category_id,brand_id,name,slug,short_desc,description,needs,art,
                              is_featured,is_new,sold_count,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                           (1, brand_id[p["brand"]], p["name"], slug, p["desc"], p["desc"], p["needs"], p["art"],
                            p.get("featured", 0), p.get("new", 0), p["sold"], ts(created), ts(created))).lastrowid
        phone_ids[p["name"]] = pid
        ram_values = sorted({v[1] for v in p["variants"]})
        for k, ((g, n), val) in enumerate(zip(spec_layout, p["specs"])):
            conn.execute("INSERT INTO product_specs(product_id,spec_group,spec_name,spec_value,sort_order) VALUES(?,?,?,?,?)",
                         (pid, g, n, val, k))
        conn.execute("INSERT INTO product_specs(product_id,spec_group,spec_name,spec_value,sort_order) VALUES(?,?,?,?,?)",
                     (pid, "Hiệu năng", "RAM", " / ".join(ram_values), 4))
        storages = " / ".join(dict.fromkeys(v[0] for v in p["variants"]))
        conn.execute("INSERT INTO product_specs(product_id,spec_group,spec_name,spec_value,sort_order) VALUES(?,?,?,?,?)",
                     (pid, "Hiệu năng", "Bộ nhớ trong", storages, 4))
        conn.execute("INSERT INTO product_specs(product_id,spec_group,spec_name,spec_value,sort_order) VALUES(?,?,?,?,?)",
                     (pid, "Kết nối", "Mạng di động", "5G" if "5G" in p["name"] or p["variants"][0][2] > 7_000_000 else "4G", 11))
        # ảnh theo màu
        color_img = {}
        for ci, (cname, chex) in enumerate(p["colors"]):
            fname = f"{slug}-{ci + 1}.svg"
            with open(os.path.join(IMG_DIR, fname), "w", encoding="utf-8") as f:
                f.write(artwork.phone_svg(p["art"], chex, f"{p['name']} màu {cname}"))
            color_img[cname] = f"/uploads/products/{fname}"
        for (storage, ram, lp, sp) in p["variants"]:
            for ci, (cname, chex) in enumerate(p["colors"]):
                multi_ram = len({v[0] for v in p["variants"]}) < len(p["variants"])
                sku = f"{code(p['brand'], 2)}{pid:03d}-{storage}{'-' + ram if multi_ram else ''}-{code(cname, 3)}{ci}"
                vid = conn.execute("""INSERT INTO product_variants(product_id,sku,storage,ram,color_name,color_hex,list_price,sale_price)
                                      VALUES(?,?,?,?,?,?,?,?)""", (pid, sku, storage, ram, cname, chex, lp, sp)).lastrowid
                variant_ids[(p["name"], storage, ram, cname)] = vid
                all_variants.append((vid, pid, "phone", sp))
        for ci, (cname, chex) in enumerate(p["colors"]):
            vid = next(v for (n, s, r, c), v in variant_ids.items() if n == p["name"] and c == cname)
            conn.execute("INSERT INTO product_images(product_id,variant_id,url,alt_text,sort_order,is_main) VALUES(?,?,?,?,?,?)",
                         (pid, vid, color_img[cname], f"{p['name']} màu {cname}", ci, 1 if ci == 0 else 0))

    # ---------- Phụ kiện ----------
    acc_ids = {}
    for ai, (name, cat, brand, art, colors, lp, sp, specs, compat) in enumerate(ACCESSORIES):
        slug = slugify(name)
        created = now - timedelta(days=40 + ai)
        desc = f"{name}. Hàng chính hãng, bảo hành 12 tháng, 1 đổi 1 trong 30 ngày nếu lỗi nhà sản xuất."
        pid = conn.execute("""INSERT INTO products(category_id,brand_id,name,slug,short_desc,description,art,is_new,sold_count,created_at,updated_at)
                              VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                           (cat_id[cat], brand_id[brand], name, slug, specs[0][1] + " · " + specs[1][1], desc, art,
                            1 if ai % 9 == 0 else 0, rnd.randint(10, 120), ts(created), ts(created))).lastrowid
        acc_ids[name] = pid
        for k, (n, v) in enumerate(specs + [("Bảo hành", "12 tháng")]):
            conn.execute("INSERT INTO product_specs(product_id,spec_group,spec_name,spec_value,sort_order) VALUES(?,?,?,?,?)",
                         (pid, "Thông tin chung", n, v, k))
        for ci, (cname, chex) in enumerate(colors):
            fname = f"{slug}-{ci + 1}.svg"
            with open(os.path.join(IMG_DIR, fname), "w", encoding="utf-8") as f:
                f.write(artwork.accessory_svg(art, chex, f"{name} màu {cname}"))
            sku = f"PK-{code(brand, 3)}-{ai + 1:02d}-{code(cname, 3)}{ci}"
            vid = conn.execute("""INSERT INTO product_variants(product_id,sku,color_name,color_hex,list_price,sale_price)
                                  VALUES(?,?,?,?,?,?)""", (pid, sku, cname, chex, lp, sp)).lastrowid
            all_variants.append((vid, pid, "acc", sp))
            conn.execute("INSERT INTO product_images(product_id,variant_id,url,alt_text,sort_order,is_main) VALUES(?,?,?,?,?,?)",
                         (pid, vid, f"/uploads/products/{fname}", f"{name} màu {cname}", ci, 1 if ci == 0 else 0))
        # tương thích
        targets = set()
        for c in compat:
            if c == "*":
                targets |= set(phone_ids.values())
            elif c in brand_id:
                targets |= {phone_ids[p["name"]] for p in PHONES if p["brand"] == c}
            else:
                targets.add(phone_ids[c])
        for t in sorted(targets):
            conn.execute("INSERT INTO accessory_compat(accessory_id,phone_id) VALUES(?,?)", (pid, t))

    # ---------- Kho: nhập đầu kỳ ----------
    special = {("iPhone 17 Pro Max", "1TB", "12GB", "Bạc"): 0, ("Samsung Galaxy A56 5G", "256GB", "8GB", "Hồng đất"): 0,
               ("Samsung Galaxy Z Fold7", "512GB", "12GB", "Bạc"): 2, ("iPhone 17 Air", "512GB", "12GB", "Xanh da trời"): 3}
    vid_special = {variant_ids[k]: q for k, q in special.items()}
    import_day = ts(now - timedelta(days=75))
    for vid, pid, kind, price in all_variants:
        q = vid_special.get(vid)
        if q is None:
            q = rnd.randint(25, 60) if kind == "acc" else (rnd.randint(8, 25) if price > 20_000_000 else rnd.randint(15, 40))
        conn.execute("INSERT INTO inventory(variant_id,on_hand,reserved,low_threshold,updated_at) VALUES(?,?,0,?,?)",
                     (vid, 0, config.LOW_STOCK_DEFAULT, import_day))
        if q:
            stock_move(conn, vid, "import", q, "Nhập hàng đầu kỳ", None, admin_id, import_day)

    # ---------- Khách hàng ----------
    cust_ids = []
    for i, (title, name, phone, email, prov, ward, street) in enumerate(CUSTOMERS):
        uid = None
        if i == 0:
            uid = add_user(email, phone, "Khach@123", name, "customer")
        joined = now - timedelta(days=70 - i * 4)
        cid = conn.execute("""INSERT INTO customers(user_id,full_name,phone,email,title,consent_at,consent_version,created_at)
                              VALUES(?,?,?,?,?,?,?,?)""", (uid, name, phone, email, title, ts(joined), config.CONSENT_VERSION, ts(joined))).lastrowid
        cust_ids.append((cid, title, name, phone, email, prov, ward, street))
        if i < 6:
            conn.execute("""INSERT INTO addresses(customer_id,receiver_name,receiver_phone,province,ward,street,is_default)
                            VALUES(?,?,?,?,?,?,1)""", (cid, name, phone, prov, ward, street))

    # ---------- Mã giảm giá ----------
    voucher_id = {}
    for v in VOUCHERS:
        voucher_id[v[0]] = conn.execute("""INSERT INTO vouchers(code,description,type,value,max_discount,min_order,usage_limit,
                              per_customer_limit,starts_at,ends_at,is_active) VALUES(?,?,?,?,?,?,?,?,?,?,?)""", v).lastrowid

    # ---------- Đơn hàng mẫu (45 đơn trong 60 ngày) ----------
    phone_variants = [(vid, pid, sp) for vid, pid, k, sp in all_variants if k == "phone" and vid not in vid_special]
    acc_variants = [(vid, pid, sp) for vid, pid, k, sp in all_variants if k == "acc"]
    pay_methods = ["cod", "cod", "cod", "bank_qr", "bank_qr", "ewallet"]
    seq = {}
    sv_customers = set()
    orders_made = []
    for n in range(45):
        age_days = rnd.uniform(0.05, 8) if n < 16 else (rnd.uniform(8, 60) if n < 42 else rnd.uniform(0.01, 0.3))
        created = (now - timedelta(days=age_days)).replace(microsecond=0)
        if created.hour < 8:
            created = created.replace(hour=8 + created.hour)
        cust = rnd.choice(cust_ids if n % 4 else cust_ids[:3])
        if n == 44:
            cust = cust_ids[0]   # khách demo luôn có 1 đơn chờ xác nhận để thử hủy đơn
        items = []
        v = rnd.choice(phone_variants)
        items.append((v, 1))
        if rnd.random() < 0.6:
            items.append((rnd.choice(acc_variants), rnd.choice([1, 1, 2])))
        if rnd.random() < 0.12:
            items = [(rnd.choice(acc_variants), 1)]
        # trạng thái theo tuổi đơn
        if age_days > 12:
            status = rnd.choices(["completed", "cancelled", "refunded"], [86, 11, 3])[0]
        elif age_days > 4:
            status = rnd.choices(["completed", "delivered", "cancelled"], [30, 60, 10])[0]
        elif age_days > 1.5:
            status = rnd.choices(["delivered", "shipping", "preparing", "cancelled"], [35, 35, 20, 10])[0]
        else:
            status = rnd.choices(["pending", "confirmed", "preparing"], [55, 30, 15])[0]
        if n >= 42:
            status = "pending"
        method = rnd.choice(pay_methods)
        delivery = "store" if rnd.random() < 0.2 else "home"
        orders_made.append(make_order(conn, rnd, created, now, cust, items, status, method, delivery,
                                      voucher_id, sv_customers, seq, admin_id, staff_id))

    # ---------- Tổng hợp khách hàng, đã bán, đánh giá ----------
    conn.execute("""UPDATE customers SET
        order_count=(SELECT COUNT(*) FROM orders o WHERE o.customer_id=customers.id),
        total_spent=(SELECT COALESCE(SUM(total),0) FROM orders o WHERE o.customer_id=customers.id AND o.status='completed')""")
    for row in conn.execute("""SELECT v.product_id, SUM(oi.quantity) q FROM order_items oi JOIN orders o ON o.id=oi.order_id
                               JOIN product_variants v ON v.id=oi.variant_id WHERE o.status IN ('delivered','completed')
                               GROUP BY v.product_id""").fetchall():
        conn.execute("UPDATE products SET sold_count=sold_count+? WHERE id=?", (row["q"], row["product_id"]))

    review_texts = {
        5: ["Máy đẹp, chạy mượt, giao hàng nhanh. Rất hài lòng.", "Đóng gói cẩn thận, nhân viên gọi xác nhận nhiệt tình.",
            "Pin trâu, dùng cả ngày không lo hết.", "Giá rõ ràng đúng như trên web, không phát sinh gì thêm.",
            "Camera chụp đêm rất ổn, đáng tiền."],
        4: ["Máy tốt, chỉ hơi nóng khi chơi game lâu.", "Giao hơi chậm một ngày nhưng hàng chuẩn.",
            "Ổn trong tầm giá, màn hình đẹp."],
        3: ["Dùng tạm ổn, loa hơi nhỏ.", "Sạc nhanh nhưng máy hơi nặng."],
    }
    acc_texts = {
        5: ["Hàng chính hãng, đúng mô tả, dùng vừa khít máy.", "Giao nhanh, đóng gói kỹ, giá rõ ràng như trên web.",
            "Chất lượng tốt so với giá tiền, sẽ ủng hộ tiếp."],
        4: ["Dùng ổn, chỉ có hộp đựng hơi đơn giản.", "Tốt, nhưng giao chậm hơn dự kiến một ngày."],
        3: ["Tạm được, chưa thật sự nổi bật.", "Dùng được, màu thực tế hơi khác ảnh một chút."],
    }
    acc_pids = set(acc_ids.values())
    demo_done = [o for o in orders_made if o["customer_id"] == cust_ids[0][0] and o["status"] in ("delivered", "completed")]
    keep_open = max(demo_done, key=lambda o: o["created"])["id"] if demo_done else None   # khách demo còn 1 đơn chưa đánh giá
    for o in orders_made:
        if o["status"] not in ("delivered", "completed") or rnd.random() > 0.75 or o["id"] == keep_open:
            continue
        seen = set()
        for pid in o["product_ids"]:
            if pid in seen:
                continue
            seen.add(pid)
            r = rnd.choices([5, 4, 3], [62, 30, 8])[0]
            st = "approved" if rnd.random() < 0.9 else "pending"
            texts = acc_texts if pid in acc_pids else review_texts
            conn.execute("INSERT INTO reviews(product_id,customer_id,order_id,rating,content,status,created_at) VALUES(?,?,?,?,?,?,?)",
                         (pid, o["customer_id"], o["id"], r, rnd.choice(texts[r]), st, ts(o["created"] + timedelta(days=4))))
    conn.execute("""UPDATE products SET
        rating_count=(SELECT COUNT(*) FROM reviews r WHERE r.product_id=products.id AND r.status='approved'),
        rating_avg=COALESCE((SELECT ROUND(AVG(rating),1) FROM reviews r WHERE r.product_id=products.id AND r.status='approved'),0)""")

    # ---------- Yêu thích của tài khoản demo khach@ ----------
    for name in ("iPhone 17 Pro Max", "Samsung Galaxy S26 Ultra", "Xiaomi 15T Pro"):
        conn.execute("INSERT INTO wishlists(customer_id,product_id,created_at) VALUES(?,?,?)",
                     (cust_ids[0][0], phone_ids[name], ts(now - timedelta(days=3))))

    # ---------- Banner ----------
    banners = [
        ("iPhone 17 Pro Max", "Màu Cam vũ trụ mới. Một con số duy nhất, đã trừ mọi ưu đãi.", "hero", "#2F3FD1", phone_ids["iPhone 17 Pro Max"], "/dien-thoai/iphone-17-pro-max"),
        ("Galaxy S26 Ultra", "Đặt hôm nay, nhận máy trong 2 giờ nội thành (giả lập).", "hero", "#1E2A6E", phone_ids["Samsung Galaxy S26 Ultra"], "/dien-thoai/samsung-galaxy-s26-ultra"),
        ("Sinh viên giảm thêm 500.000₫", "Nhập mã SINHVIEN500 ở giỏ hàng cho đơn từ 5 triệu. Mỗi khách dùng 1 lần.", "hero", "#0F7A5C", phone_ids["Xiaomi Redmi Note 15 Pro"], "/dien-thoai?gia=5-10"),
        ("Trả góp 0% qua thẻ tín dụng", "Chỉ từ 1.290.000₫/tháng, không phí chuyển đổi (mô phỏng).", "side", "#FFF4E0", None, "/ho-tro/huong-dan-mua-hang"),
        ("Mua máy kèm phụ kiện giảm 20%", "Ốp lưng, cường lực, sạc nhanh chọn ngay ở trang sản phẩm.", "side", "#EEF0FD", None, "/phu-kien"),
    ]
    for i, (t, s, pos, bg, pid, link) in enumerate(banners):
        conn.execute("""INSERT INTO banners(title,subtitle,position,bg_color,product_id,link_url,sort_order,starts_at,ends_at)
                        VALUES(?,?,?,?,?,?,?,?,?)""", (t, s, pos, bg, pid, link, i, ts(now - timedelta(days=10)), "2027-01-31 23:59:59"))

    # ---------- Giá sốc ----------
    flash = [(("Samsung Galaxy S26 Ultra", "256GB", "12GB", "Đen titan"), 27_990_000),
             (("Samsung Galaxy A56 5G", "128GB", "8GB", "Xanh nhạt"), 8_490_000),
             (("Xiaomi Redmi Note 15 Pro", "128GB", "8GB", "Xanh lá"), 5_990_000),
             (("vivo Y19s", "128GB", "4GB", "Xám xanh"), 3_490_000),
             (("iPhone 17 Pro Max", "256GB", "12GB", "Cam vũ trụ"), 33_990_000)]
    day0 = now.replace(hour=0, minute=0, second=0)
    prom = conn.execute("INSERT INTO promotions(name,starts_at,ends_at) VALUES(?,?,?)",
                        ("Giá sốc hôm nay", ts(day0), ts(day0 + timedelta(days=1, seconds=-1)))).lastrowid
    for key, price in flash:
        conn.execute("INSERT INTO promotion_items(promotion_id,variant_id,promo_price,quota,sold) VALUES(?,?,?,?,?)",
                     (prom, variant_ids[key], price, 20, rnd.randint(6, 17)))

    # ---------- Tin tức ----------
    for i, (title, summary, bg, art, c) in enumerate(POSTS):
        slug = slugify(title)
        fname = f"{slug}.svg"
        with open(os.path.join(POST_DIR, fname), "w", encoding="utf-8") as f:
            f.write(artwork.post_cover_svg(bg, art, c))
        conn.execute("INSERT INTO posts(title,slug,summary,content,cover_url,published_at) VALUES(?,?,?,?,?,?)",
                     (title, slug, summary, BODIES[i].strip(), f"/uploads/posts/{fname}", ts(now - timedelta(days=2 + i * 3))))

    conn.execute("COMMIT")
    check(conn)
    counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("products", "product_variants", "customers", "orders", "reviews", "users")}
    conn.close()
    if not quiet:
        print("Đã tạo dữ liệu mẫu:", ", ".join(f"{k}={v}" for k, v in counts.items()))
    return counts


def stock_move(conn, vid, typ, qty, reason, order_id, user_id, when):
    """Mọi biến động kho đều qua đây và được ghi nhật ký."""
    if typ == "import":
        conn.execute("UPDATE inventory SET on_hand=on_hand+?, updated_at=? WHERE variant_id=?", (qty, when, vid))
        change = qty
    elif typ == "reserve":
        conn.execute("UPDATE inventory SET reserved=reserved+?, updated_at=? WHERE variant_id=?", (qty, when, vid))
        change = qty
    elif typ == "release":
        conn.execute("UPDATE inventory SET reserved=reserved-?, updated_at=? WHERE variant_id=?", (qty, when, vid))
        change = -qty
    elif typ == "sale":
        conn.execute("UPDATE inventory SET on_hand=on_hand-?, reserved=reserved-?, updated_at=? WHERE variant_id=?", (qty, qty, when, vid))
        change = -qty
    elif typ == "return":
        conn.execute("UPDATE inventory SET on_hand=on_hand+?, updated_at=? WHERE variant_id=?", (qty, when, vid))
        change = qty
    else:
        raise ValueError(typ)
    conn.execute("INSERT INTO inventory_transactions(variant_id,type,qty_change,reason,order_id,created_by,created_at) VALUES(?,?,?,?,?,?,?)",
                 (vid, typ, change, reason, order_id, user_id, when))


PATHS = {
    "pending": ["pending"],
    "confirmed": ["pending", "confirmed"],
    "preparing": ["pending", "confirmed", "preparing"],
    "shipping": ["pending", "confirmed", "preparing", "shipping"],
    "delivered": ["pending", "confirmed", "preparing", "shipping", "delivered"],
    "completed": ["pending", "confirmed", "preparing", "shipping", "delivered", "completed"],
    "refunded": ["pending", "confirmed", "preparing", "shipping", "delivered", "returning", "refunded"],
}
NOTES = {"pending": "Khách đặt hàng trên website", "confirmed": "Đã gọi xác nhận với khách",
         "preparing": "Đang đóng gói", "shipping": "Đã bàn giao cho đơn vị vận chuyển",
         "delivered": "Khách đã nhận hàng", "completed": "Hết thời hạn đổi trả 30 ngày",
         "returning": "Khách yêu cầu trả hàng", "refunded": "Đã nhận lại hàng và hoàn tiền",
         "cancelled": "Khách đổi ý, không mua nữa"}


def make_order(conn, rnd, created, now, cust, items, status, method, delivery, voucher_id, sv_customers, seq, admin_id, staff_id):
    cid, title, name, phone, email, prov, ward, street = cust
    day = created.strftime("%y%m%d")
    seq[day] = seq.get(day, 0) + 1
    order_code = f"NM{day}{seq[day]:04d}"
    lines = []
    for (vid, pid, price), qty in items:
        r = conn.execute("""SELECT p.name, v.sku, v.storage, v.color_name FROM product_variants v JOIN products p ON p.id=v.product_id
                            WHERE v.id=?""", (vid,)).fetchone()
        label = " · ".join(x for x in (r["storage"], r["color_name"]) if x)
        lines.append((vid, pid, r["name"], label, r["sku"], price, qty))
    subtotal = sum(l[5] * l[6] for l in lines)
    discount, vid_used = 0, None
    if subtotal >= 5_000_000 and cid not in sv_customers and rnd.random() < 0.25:
        discount, vid_used = 500_000, voucher_id["SINHVIEN500"]
        sv_customers.add(cid)
    ship = 0 if (delivery == "store" or subtotal >= config.FREE_SHIP_FROM) else config.SHIPPING_FEE
    total = subtotal - discount + ship
    store_id = rnd.randint(1, 3) if delivery == "store" else None
    addr = None if delivery == "store" else f"{street}, {ward}, {prov}"
    path = PATHS.get(status) or (["pending", "confirmed"][:rnd.randint(1, 2)] + ["cancelled"])
    final = path[-1]
    pay_status = "unpaid" if method == "cod" else "pending"
    times = [created]
    for _ in path[1:]:
        times.append(min(times[-1] + timedelta(hours=rnd.uniform(1, 30)), now - timedelta(minutes=5)))
    if final == "completed":
        times[-1] = max(times[-2], created + timedelta(days=12))
    if delivery == "store" and "shipping" in path:   # nhận tại cửa hàng: không qua vận chuyển
        i = path.index("shipping")
        path, times = path[:i] + path[i + 1:], times[:i] + times[i + 1:]
        final = path[-1]
    oid = conn.execute("""INSERT INTO orders(order_code,customer_id,status,receiver_name,receiver_phone,receiver_title,delivery_method,
            shipping_address,store_id,subtotal,discount_amount,shipping_fee,total,voucher_id,payment_method,payment_status,
            cancel_reason,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                       (order_code, cid, final, name, phone, title, delivery, addr, store_id, subtotal, discount, ship, total,
                        vid_used, method, pay_status, NOTES["cancelled"] if final == "cancelled" else None,
                        ts(created), ts(times[-1]))).lastrowid
    for vid, pid, pname, label, sku, price, qty in lines:
        conn.execute("""INSERT INTO order_items(order_id,variant_id,product_name,variant_label,sku,unit_price,quantity,line_total)
                        VALUES(?,?,?,?,?,?,?,?)""", (oid, vid, pname, label, sku, price, qty, price * qty))
        stock_move(conn, vid, "reserve", qty, "Giữ hàng cho đơn " + order_code, oid, None, ts(created))
    if vid_used:
        conn.execute("UPDATE vouchers SET used_count=used_count+1 WHERE id=?", (vid_used,))
        conn.execute("INSERT INTO voucher_usages(voucher_id,customer_id,order_id,used_at) VALUES(?,?,?,?)", (vid_used, cid, oid, ts(created)))
    pay_id = conn.execute("INSERT INTO payments(order_id,method,amount,status,created_at) VALUES(?,?,?,?,?)",
                          (oid, method, total, "pending", ts(created))).lastrowid
    prev = None
    for st, t in zip(path, times):
        by = None if st == "pending" else rnd.choice([admin_id, staff_id])
        conn.execute("INSERT INTO order_status_history(order_id,from_status,to_status,note,changed_by,changed_at) VALUES(?,?,?,?,?,?)",
                     (oid, prev, st, NOTES[st], by, ts(t)))
        prev = st
        if st == "confirmed" and method != "cod":
            conn.execute("UPDATE payments SET status='paid', paid_at=?, provider_txn_id=? WHERE id=?",
                         (ts(t), f"MOCK{oid:06d}", pay_id))
            pay_status = "paid"
        if st == "shipping":
            conn.execute("INSERT INTO shipments(order_id,carrier,tracking_code,shipped_at) VALUES(?,?,?,?)",
                         (oid, rnd.choice(["GHN", "GHTK", "Viettel Post"]), f"VD{rnd.randint(10**8, 10**9 - 1)}", ts(t)))
        if st == "delivered":
            conn.execute("UPDATE shipments SET delivered_at=? WHERE order_id=?", (ts(t), oid))
            for vid, *_rest in lines:
                qty = _rest[-1]
                stock_move(conn, vid, "sale", qty, "Xuất bán đơn " + order_code, oid, None, ts(t))
            if method == "cod":
                conn.execute("UPDATE payments SET status='paid', paid_at=? WHERE id=?", (ts(t), pay_id))
                pay_status = "paid"
        if st == "refunded":
            for vid, *_rest in lines:
                stock_move(conn, vid, "return", _rest[-1], "Nhận lại hàng đơn " + order_code, oid, admin_id, ts(t))
            conn.execute("UPDATE payments SET status='refunded' WHERE id=?", (pay_id,))
            pay_status = "refunded"
        if st == "cancelled":
            for vid, *_rest in lines:
                stock_move(conn, vid, "release", _rest[-1], "Hủy đơn " + order_code, oid, None, ts(t))
            conn.execute("UPDATE payments SET status='failed' WHERE id=?", (pay_id,))
            if vid_used:
                conn.execute("UPDATE vouchers SET used_count=used_count-1 WHERE id=?", (vid_used,))
                conn.execute("DELETE FROM voucher_usages WHERE order_id=?", (oid,))
    conn.execute("UPDATE orders SET payment_status=? WHERE id=?", (pay_status, oid))
    return {"id": oid, "status": final, "customer_id": cid, "created": created, "product_ids": [l[1] for l in lines]}


def check(conn):
    """Đối soát: tồn kho = tổng nhật ký; không có số âm."""
    bad = conn.execute("""SELECT i.variant_id FROM inventory i
        WHERE i.on_hand <> (SELECT COALESCE(SUM(CASE WHEN type IN ('import','return','adjust') THEN qty_change
                                                     WHEN type='sale' THEN qty_change ELSE 0 END),0)
                            FROM inventory_transactions t WHERE t.variant_id=i.variant_id)
           OR i.reserved <> (SELECT COALESCE(SUM(CASE WHEN type IN ('reserve','release') THEN qty_change
                                                      WHEN type='sale' THEN qty_change ELSE 0 END),0)
                             FROM inventory_transactions t WHERE t.variant_id=i.variant_id)""").fetchall()
    if bad:
        raise RuntimeError(f"Tồn kho lệch nhật ký ở {len(bad)} SKU")


if __name__ == "__main__":
    build()
