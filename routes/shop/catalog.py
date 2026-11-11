"""Trang danh mục: /dien-thoai và /phu-kien."""
from core import db
from core.router import route
from services import catalog


def _more_url(base, q, page):
    from urllib.parse import urlencode
    q = {k: v for k, v in q.items() if v and k != "partial"}
    q["trang"] = page + 1
    return base + "?" + urlencode(q)


def _query(req):
    """Gộp ?hang=a&hang=b và ?hang=a,b về cùng một dạng."""
    q = {}
    for k, vals in req.query_list.items():
        q[k] = ",".join(v for v in vals if v)
    return q


@route("/dien-thoai")
def phones(req):
    q = _query(req)
    data = catalog.browse(req.db, "phone", q)
    data["more_url"] = _more_url("/dien-thoai", q, data["page"])
    title = "Điện thoại"
    sel_brand = data["sel"].get("hang", [])
    if len(sel_brand) == 1:
        title = "Điện thoại " + next(o["label"] for g in data["groups"] if g["key"] == "hang" for o in g["options"] if o["on"])
    return req.render("shop/catalog.html", kind="phone", title=title, base="/dien-thoai",
                      quick=catalog.NEEDS, quick_key="nhu-cau", **data)


@route("/phu-kien")
def accessories(req):
    q = _query(req)
    data = catalog.browse(req.db, "accessory", q)
    data["more_url"] = _more_url("/phu-kien", q, data["page"])
    title = "Phụ kiện"
    loai = data["sel"].get("loai", [])
    if len(loai) == 1:
        title = db.scalar(req.db, "SELECT name FROM categories WHERE slug=?", (loai[0],)) or title
    quick = [(r["slug"], r["name"]) for r in db.all(req.db, """SELECT slug, name FROM categories
             WHERE kind='accessory' AND parent_id IS NOT NULL AND is_active=1 ORDER BY sort_order""")]
    return req.render("shop/catalog.html", kind="accessory", title=title, base="/phu-kien",
                      quick=quick, quick_key="loai", **data)
