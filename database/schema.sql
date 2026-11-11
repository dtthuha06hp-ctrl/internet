-- =====================================================================
--  Cơ sở dữ liệu Nhịp Mobile (SQLite)
--  31 bảng: 21 bảng lõi theo Phần 6 tài liệu + 10 bảng bổ sung.
--  Tiền lưu số nguyên (đồng). Ngày giờ lưu dạng văn bản ISO 8601.
--  Xem bản trình bày: tai-lieu/co-so-du-lieu.html
-- =====================================================================
PRAGMA foreign_keys = ON;

-- ---------------- 1. Tài khoản & khách hàng ----------------
CREATE TABLE users (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  email          TEXT NOT NULL UNIQUE,
  phone          TEXT UNIQUE,
  password_hash  TEXT NOT NULL,
  full_name      TEXT NOT NULL,
  role           TEXT NOT NULL DEFAULT 'customer' CHECK (role IN ('customer','staff','admin')),
  status         TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','locked')),
  failed_logins  INTEGER NOT NULL DEFAULT 0 CHECK (failed_logins >= 0),
  locked_until   TEXT,
  created_at     TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE customers (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id         INTEGER UNIQUE REFERENCES users(id),
  full_name       TEXT NOT NULL,
  phone           TEXT NOT NULL UNIQUE CHECK (length(phone) = 10),
  email           TEXT,
  title           TEXT CHECK (title IN ('Anh','Chị')),
  total_spent     INTEGER NOT NULL DEFAULT 0 CHECK (total_spent >= 0),
  order_count     INTEGER NOT NULL DEFAULT 0 CHECK (order_count >= 0),
  consent_at      TEXT,
  consent_version TEXT,
  created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE addresses (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id    INTEGER NOT NULL REFERENCES customers(id),
  receiver_name  TEXT NOT NULL,
  receiver_phone TEXT NOT NULL,
  province       TEXT NOT NULL,
  ward           TEXT NOT NULL,
  street         TEXT NOT NULL,
  is_default     INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0,1))
);

CREATE TABLE sessions (
  token       TEXT PRIMARY KEY,
  user_id     INTEGER REFERENCES users(id),
  csrf_token  TEXT NOT NULL,
  expires_at  TEXT NOT NULL,
  created_at  TEXT NOT NULL
);

-- ---------------- 2. Sản phẩm ----------------
CREATE TABLE categories (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  parent_id   INTEGER REFERENCES categories(id),
  name        TEXT NOT NULL,
  slug        TEXT NOT NULL UNIQUE,
  kind        TEXT NOT NULL CHECK (kind IN ('phone','accessory')),
  sort_order  INTEGER NOT NULL DEFAULT 0,
  is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1))
);

CREATE TABLE brands (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  name        TEXT NOT NULL,
  slug        TEXT NOT NULL UNIQUE,
  logo_url    TEXT,
  sort_order  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE products (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  category_id   INTEGER NOT NULL REFERENCES categories(id),
  brand_id      INTEGER NOT NULL REFERENCES brands(id),
  name          TEXT NOT NULL,
  slug          TEXT NOT NULL UNIQUE,
  short_desc    TEXT,
  description   TEXT,
  needs         TEXT,                     -- cam,game,pin,slim
  art           TEXT,                     -- kiểu ảnh minh họa
  is_featured   INTEGER NOT NULL DEFAULT 0 CHECK (is_featured IN (0,1)),
  is_new        INTEGER NOT NULL DEFAULT 0 CHECK (is_new IN (0,1)),
  is_active     INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
  rating_avg    REAL NOT NULL DEFAULT 0 CHECK (rating_avg BETWEEN 0 AND 5),
  rating_count  INTEGER NOT NULL DEFAULT 0,
  sold_count    INTEGER NOT NULL DEFAULT 0,
  created_at    TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  updated_at    TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE product_specs (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id  INTEGER NOT NULL REFERENCES products(id),
  spec_group  TEXT NOT NULL,
  spec_name   TEXT NOT NULL,
  spec_value  TEXT NOT NULL,
  sort_order  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE product_variants (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id  INTEGER NOT NULL REFERENCES products(id),
  sku         TEXT NOT NULL UNIQUE,
  storage     TEXT,
  ram         TEXT,
  color_name  TEXT,
  color_hex   TEXT,
  list_price  INTEGER NOT NULL CHECK (list_price > 0),
  sale_price  INTEGER NOT NULL CHECK (sale_price > 0),
  is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
  CHECK (sale_price <= list_price)
);

CREATE TABLE product_images (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id  INTEGER NOT NULL REFERENCES products(id),
  variant_id  INTEGER REFERENCES product_variants(id),
  url         TEXT NOT NULL,
  alt_text    TEXT,
  sort_order  INTEGER NOT NULL DEFAULT 0,
  is_main     INTEGER NOT NULL DEFAULT 0 CHECK (is_main IN (0,1))
);

CREATE TABLE price_history (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  variant_id  INTEGER NOT NULL REFERENCES product_variants(id),
  old_price   INTEGER,
  new_price   INTEGER NOT NULL,
  changed_by  INTEGER REFERENCES users(id),
  changed_at  TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE accessory_compat (
  accessory_id  INTEGER NOT NULL REFERENCES products(id),
  phone_id      INTEGER NOT NULL REFERENCES products(id),
  PRIMARY KEY (accessory_id, phone_id)
);

-- ---------------- 3. Kho hàng ----------------
CREATE TABLE inventory (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  variant_id     INTEGER NOT NULL UNIQUE REFERENCES product_variants(id),
  on_hand        INTEGER NOT NULL DEFAULT 0 CHECK (on_hand >= 0),
  reserved       INTEGER NOT NULL DEFAULT 0 CHECK (reserved >= 0),
  low_threshold  INTEGER NOT NULL DEFAULT 5,
  updated_at     TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  CHECK (reserved <= on_hand)
);

CREATE TABLE stores (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  name        TEXT NOT NULL,
  address     TEXT NOT NULL,
  province    TEXT NOT NULL,
  phone       TEXT,
  open_hours  TEXT,
  is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1))
);

-- ---------------- 5. Marketing (đặt trước vì orders tham chiếu) ----------------
CREATE TABLE vouchers (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  code                TEXT NOT NULL UNIQUE,
  description         TEXT,
  type                TEXT NOT NULL CHECK (type IN ('fixed','percent')),
  value               INTEGER NOT NULL CHECK (value > 0),
  max_discount        INTEGER,
  min_order           INTEGER NOT NULL DEFAULT 0 CHECK (min_order >= 0),
  usage_limit         INTEGER,
  used_count          INTEGER NOT NULL DEFAULT 0 CHECK (used_count >= 0),
  per_customer_limit  INTEGER NOT NULL DEFAULT 1,
  starts_at           TEXT,
  ends_at             TEXT,
  is_active           INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1))
);

