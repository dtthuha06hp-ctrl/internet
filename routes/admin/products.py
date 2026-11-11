"""Quản trị sản phẩm, phiên bản, ảnh, kho."""
from core import db
from core.router import route
from core.server import HttpError, redirect
from routes.admin.common import admin, pager
from services import admin_catalog as ac, inventory


def _refs(conn):
    return {
        "cats": db.all(conn, """SELECT c.*, p.name AS parent FROM categories c LEFT JOIN categories p ON p.id=c.parent_id
                                WHERE c.kind='phone' OR c.parent_id IS NOT NULL ORDER BY c.kind DESC, c.sort_order"""),
        "brands": db.all(conn, "SELECT * FROM brands ORDER BY sort_order"),
        "phones": db.all(conn, """SELECT p.id, p.name FROM products p JOIN categories c ON c.id=p.category_id
                                  WHERE c.kind='phone' ORDER BY p.name"""),
        "needs": ac.NEEDS,
    }


@route("/quan-tri/san-pham")
def product_list(req):
    admin(req)
    q, cat, st = req.query.get("q", "").strip()[:50], req.query.get("loai", ""), req.query.get("tt", "")
    _, total = ac.product_list(req.db, q, cat, st, limit=1)
    pg = pager(req, total)
    rows, _ = ac.product_list(req.db, q, cat, st, limit=pg["per"], offset=pg["offset"])
    return req.render("admin/products.html", active="san-pham", rows=rows, pg=pg, q=q, cat=cat, st=st)


@route("/quan-tri/san-pham/moi", methods=("GET", "POST"))
def product_new(req):
    admin(req)
    f, errors, error = {"is_active": "1"}, {}, ""
    if req.method == "POST":
        req.check_csrf()
        try:
            pid = ac.save_product(req.db, req.form, req.form_list)
            return redirect(f"/quan-tri/san-pham/{pid}?tb=moi")
        except ac.CatalogError as e:
            f, errors, error = dict(req.form), e.field, str(e)
            f["needs"] = ",".join(req.form_list.get("needs", []))
    return req.render("admin/product_form.html", active="san-pham", p=None, f=f, errors=errors, error=error, notice="",
                      compat=set(), variants=[], images=[], **_refs(req.db))


@route("/quan-tri/san-pham/<pid>", methods=("GET", "POST"))
def product_edit(req, pid):
    admin(req)
    pid = int(pid) if pid.isdigit() else 0
    p = db.one(req.db, "SELECT p.*, c.kind FROM products p JOIN categories c ON c.id=p.category_id WHERE p.id=?", (pid,))
    if not p:
        raise HttpError(404, "Không tìm thấy sản phẩm.")
    errors, error = {}, ""
    tb = req.query.get("tb", "")
    notice = {"moi": "Đã tạo sản phẩm. Hãy thêm phiên bản (dung lượng × màu) và ảnh bên dưới.", "ok": "Đã lưu."}.get(tb, "")
    if tb.startswith("mt") and tb[2:].isdigit():
        notice = f"Đã tạo {tb[2:]} phiên bản mới, mỗi phiên bản có mã SKU riêng."
    f = dict(p)
    f["specs"] = ac.specs_text(req.db, pid)
    vform, verr = {}, {}
    if req.method == "POST":
        req.check_csrf()
        act = req.form.get("action", "")
        try:
            if act == "luu":
                ac.save_product(req.db, req.form, req.form_list, pid)
            elif act in ("them-pb", "sua-pb"):
                vid = int(req.form.get("vid")) if act == "sua-pb" else None
                ac.save_variant(req.db, pid, req.form, req.user, vid)
            elif act == "ma-tran":
                n = ac.save_variant_matrix(req.db, pid, req.form, req.user)
                return redirect(f"/quan-tri/san-pham/{pid}?tb=mt{n}#phien-ban")
            elif act == "anh":
                for fl in req.files.get("image", []):
                    v = req.form.get("variant_id")
                    ac.upload_image(req.db, pid, fl, int(v) if v and v.isdigit() else None, req.form.get("main") == "1")
            elif act == "xoa-anh":
                ac.delete_image(req.db, pid, int(req.form.get("image_id") or 0))
            elif act in ("an", "hien"):
                req.db.execute("UPDATE products SET is_active=? WHERE id=?", (1 if act == "hien" else 0, pid))
            return redirect(f"/quan-tri/san-pham/{pid}?tb=ok#{req.form.get('anchor', '')}")
        except ac.CatalogError as e:
            error = str(e)
            if act == "luu":
                f, errors = dict(req.form), e.field
                f["needs"] = ",".join(req.form_list.get("needs", []))
            else:
                vform, verr = dict(req.form), e.field
    variants = [dict(r) for r in db.all(req.db, """SELECT v.*, i.on_hand, i.reserved, i.on_hand-i.reserved AS available
                                                  FROM product_variants v LEFT JOIN inventory i ON i.variant_id=v.id
                                                  WHERE v.product_id=? ORDER BY v.id""", (pid,))]
    for v in variants:
        v["history"] = db.all(req.db, """SELECT h.*, u.full_name FROM price_history h LEFT JOIN users u ON u.id=h.changed_by
                                         WHERE h.variant_id=? ORDER BY h.changed_at DESC LIMIT 3""", (v["id"],))
    images = db.all(req.db, """SELECT im.*, v.color_name FROM product_images im LEFT JOIN product_variants v ON v.id=im.variant_id
                               WHERE im.product_id=? ORDER BY im.is_main DESC, im.sort_order""", (pid,))
    compat = {r["phone_id"] for r in db.all(req.db, "SELECT phone_id FROM accessory_compat WHERE accessory_id=?", (pid,))}
    return req.render("admin/product_form.html", active="san-pham", p=dict(p), f=f, errors=errors, error=error, notice=notice,
                      variants=variants, images=images, compat=compat, vform=vform, verr=verr, **_refs(req.db))


