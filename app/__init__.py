"""Kurum İçi Teknik Destek Kayıt ve İstatistik Programı - uygulama fabrikası."""
import os
import secrets
import sys
from datetime import timedelta

from flask import Flask, abort, redirect, render_template, request, session, url_for
from sqlalchemy import event
from sqlalchemy.engine import Engine

from . import constants as C
from .extensions import db, login_manager


def _load_secret_key(instance_path):
    """SECRET_KEY ortam değişkeninden okunur; yoksa veri klasöründe bir kez üretilir."""
    key = os.environ.get("SECRET_KEY")
    if key:
        return key
    path = os.path.join(instance_path, "secret_key")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(secrets.token_hex(32))
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


@event.listens_for(Engine, "connect")
def _sqlite_pragmas(dbapi_connection, connection_record):
    """SQLite: yabancı anahtar kontrolü ve eşzamanlı okuma için WAL modu."""
    if type(dbapi_connection).__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()
        # SQLite'ın LOWER() fonksiyonu Türkçe harfleri (Ş, İ, Ç, Ö, Ü, Ğ) küçültmez;
        # aramada büyük/küçük harf duyarsızlığı için Türkçe uyumlu fonksiyon
        dbapi_connection.create_function("tr_lower", 1, tr_lower, deterministic=True)


def tr_lower(value):
    if value is None:
        return None
    return str(value).replace("I", "ı").replace("İ", "i").lower()


def default_data_dir():
    """Veri klasörü: veritabanı, gizli anahtar ve yedekler burada tutulur.

    .exe olarak çalışırken programın yanındaki "veri" klasörü,
    kaynak koddan çalışırken proje kökündeki "veri" klasörü kullanılır.
    DESTEK_DATA_DIR ortam değişkeni ile değiştirilebilir.
    """
    if os.environ.get("DESTEK_DATA_DIR"):
        return os.path.abspath(os.environ["DESTEK_DATA_DIR"])
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), "veri")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "veri")


def create_app(test_config=None, data_dir=None):
    app = Flask(__name__, instance_path=os.path.abspath(data_dir or default_data_dir()))
    os.makedirs(app.instance_path, exist_ok=True)

    app.config.update(
        SECRET_KEY=_load_secret_key(app.instance_path),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL",
            "sqlite:///" + os.path.join(app.instance_path, "destek.db"),
        ),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE") == "1",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        # Ortak bilgisayar: bu kadar dakika işlem yapılmazsa oturum kendiliğinden kapanır
        IDLE_TIMEOUT_MINUTES=int(os.environ.get("IDLE_TIMEOUT_MINUTES", "15")),
        TICKETS_PER_PAGE=50,
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Bu sayfayı görüntülemek için giriş yapınız."
    login_manager.login_message_category = "warning"
    login_manager.session_protection = "strong"

    from .models import Setting, User

    @login_manager.user_loader
    def load_user(user_id):
        user = db.session.get(User, int(user_id))
        # Pasife alınan kullanıcının açık oturumu da sonlanır
        return user if user and user.active else None

    from .admin import bp as admin_bp
    from .auth import bp as auth_bp
    from .dashboard import bp as dashboard_bp
    from .reports import bp as reports_bp
    from .stats import bp as stats_bp
    from .tickets import bp as tickets_bp

    for bp in (auth_bp, dashboard_bp, tickets_bp, stats_bp, reports_bp, admin_bp):
        app.register_blueprint(bp)

    from .cli import register_cli
    register_cli(app)

    _register_local_only(app)
    _register_csrf(app)
    _register_idle_timeout(app)
    _register_initial_setup(app, User)
    _register_template_helpers(app, Setting)
    _register_error_handlers(app)

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; frame-ancestors 'none'",
        )
        # Kişisel veri içeren sayfalar tarayıcı önbelleğinde kalmasın
        if request.endpoint and request.endpoint != "static":
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    with app.app_context():
        db.create_all()
        from .demo import ensure_base_data
        ensure_base_data()   # ilk çalıştırmada başlangıç projeleri ve kategorileri

    return app


