"""Giriş / çıkış, şifre değiştirme ve rol kontrol yardımcıları."""
import time
from datetime import datetime
from functools import wraps
from urllib.parse import urlsplit

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .extensions import db
from .models import User

bp = Blueprint("auth", __name__)

MIN_PASSWORD_LENGTH = 8

# Basit kaba kuvvet koruması: kullanıcı adı başına 5 hatalı denemede 5 dk bekleme.
# Küçük kurum içi uygulama için bellek içi tutmak yeterlidir.
MAX_FAILED = 5
LOCK_SECONDS = 300
_failed_logins = {}


def admin_required(view):
    """Yalnızca yönetici rolündeki kullanıcıların erişebileceği sayfalar için."""
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def validate_password(password, password2):
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Şifre en az {MIN_PASSWORD_LENGTH} karakter olmalıdır."
    if password != password2:
        return "Şifreler birbiriyle eşleşmiyor."
    return None


def _is_locked(username):
    count, since = _failed_logins.get(username, (0, 0))
    if count >= MAX_FAILED and time.time() - since < LOCK_SECONDS:
        return True
    if count >= MAX_FAILED:
        _failed_logins.pop(username, None)
    return False


def _register_failure(username):
    count, _ = _failed_logins.get(username, (0, 0))
    _failed_logins[username] = (count + 1, time.time())


def _safe_next(target):
    """Açık yönlendirmeyi engeller: yalnızca uygulama içi yollar kabul edilir."""
    if not target:
        return None
    parts = urlsplit(target)
    if parts.scheme or parts.netloc or not target.startswith("/") or target.startswith("//"):
        return None
    return target


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")

        if _is_locked(username):
            flash("Çok sayıda hatalı deneme yapıldı. Lütfen birkaç dakika sonra tekrar deneyiniz.", "danger")
            return render_template("auth/login.html", username=username), 429

        user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
        if user is None or not user.check_password(password) or not user.active:
            _register_failure(username)
            flash("Kullanıcı adı veya şifre hatalı.", "danger")
            return render_template("auth/login.html", username=username), 401

        _failed_logins.pop(username, None)
        session.clear()            # oturum sabitleme saldırısına karşı
        session.permanent = True   # 8 saatlik oturum süresi
        login_user(user)
        user.last_login_at = datetime.now()
        db.session.commit()
        return redirect(_safe_next(request.args.get("next")) or url_for("dashboard.index"))

    return render_template("auth/login.html", username="")


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    session.clear()
    flash("Oturum kapatıldı.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current = request.form.get("current_password", "")
        new = request.form.get("new_password", "")
        new2 = request.form.get("new_password2", "")
        if not current_user.check_password(current):
            flash("Mevcut şifre hatalı.", "danger")
        else:
            error = validate_password(new, new2)
            if error:
                flash(error, "danger")
            else:
                current_user.set_password(new)
                db.session.commit()
                flash("Şifreniz güncellendi.", "success")
                return redirect(url_for("dashboard.index"))
    return render_template("auth/password.html")
