"""Quản trị: hãng và loại phụ kiện (FR-15)."""
from core import db
from core.router import route
from core.server import redirect
from routes.admin.common import admin
from services.admin_catalog import slugify, money


def _unique_slug(conn, table, name):
    base = slugify(name) or "muc"
    slug, n = base, 2
    while db.scalar(conn, f"SELECT 1 FROM {table} WHERE slug=?", (slug,)):
        slug, n = f"{base}-{n}", n + 1
    return slug


@route("/quan-tri/danh-muc", methods=("GET", "POST"))
def taxonomy(req):
    admin(req)
    error = ""
    if req.method == "POST":
        req.check_csrf()
        act = req.form.get("action", "")
        name = (req.form.get("name") or "").strip()
        rid = int(req.form.get("id") or 0)
        order = money(req.form.get("sort_order"))
        c = req.db
        if act in ("them-hang", "sua-hang", "them-loai", "sua-loai") and not 2 <= len(name) <= 40:
            error = "Tên cần từ 2 đến 40 ký tự."
        elif act == "them-hang":
            if db.scalar(c, "SELECT 1 FROM brands WHERE lower(name)=lower(?)", (name,)):
                error = f"Hãng {name} đã có."
            else:
                c.execute("INSERT INTO brands(name,slug,sort_order) VALUES(?,?,?)", (name, _unique_slug(c, "brands", name), order))
        elif act == "sua-hang":
            c.execute("UPDATE brands SET name=?, sort_order=? WHERE id=?", (name, order, rid))
        elif act == "them-loai":
            c.execute("INSERT INTO categories(parent_id,name,slug,kind,sort_order) VALUES(?,?,?,?,?)",
                      (db.scalar(c, "SELECT id FROM categories WHERE slug='phu-kien'"), name, _unique_slug(c, "categories", name), "accessory", order))
        elif act == "sua-loai":
            c.execute("UPDATE categories SET name=?, sort_order=? WHERE id=? AND parent_id IS NOT NULL", (name, order, rid))
        elif act in ("an-loai", "hien-loai"):
            n = db.scalar(c, "SELECT COUNT(*) FROM products WHERE category_id=? AND is_active=1", (rid,))
            if act == "an-loai" and n:
                error = f"Loại này còn {n} sản phẩm đang bán. Hãy ẩn hoặc chuyển các sản phẩm đó sang loại khác trước."
            else:
                c.execute("UPDATE categories SET is_active=? WHERE id=? AND parent_id IS NOT NULL", (1 if act == "hien-loai" else 0, rid))
        if not error:
            return redirect("/quan-tri/danh-muc?tb=ok")
    brands = db.all(req.db, """SELECT b.*, (SELECT COUNT(*) FROM products p WHERE p.brand_id=b.id) n FROM brands b ORDER BY sort_order, name""")
    cats = db.all(req.db, """SELECT c.*, (SELECT COUNT(*) FROM products p WHERE p.category_id=c.id) n FROM categories c
                             WHERE c.parent_id IS NOT NULL ORDER BY sort_order, name""")
    return req.render("admin/taxonomy.html", active="danh-muc", brands=brands, cats=cats, error=error,
                      notice="Đã lưu." if req.query.get("tb") else "")