def _register_csrf(app):
    """Tüm POST formları için basit oturum tabanlı CSRF koruması."""

    def csrf_token():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_hex(32)
        return session["csrf_token"]

    @app.before_request
    def check_csrf():
        if request.method == "POST" and not app.config.get("CSRF_DISABLED"):
            sent = request.form.get("csrf_token", "")
            expected = session.get("csrf_token", "")
            if not expected or not secrets.compare_digest(sent, expected):
                abort(400, description="Oturum doğrulaması başarısız. Sayfayı yenileyip tekrar deneyiniz.")

    app.jinja_env.globals["csrf_token"] = csrf_token


LOCAL_ADDRESSES = {"127.0.0.1", "::1"}


def _register_local_only(app):
    """Program yalnızca kurulu olduğu bilgisayardan kullanılır.

    Sunucu zaten yalnızca 127.0.0.1'i dinler; bu kontrol ikinci bir güvenlik katmanıdır.
    """
    @app.before_request
    def reject_remote():
        if request.remote_addr not in LOCAL_ADDRESSES:
            abort(403)


def _register_idle_timeout(app):
    """Belirli süre işlem yapılmayan oturumu kapatır (ortak bilgisayar güvenliği)."""
    from flask_login import current_user, logout_user
    import time

    @app.before_request
    def idle_logout():
        if request.endpoint == "static" or not current_user.is_authenticated:
            return None
        now = time.time()
        last = session.get("last_seen")
        if last and now - last > app.config["IDLE_TIMEOUT_MINUTES"] * 60:
            logout_user()
            session.clear()
            from flask import flash
            flash("Uzun süre işlem yapılmadığı için oturumunuz kapatıldı. Lütfen tekrar giriş yapınız.", "warning")
            return redirect(url_for("auth.login"))
        session["last_seen"] = now
        return None


def _register_initial_setup(app, User):
    """Hiç yönetici yoksa (ilk kurulum) tüm istekler kurulum ekranına yönlendirilir."""

    @app.before_request
    def require_initial_setup():
        if app.config.get("SETUP_DONE") or request.endpoint in ("auth.setup", "static"):
            return None
        has_admin = db.session.execute(
            db.select(User.id).where(User.role == C.ROLE_ADMIN, User.active.is_(True)).limit(1)
        ).first()
        if has_admin:
            app.config["SETUP_DONE"] = True
            return None
        return redirect(url_for("auth.setup"))


def _register_template_helpers(app, Setting):
    @app.context_processor
    def inject_globals():
        return {
            "C": C,
            "ROLES": C.ROLES,
            "SOURCES": C.SOURCES,
            "STATUSES": C.STATUSES,
            "PRIORITIES": C.PRIORITIES,
            "CHANNELS": C.CHANNELS,
            "org_name": Setting.get("org_name"),
        }

    @app.template_filter("date_tr")
    def date_tr(value):
        return value.strftime("%d.%m.%Y") if value else ""

    @app.template_filter("time_tr")
    def time_tr(value):
        return value.strftime("%H:%M") if value else ""

    @app.template_filter("datetime_tr")
    def datetime_tr(value):
        return value.strftime("%d.%m.%Y %H:%M") if value else ""

    @app.template_filter("minutes")
    def minutes(value):
        """Dakikayı okunur biçime çevirir: 8 dk, 1 sa 5 dk."""
        if value is None:
            return "-"
        value = int(round(value))
        if value < 60:
            return f"{value} dk"
        hours, mins = divmod(value, 60)
        return f"{hours} sa {mins} dk" if mins else f"{hours} sa"

    @app.template_filter("num")
    def num(value, digits=0):
        if value is None:
            return "-"
        text = f"{value:,.{digits}f}"
        # Türkçe biçim: binlik ayırıcı nokta, ondalık virgül
        return text.replace(",", "X").replace(".", ",").replace("X", ".")


def _register_error_handlers(app):
    def render_error(code, title, message):
        return render_template("errors/error.html", code=code, title=title, message=message), code

    @app.errorhandler(400)
    def bad_request(e):
        return render_error(400, "Geçersiz istek", getattr(e, "description", ""))

    @app.errorhandler(403)
    def forbidden(e):
        return render_error(403, "Yetkisiz erişim", "Bu sayfayı görüntüleme yetkiniz bulunmuyor.")

    @app.errorhandler(404)
    def not_found(e):
        return render_error(404, "Sayfa bulunamadı", "Aradığınız sayfa veya kayıt bulunamadı.")

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_error(500, "Beklenmeyen hata", "İşlem sırasında bir hata oluştu. Lütfen tekrar deneyiniz.")
