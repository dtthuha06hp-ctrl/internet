"""Quản trị: báo cáo + xuất CSV (chỉ quản trị viên)."""
from core.router import route
from core.server import Response
from routes.admin.common import admin
from services import reports as rp

PERIODS = {"7": 7, "30": 30, "90": 90}


def _period(req):
    k = req.query.get("ky", "30")
    k = k if k in PERIODS else "30"
    return k, *rp.period(PERIODS[k])


@route("/quan-tri/bao-cao")
def report(req):
    admin(req)
    k, d1, d2 = _period(req)
    c = req.db
    top = rp.top_products(c, d1, d2)
    mx = max([t["revenue"] for t in top] + [1])
    return req.render("admin/reports.html", active="bao-cao", ky=k, d1=d1, d2=d2, s=rp.summary(c, d1, d2),
                      days=rp.by_day(c, d1, d2), top=top, top_max=mx, cats=rp.by_category(c, d1, d2),
                      pays=rp.payment_mix(c, d1, d2), reasons=rp.cancel_reasons(c, d1, d2))


@route("/quan-tri/bao-cao/xuat")
def export(req):
    admin(req)
    k, d1, d2 = _period(req)
    kind = req.query.get("loai", "don-hang")
    if kind == "san-pham":
        rows = [["Sản phẩm", "Số lượng bán", "Số đơn", "Doanh thu (₫)"]] + [
            [t["name"], t["qty"], t["orders"], t["revenue"]] for t in rp.top_products(req.db, d1, d2, limit=1000)]
    else:
        kind = "don-hang"
        rows = rp.orders_csv_rows(req.db, d1, d2)
    name = f"nhipmobile-{kind}-{d1}-den-{d2}.csv"
    return Response(rp.to_csv(rows), 200, "text/csv; charset=utf-8", {"Content-Disposition": f'attachment; filename="{name}"'})