-- ---------------- 4. Giỏ hàng & đơn hàng ----------------
CREATE TABLE carts (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id    INTEGER REFERENCES customers(id),
  session_token  TEXT,
  voucher_code   TEXT,
  status         TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','ordered','merged')),
  updated_at     TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE cart_items (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  cart_id     INTEGER NOT NULL REFERENCES carts(id),
  variant_id  INTEGER NOT NULL REFERENCES product_variants(id),
  quantity    INTEGER NOT NULL CHECK (quantity BETWEEN 1 AND 3),
  added_at    TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  UNIQUE (cart_id, variant_id)
);

CREATE TABLE orders (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  order_code        TEXT NOT NULL UNIQUE,
  customer_id       INTEGER NOT NULL REFERENCES customers(id),
  status            TEXT NOT NULL DEFAULT 'pending' CHECK (status IN
                    ('pending','confirmed','preparing','shipping','delivery_failed','delivered',
                     'completed','returning','refunded','cancelled')),
  receiver_name     TEXT NOT NULL,
  receiver_phone    TEXT NOT NULL,
  receiver_title    TEXT,
  delivery_method   TEXT NOT NULL CHECK (delivery_method IN ('home','store')),
  shipping_address  TEXT,
  store_id          INTEGER REFERENCES stores(id),
  subtotal          INTEGER NOT NULL CHECK (subtotal >= 0),
  discount_amount   INTEGER NOT NULL DEFAULT 0 CHECK (discount_amount >= 0),
  shipping_fee      INTEGER NOT NULL DEFAULT 0 CHECK (shipping_fee >= 0),
  total             INTEGER NOT NULL CHECK (total >= 0),
  voucher_id        INTEGER REFERENCES vouchers(id),
  payment_method    TEXT NOT NULL CHECK (payment_method IN ('cod','bank_qr','ewallet')),
  payment_status    TEXT NOT NULL DEFAULT 'unpaid' CHECK (payment_status IN ('unpaid','pending','paid','refunded')),
  note              TEXT,
  internal_note     TEXT,
  cancel_reason     TEXT,
  idempotency_key   TEXT UNIQUE,
  created_at        TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  updated_at        TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  CHECK (total = subtotal - discount_amount + shipping_fee),
  CHECK (status <> 'cancelled' OR cancel_reason IS NOT NULL)
);

CREATE TABLE order_items (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id       INTEGER NOT NULL REFERENCES orders(id),
  variant_id     INTEGER NOT NULL REFERENCES product_variants(id),
  product_name   TEXT NOT NULL,
  variant_label  TEXT,
  sku            TEXT NOT NULL,
  unit_price     INTEGER NOT NULL CHECK (unit_price > 0),
  quantity       INTEGER NOT NULL CHECK (quantity BETWEEN 1 AND 3),
  line_total     INTEGER NOT NULL,
  CHECK (line_total = unit_price * quantity)
);

CREATE TABLE order_status_history (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id     INTEGER NOT NULL REFERENCES orders(id),
  from_status  TEXT,
  to_status    TEXT NOT NULL,
  note         TEXT,
  changed_by   INTEGER REFERENCES users(id),
  changed_at   TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE payments (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id         INTEGER NOT NULL REFERENCES orders(id),
  method           TEXT NOT NULL CHECK (method IN ('cod','bank_qr','ewallet')),
  amount           INTEGER NOT NULL CHECK (amount > 0),
  status           TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','paid','failed','refunded')),
  provider_txn_id  TEXT UNIQUE,
  paid_at          TEXT,
  created_at       TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE shipments (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id       INTEGER NOT NULL UNIQUE REFERENCES orders(id),
  carrier        TEXT,
  tracking_code  TEXT,
  shipped_at     TEXT,
  delivered_at   TEXT
);

CREATE TABLE inventory_transactions (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  variant_id  INTEGER NOT NULL REFERENCES product_variants(id),
  type        TEXT NOT NULL CHECK (type IN ('import','reserve','release','sale','return','adjust')),
  qty_change  INTEGER NOT NULL CHECK (qty_change <> 0),
  reason      TEXT,
  order_id    INTEGER REFERENCES orders(id),
  created_by  INTEGER REFERENCES users(id),
  created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  CHECK (type <> 'adjust' OR reason IS NOT NULL)
);

CREATE TABLE voucher_usages (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  voucher_id   INTEGER NOT NULL REFERENCES vouchers(id),
  customer_id  INTEGER NOT NULL REFERENCES customers(id),
  order_id     INTEGER NOT NULL REFERENCES orders(id),
  used_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE promotions (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  name        TEXT NOT NULL,
  starts_at   TEXT NOT NULL,
  ends_at     TEXT NOT NULL,
  is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1))
);

CREATE TABLE promotion_items (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  promotion_id  INTEGER NOT NULL REFERENCES promotions(id),
  variant_id    INTEGER NOT NULL REFERENCES product_variants(id),
  promo_price   INTEGER NOT NULL CHECK (promo_price > 0),
  quota         INTEGER NOT NULL CHECK (quota > 0),
  sold          INTEGER NOT NULL DEFAULT 0,
  CHECK (sold BETWEEN 0 AND quota)
);

CREATE TABLE banners (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  title       TEXT NOT NULL,
  subtitle    TEXT,
  image_url   TEXT,
  link_url    TEXT,
  position    TEXT NOT NULL CHECK (position IN ('hero','side')),
  bg_color    TEXT,
  product_id  INTEGER REFERENCES products(id),
  sort_order  INTEGER NOT NULL DEFAULT 0,
  starts_at   TEXT,
  ends_at     TEXT,
  is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1))
);

