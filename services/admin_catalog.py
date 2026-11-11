"""Quản lý sản phẩm, phiên bản, ảnh (phía quản trị)."""
import os
import re
import secrets
import unicodedata
from datetime import datetime

import config
from core import db
from services import inventory

NEEDS = [("cam", "Chụp ảnh đẹp"), ("game", "Chơi game"), ("pin", "Pin trâu"), ("slim", "Mỏng nhẹ")]


class CatalogError(Exception):
    def __init__(self, message, field=None):
        super().__init__(message)
        self.field = field or {}


def now():
    return datetime.now().isoformat(sep=" ", timespec="seconds")


def slugify(s):
    s = (s or "").replace("đ", "d").replace("Đ", "D").replace("+", " plus ")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def money(v):
    v = re.sub(r"[^\d]", "", str(v or ""))
    return int(v) if v else 0


def product_list(conn, q="", cat="", status="", limit=30, offset=0):
    sql = """ FROM products p JOIN categories c ON c.id=p.category_id JOIN brands b ON b.id=p.brand_id WHERE 1=1"""
    args = []
    if q:
        sql += " AND (p.name LIKE ? OR EXISTS (SELECT 1 FROM product_variants v WHERE v.product_id=p.id AND v.sku LIKE ?))"
        args += [f"%{q}%", f"%{q}%"]
    if cat == "phone":
        sql += " AND c.kind='phone'"
    elif cat == "accessory":
        sql += " AND c.kind='accessory'"
    if status == "an":
        sql += " AND p.is_active=0"
    elif status == "hien":
        sql += " AND p.is_active=1"
    total = db.scalar(conn, "SELECT COUNT(*)" + sql, args)
    rows = [dict(r) for r in db.all(conn, """SELECT p.*, c.name cat_name, c.kind, b.name brand,
        (SELECT COUNT(*) FROM product_variants v WHERE v.product_id=p.id) n_var,
        (SELECT MIN(sale_price) FROM product_variants v WHERE v.product_id=p.id AND v.is_active=1) min_price,
        (SELECT MAX(sale_price) FROM product_variants v WHERE v.product_id=p.id AND v.is_active=1) max_price,
        (SELECT COALESCE(SUM(i.on_hand-i.reserved),0) FROM product_variants v JOIN inventory i ON i.variant_id=v.id WHERE v.product_id=p.id) stock,
        (SELECT url FROM product_images im WHERE im.product_id=p.id ORDER BY im.is_main DESC, im.sort_order LIMIT 1) image"""
                                    + sql + " ORDER BY p.is_active DESC, c.kind DESC, p.name LIMIT ? OFFSET ?", args + [limit, offset])]
    return rows, total


def parse_specs(text):
    out = []
    for i, line in enumerate((text or "").splitlines()):
        parts = [p.strip() for p in line.split("|")]
        if len(parts) == 3 and all(parts):
            out.append((parts[0], parts[1], parts[2], i))
        elif line.strip():
            raise CatalogError(f"Dòng thông số số {i + 1} chưa đúng dạng \"Nhóm | Tên | Giá trị\": {line.strip()}",
                               {"specs": "Sai định dạng"})
    return out


def specs_text(conn, pid):
    return "\n".join(f"{r['spec_group']} | {r['spec_name']} | {r['spec_value']}"
                     for r in db.all(conn, "SELECT * FROM product_specs WHERE product_id=? ORDER BY sort_order, id", (pid,)))


