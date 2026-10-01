"""Teknik Destek Kayıt Programı - başlatıcı.

Windows'ta DestekKayit.exe bu dosyadan üretilir. Program bir bilgisayarda çalışır;
o bilgisayardan ve aynı ağdaki diğer bilgisayarlardan tarayıcı ile kullanılır.

    python run.py                      Programı başlatır ve tarayıcıyı açar
    python run.py --no-browser         Tarayıcı açmadan başlatır (otomatik başlatma için)
    python run.py --port 8080          Farklı port kullanır (varsayılan 8000)
    python run.py --yonetici-sifirla   Yönetici şifresini sıfırlar (şifre unutulursa)
    python run.py --debug              Geliştirme sunucusu (yalnızca geliştirme)

Veriler programın yanındaki "veri" klasöründe tutulur (DESTEK_DATA_DIR ile değiştirilebilir).
"""
import argparse
import getpass
import os
import socket
import sys
import threading
import time
import webbrowser


def local_ips():
    """Bu bilgisayarın ağ (IPv4) adresleri."""
    ips = set()
    try:
        # Hiçbir veri göndermez; yalnızca varsayılan ağ arayüzünü öğrenmek içindir
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ips.add(s.getsockname()[0])
    except OSError:
        pass
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            ips.add(ip)
    except OSError:
        pass
    return sorted(ip for ip in ips if not ip.startswith("127."))


def port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def backup_loop(app):
    """Program açık kaldığı sürece günde bir yedek alır (saatte bir kontrol eder)."""
    from app.backup import create_backup
    while True:
        try:
            create_backup(app, daily=True)
        except Exception as exc:  # yedek hatası programı durdurmamalı
            print(f"[Uyarı] Yedek alınamadı: {exc}")
        time.sleep(3600)


def reset_admin(app):
    from app.constants import ROLE_ADMIN
    from app.extensions import db
    from app.models import User

    print("\n=== Yönetici şifresi sıfırlama ===")
    with app.app_context():
        admins = db.session.execute(db.select(User).where(User.role == ROLE_ADMIN)).scalars().all()
        if admins:
            print("Mevcut yöneticiler: " + ", ".join(u.username for u in admins))
        username = input("Kullanıcı adı [admin]: ").strip().lower() or "admin"
        password = getpass.getpass("Yeni şifre (en az 8 karakter, yazarken görünmez): ")
        if len(password) < 8 or password != getpass.getpass("Yeni şifre (tekrar): "):
            print("Şifre en az 8 karakter olmalı ve iki giriş aynı olmalıdır. İşlem iptal edildi.")
            return
        user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
        if user is None:
            user = User(username=username, full_name="Sistem Yöneticisi", role=ROLE_ADMIN)
            db.session.add(user)
        user.role, user.active = ROLE_ADMIN, True
        user.set_password(password)
        db.session.commit()
        print(f"Tamam: '{username}' kullanıcısı yönetici yapıldı ve şifresi güncellendi.")


def main():
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    parser = argparse.ArgumentParser(description="Teknik Destek Kayıt Programı")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    parser.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    parser.add_argument("--no-browser", action="store_true", help="Tarayıcıyı otomatik açma")
    parser.add_argument("--yonetici-sifirla", action="store_true", help="Yönetici şifresini sıfırla")
    parser.add_argument("--debug", action="store_true", help="Flask geliştirme sunucusu")
    args = parser.parse_args()

    local_url = f"http://localhost:{args.port}"

    if not args.yonetici_sifirla and port_in_use(args.port):
        print(f"Program zaten çalışıyor. Tarayıcıda açılıyor: {local_url}")
        if not args.no_browser:
            webbrowser.open(local_url)
        time.sleep(3)
        return

    from app import create_app
    app = create_app()

    if args.yonetici_sifirla:
        reset_admin(app)
        return

    lan_urls = [f"http://{ip}:{args.port}" for ip in local_ips()]
    app.config["ACCESS_URLS"] = lan_urls

    if args.debug:
        app.run(host=args.host, port=args.port, debug=True)
        return

    threading.Thread(target=backup_loop, args=(app,), daemon=True).start()

    line = "=" * 64
    print(line)
    print("  TEKNİK DESTEK KAYIT PROGRAMI ÇALIŞIYOR")
    print(line)
    print(f"  Bu bilgisayardan      : {local_url}")
    for url in lan_urls:
        print(f"  Diğer bilgisayarlardan: {url}")
    print(f"  Veri klasörü          : {app.instance_path}")
    print(line)
    print("  Bu pencereyi KAPATMAYIN. Kapatırsanız program durur.")
    print("  (Pencereyi simge durumuna küçültebilirsiniz.)")
    print(line)

    if not args.no_browser:
        threading.Timer(1.5, webbrowser.open, args=(local_url,)).start()

    from waitress import serve
    serve(app, host=args.host, port=args.port, threads=8)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        # .exe penceresi hata mesajı okunmadan kapanmasın
        print(f"\nHATA: {exc}")
        if getattr(sys, "frozen", False):
            input("Kapatmak için Enter'a basınız...")
        raise