-- ---------------- 6. Tương tác & nội dung ----------------
CREATE TABLE reviews (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id   INTEGER NOT NULL REFERENCES products(id),
  customer_id  INTEGER NOT NULL REFERENCES customers(id),
  order_id     INTEGER NOT NULL REFERENCES orders(id),
  rating       INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
  content      TEXT,
  status       TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','hidden')),
  created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  UNIQUE (order_id, product_id)
);

CREATE TABLE wishlists (
  customer_id  INTEGER NOT NULL REFERENCES customers(id),
  product_id   INTEGER NOT NULL REFERENCES products(id),
  created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  PRIMARY KEY (customer_id, product_id)
);

CREATE TABLE posts (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  title         TEXT NOT NULL,
  slug          TEXT NOT NULL UNIQUE,
  summary       TEXT,
  content       TEXT,
  cover_url     TEXT,
  is_published  INTEGER NOT NULL DEFAULT 1 CHECK (is_published IN (0,1)),
  published_at  TEXT
);

CREATE TABLE email_outbox (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  to_email    TEXT NOT NULL,
  subject     TEXT NOT NULL,
  body_html   TEXT NOT NULL,
  order_id    INTEGER REFERENCES orders(id),
  created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- ---------------- Chỉ mục tăng tốc tìm kiếm ----------------
CREATE INDEX idx_products_cat     ON products(category_id, is_active);
CREATE INDEX idx_products_brand   ON products(brand_id);
CREATE INDEX idx_variants_product ON product_variants(product_id);
CREATE INDEX idx_images_product   ON product_images(product_id);
CREATE INDEX idx_specs_product    ON product_specs(product_id);
CREATE INDEX idx_orders_status    ON orders(status, created_at);
CREATE INDEX idx_orders_customer  ON orders(customer_id);
CREATE INDEX idx_items_order      ON order_items(order_id);
CREATE INDEX idx_history_order    ON order_status_history(order_id);
CREATE INDEX idx_invtx_variant    ON inventory_transactions(variant_id);
CREATE INDEX idx_reviews_product  ON reviews(product_id, status);
CREATE INDEX idx_carts_session    ON carts(session_token, status);
