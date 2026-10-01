"""Komut satırı komutları.

    flask --app app init-db          Tabloları ve başlangıç projelerini/kategorilerini oluşturur
    flask --app app create-admin     Yönetici hesabı oluşturur (veya şifresini sıfırlar)
    flask --app app seed-demo        Demo personel ve destek kayıtları oluşturur
    flask --app app clear-demo       Demo verilerini temizler
"""
import click

from .auth import MIN_PASSWORD_LENGTH
from .constants import ROLE_ADMIN
from .demo import DEMO_PASSWORD, clear_demo, ensure_base_data, seed_demo
from .extensions import db
from .models import User


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        """Veritabanını ve başlangıç verilerini oluşturur."""
        db.create_all()
        ensure_base_data()
        click.echo("Veritabanı hazır.")

    @app.cli.command("create-admin")
    @click.option("--username", prompt="Kullanıcı adı", default="admin")
    @click.option("--full-name", prompt="Ad Soyad", default="Sistem Yöneticisi")
    @click.option("--password", prompt="Şifre", hide_input=True, confirmation_prompt=True)
    def create_admin(username, full_name, password):
        """Yönetici hesabı oluşturur; kullanıcı varsa şifresini sıfırlar ve yönetici yapar."""
        if len(password) < MIN_PASSWORD_LENGTH:
            raise click.ClickException(f"Şifre en az {MIN_PASSWORD_LENGTH} karakter olmalıdır.")
        ensure_base_data()
        username = username.strip().lower()
        user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
        if user is None:
            user = User(username=username, full_name=full_name.strip(), role=ROLE_ADMIN)
            db.session.add(user)
            message = f"Yönetici oluşturuldu: {username}"
        else:
            user.role, user.active = ROLE_ADMIN, True
            message = f"Mevcut kullanıcı güncellendi (yönetici, yeni şifre): {username}"
        user.set_password(password)
        db.session.commit()
        click.echo(message)

    @app.cli.command("seed-demo")
    @click.option("--count", default=45, show_default=True, help="Oluşturulacak kayıt sayısı")
    def seed_demo_cmd(count):
        """Demo personel ve destek kayıtları oluşturur."""
        n = seed_demo(count=count)
        click.echo(f"{n} demo kayıt oluşturuldu. Demo personel şifresi: {DEMO_PASSWORD}")

    @app.cli.command("clear-demo")
    @click.confirmation_option(prompt="Tüm demo veriler silinecek. Emin misiniz?")
    def clear_demo_cmd():
        """Demo verilerini temizler (gerçek kayıtlara dokunmaz)."""
        tickets, users, deactivated = clear_demo()
        click.echo(f"{tickets} demo kayıt ve {users} demo personel silindi; {deactivated} personel pasife alındı.")