def save_product(conn, form, form_list, pid=None):
    f = {k: (form.get(k) or "").strip() for k in ("name", "category_id", "brand_id", "short_desc", "description", "specs")}
    err = {}
    if len(f["name"]) < 2:
        err["name"] = "Vui lòng nhập tên sản phẩm."
    cat = db.one(conn, "SELECT * FROM categories WHERE id=?", (int(f["category_id"]) if f["category_id"].isdigit() else 0,))
    if not cat or (cat["kind"] == "accessory" and cat["parent_id"] is None):
        err["category_id"] = "Vui lòng chọn danh mục (với phụ kiện, chọn loại cụ thể)."
    if not f["brand_id"].isdigit() or not db.scalar(conn, "SELECT 1 FROM brands WHERE id=?", (int(f["brand_id"]),)):
        err["brand_id"] = "Vui lòng chọn hãng."
    specs = []
    try:
        specs = parse_specs(f["specs"])
    except CatalogError as e:
        err.update(e.field)
        err["specs"] = str(e)
    if err:
        raise CatalogError(next(iter(err.values())), err)
    needs = ",".join(v for v in form_list.get("needs", []) if v in dict(NEEDS))
    flags = {k: 1 if form.get(k) == "1" else 0 for k in ("is_new", "is_featured", "is_active")}
    slug = slugify(f["name"])
    base, n = slug, 2
    while db.scalar(conn, "SELECT 1 FROM products WHERE slug=? AND id<>?", (slug, pid or 0)):
        slug, n = f"{base}-{n}", n + 1
    t = now()
    with db.transaction(conn):
        if pid:
            conn.execute("""UPDATE products SET category_id=?, brand_id=?, name=?, slug=?, short_desc=?, description=?, needs=?,
                            is_new=?, is_featured=?, is_active=?, updated_at=? WHERE id=?""",
                         (cat["id"], int(f["brand_id"]), f["name"], slug, f["short_desc"] or None, f["description"] or None,
                          needs or None, flags["is_new"], flags["is_featured"], flags["is_active"], t, pid))
        else:
            pid = conn.execute("""INSERT INTO products(category_id,brand_id,name,slug,short_desc,description,needs,art,is_new,is_featured,
                                  is_active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                               (cat["id"], int(f["brand_id"]), f["name"], slug, f["short_desc"] or None, f["description"] or None,
                                needs or None, None, flags["is_new"], flags["is_featured"], flags["is_active"], t, t)).lastrowid
        conn.execute("DELETE FROM product_specs WHERE product_id=?", (pid,))
        for g, name, val, i in specs:
            conn.execute("INSERT INTO product_specs(product_id,spec_group,spec_name,spec_value,sort_order) VALUES(?,?,?,?,?)",
                         (pid, g, name, val, i))
        if cat["kind"] == "accessory":
            conn.execute("DELETE FROM accessory_compat WHERE accessory_id=?", (pid,))
            for ph in form_list.get("compat", []):
                if ph.isdigit():
                    conn.execute("INSERT OR IGNORE INTO accessory_compat(accessory_id,phone_id) VALUES(?,?)", (pid, int(ph)))
    return pid


def save_variant(conn, pid, form, user, vid=None):
    f = {k: (form.get(k) or "").strip() for k in ("storage", "ram", "color_name", "color_hex", "list_price", "sale_price", "initial_stock")}
    lp, sp = money(f["list_price"]), money(f["sale_price"])
    err = {}
    if not f["color_name"]:
        err["color_name"] = "Nhập tên màu."
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", f["color_hex"] or ""):
        err["color_hex"] = "Mã màu dạng #RRGGBB."
    if lp <= 0 or sp <= 0:
        err["sale_price"] = "Giá phải lớn hơn 0."
    elif sp > lp:
        err["sale_price"] = "Giá bán không được cao hơn giá gốc."
    if err:
        raise CatalogError(next(iter(err.values())), err)
    active = 1 if form.get("is_active", "1") == "1" else 0
    with db.transaction(conn):
        if vid:
            old = db.one(conn, "SELECT * FROM product_variants WHERE id=? AND product_id=?", (vid, pid))
            if not old:
                raise CatalogError("Không tìm thấy phiên bản.")
            conn.execute("""UPDATE product_variants SET storage=?, ram=?, color_name=?, color_hex=?, list_price=?, sale_price=?, is_active=?
                            WHERE id=?""", (f["storage"] or None, f["ram"] or None, f["color_name"], f["color_hex"].upper(), lp, sp, active, vid))
            if old["sale_price"] != sp:   # ghi lịch sử giá
                conn.execute("INSERT INTO price_history(variant_id,old_price,new_price,changed_by,changed_at) VALUES(?,?,?,?,?)",
                             (vid, old["sale_price"], sp, user["id"], now()))
        else:
            brand = db.scalar(conn, "SELECT b.slug FROM products p JOIN brands b ON b.id=p.brand_id WHERE p.id=?", (pid,)) or "x"
            sku_base = f"{brand[:2].upper()}{pid:03d}-{f['storage'] or 'PK'}{'-' + f['ram'] if f['ram'] else ''}-{slugify(f['color_name'])[:3].upper()}"
            sku, n = sku_base, 2
            while db.scalar(conn, "SELECT 1 FROM product_variants WHERE sku=?", (sku,)):
                sku, n = f"{sku_base}{n}", n + 1
            vid = conn.execute("""INSERT INTO product_variants(product_id,sku,storage,ram,color_name,color_hex,list_price,sale_price,is_active)
                                  VALUES(?,?,?,?,?,?,?,?,?)""", (pid, sku, f["storage"] or None, f["ram"] or None, f["color_name"],
                                                                f["color_hex"].upper(), lp, sp, active)).lastrowid
            conn.execute("INSERT INTO price_history(variant_id,old_price,new_price,changed_by,changed_at) VALUES(?,?,?,?,?)",
                         (vid, None, sp, user["id"], now()))
            inventory.ensure_row(conn, vid, config.LOW_STOCK_DEFAULT)
            q = money(f["initial_stock"])
            if q:
                inventory.move(conn, vid, "import", q, "Nhập kho khi tạo phiên bản", None, user["id"])
    return vid


ALLOWED = {b"\x89PNG\r\n\x1a\n": "png", b"\xff\xd8\xff": "jpg", b"RIFF": "webp"}
MAX_IMAGE = 3 * 1024 * 1024


def upload_image(conn, pid, file, variant_id=None, make_main=False):
    data = file["data"]
    if not data:
        raise CatalogError("Chưa chọn ảnh.")
    if len(data) > MAX_IMAGE:
        raise CatalogError("Ảnh tối đa 3 MB.")
    ext = next((e for sig, e in ALLOWED.items() if data.startswith(sig)), None)
    if ext == "webp" and data[8:12] != b"WEBP":
        ext = None
    if not ext:
        raise CatalogError("Chỉ nhận ảnh PNG, JPG hoặc WEBP.")
    slug = db.scalar(conn, "SELECT slug FROM products WHERE id=?", (pid,))
    fname = f"{slug}-u{secrets.token_hex(4)}.{ext}"
    folder = os.path.join(config.UPLOAD_DIR, "products")
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, fname), "wb") as fh:
        fh.write(data)
    with db.transaction(conn):
        if make_main:
            conn.execute("UPDATE product_images SET is_main=0 WHERE product_id=?", (pid,))
        order = (db.scalar(conn, "SELECT MAX(sort_order) FROM product_images WHERE product_id=?", (pid,)) or 0) + 1
        conn.execute("INSERT INTO product_images(product_id,variant_id,url,alt_text,sort_order,is_main) VALUES(?,?,?,?,?,?)",
                     (pid, variant_id, f"/uploads/products/{fname}", None, -1 if make_main else order, 1 if make_main else 0))


def delete_image(conn, pid, image_id):
    if db.scalar(conn, "SELECT COUNT(*) FROM product_images WHERE product_id=?", (pid,)) <= 1:
        raise CatalogError("Sản phẩm cần ít nhất một ảnh.")
    conn.execute("DELETE FROM product_images WHERE id=? AND product_id=?", (image_id, pid))
    if not db.scalar(conn, "SELECT 1 FROM product_images WHERE product_id=? AND is_main=1", (pid,)):
        conn.execute("UPDATE product_images SET is_main=1 WHERE id=(SELECT id FROM product_images WHERE product_id=? ORDER BY sort_order LIMIT 1)", (pid,))


def save_variant_matrix(conn, pid, form, user):
    """Tạo nhanh nhiều phiên bản: mỗi dòng dung lượng × mỗi màu (US-07: 2 dung lượng × 3 màu = 6 SKU)."""
    rows, err = [], {}
    for i in range(1, 4):
        st = (form.get(f"m_storage{i}") or "").strip()
        lp, sp = money(form.get(f"m_list{i}")), money(form.get(f"m_sale{i}"))
        if not st and not lp and not sp:
            continue
        if not st:
            err[f"m_storage{i}"] = "Nhập dung lượng."
        if lp <= 0:
            err[f"m_list{i}"] = "Thiếu giá gốc."
        if sp <= 0:
            err[f"m_sale{i}"] = "Thiếu giá bán."
        elif sp > lp > 0:
            err[f"m_sale{i}"] = "Giá bán cao hơn giá gốc."
        rows.append((st, (form.get(f"m_ram{i}") or "").strip(), lp, sp))
    colors = []
    for line in (form.get("m_colors") or "").splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^(.*?)\s*(#[0-9A-Fa-f]{6})?$", line)
        colors.append((m.group(1).strip(), (m.group(2) or "#9CA3AF").upper()))
    if not rows:
        err["m_storage1"] = "Nhập ít nhất một dung lượng."
    if not colors or any(not c for c, _ in colors):
        err["m_colors"] = "Nhập ít nhất một màu, mỗi dòng một màu."
    if err:
        raise CatalogError("Chưa tạo phiên bản nào: " + next(iter(err.values())) + " Ô bị thiếu được tô đỏ.", err)
    existing = {(r["storage"], r["color_name"]) for r in db.all(conn, "SELECT storage, color_name FROM product_variants WHERE product_id=?", (pid,))}
    made = 0
    for st, ram, lp, sp in rows:
        for cname, chex in colors:
            if (st, cname) in existing:
                continue
            save_variant(conn, pid, {"storage": st, "ram": ram, "color_name": cname, "color_hex": chex,
                                     "list_price": str(lp), "sale_price": str(sp), "initial_stock": form.get("m_stock") or ""}, user)
            made += 1
    return made