# ---------------- Kho ----------------
@route("/quan-tri/kho", methods=("GET", "POST"))
def stock(req):
    admin(req)
    error = notice = ""
    if req.method == "POST":
        req.check_csrf()
        try:
            vid = int(req.form.get("variant_id") or 0)
            qty = int(req.form.get("qty") or 0)
            act = req.form.get("action")
            reason = (req.form.get("reason") or "").strip()
            with db.transaction(req.db):
                if act == "nhap":
                    inventory.move(req.db, vid, "import", qty, reason or "Nhập hàng từ nhà cung cấp", None, req.user["id"])
                elif act == "dieu-chinh":
                    inventory.move(req.db, vid, "adjust", qty, reason, None, req.user["id"])
                elif act == "nguong":
                    req.db.execute("UPDATE inventory SET low_threshold=? WHERE variant_id=?", (max(0, qty), vid))
            notice = "Đã cập nhật kho."
        except (inventory.StockError, ValueError) as e:
            error = str(e) or "Số lượng không hợp lệ."
    q = req.query.get("q", "").strip()[:50]
    only_low = req.query.get("sap-het") == "1"
    sql = """ FROM inventory i JOIN product_variants v ON v.id=i.variant_id JOIN products p ON p.id=v.product_id WHERE 1=1"""
    args = []
    if q:
        sql += " AND (p.name LIKE ? OR v.sku LIKE ?)"
        args += [f"%{q}%", f"%{q}%"]
    if only_low:
        sql += " AND i.on_hand-i.reserved<=i.low_threshold"
    total = db.scalar(req.db, "SELECT COUNT(*)" + sql, args)
    pg = pager(req, total, 40)
    rows = db.all(req.db, """SELECT i.*, v.sku, v.storage, v.color_name, p.name, p.id pid, i.on_hand-i.reserved available"""
                  + sql + " ORDER BY (i.on_hand-i.reserved<=i.low_threshold) DESC, available, p.name LIMIT ? OFFSET ?",
                  args + [pg["per"], pg["offset"]])
    log = db.all(req.db, """SELECT t.*, v.sku, p.name, u.full_name FROM inventory_transactions t JOIN product_variants v ON v.id=t.variant_id
                            JOIN products p ON p.id=v.product_id LEFT JOIN users u ON u.id=t.created_by
                            ORDER BY t.created_at DESC, t.id DESC LIMIT 15""")
    low_n = db.scalar(req.db, "SELECT COUNT(*) FROM inventory WHERE on_hand-reserved<=low_threshold")
    return req.render("admin/stock.html", active="kho", rows=rows, pg=pg, q=q, only_low=only_low, log=log, low_n=low_n,
                      error=error, notice=notice)
