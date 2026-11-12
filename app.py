"""Điểm khởi động website Nhịp Mobile.

Cách chạy: bấm đúp chay_web.bat (Windows) hoặc gõ: python app.py
Tùy chọn:  --reset       xóa dữ liệu, nạp lại dữ liệu mẫu rồi thoát
           --no-browser  không tự mở trình duyệt
           --port 8000   chọn cổng
"""
import argparse
import os
import sys
import threading
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

if sys.version_info < (3, 9):
    print("Cần Python 3.9 trở lên. Hãy cài bản mới tại python.org")
    sys.exit(1)

import config  # noqa: E402
from core import db, server, session  # noqa: E402

# Nạp các trang (mỗi file tự đăng ký đường dẫn của mình)
from routes.shop import home, search, account, catalog, product, compare, cart, checkout, tracking, my_account  # noqa: E402,F401
from routes.admin import dashboard, mailbox, orders, products, customers, marketing, reports, taxonomy  # noqa: E402,F401
from routes.shop import pages  # noqa: E402,F401  (nạp sau cùng: trang "sẽ có ở giai đoạn sau")


def prepare(reset=False):
    from database import seed
    if reset or not os.path.exists(config.DB_PATH):
        print("Đang tạo cơ sở dữ liệu và dữ liệu mẫu...")
        try:
            seed.build()
        except PermissionError:
            print("Không xóa được dữ liệu cũ vì web đang chạy. Hãy đóng cửa sổ web rồi thử lại.")
            sys.exit(1)
    conn = db.connect()
    from services import promotions
    promotions.ensure_daily(conn)
    session.cleanup(conn)
    conn.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--port", type=int, default=config.PORT)
    args = ap.parse_args()

    if args.reset:
        prepare(reset=True)
        print("Xong. Dữ liệu đã trở về như ban đầu.")
        return
    prepare()

    httpd = None
    for port in range(args.port, args.port + 11):
        try:
            httpd = server.serve(config.HOST, port)
            break
        except OSError:
            continue
    if not httpd:
        print("Không mở được cổng nào từ", args.port, "đến", args.port + 10, ". Hãy tắt cửa sổ web cũ rồi thử lại.")
        return
    url = f"http://{config.HOST}:{httpd.server_address[1]}"
    line = "=" * 62
    print(line)
    print(f"  {config.SHOP_NAME} đang chạy tại:  {url}")
    print(f"  Trang quản trị:                {url}/quan-tri")
    print("  Tài khoản admin:  " + config.ADMIN_EMAIL + " / " + ("(mật khẩu đặt trong ADMIN_PASSWORD)" if config.ON_SERVER else config.ADMIN_PASSWORD))
    print("  Tài khoản khách:  khach@nhipmobile.vn / Khach@123")
    print()
    print("  ĐỂ TẮT WEB: đóng cửa sổ này (hoặc bấm Ctrl + C).")
    print(line)
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã tắt web. Hẹn gặp lại!")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
