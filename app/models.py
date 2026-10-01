"""Veritabanı modelleri.

Tablolar: users, projects, categories, support_tickets, audit_logs, settings.
Kayıtlar silinmez; arşivlenir. İstatistik sorgularında sık kullanılan alanlar
(tarih, proje, personel, kaynak, durum) indekslidir.
"""
import json
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .constants import (
    CHANNELS, DONE_STATUSES, PRIORITIES, ROLE_ADMIN, ROLES, SOURCES, STATUSES,
)
from .extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    is_demo = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    last_login_at = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):  # Flask-Login: pasif kullanıcı oturum açamaz
        return self.active

    @property
    def is_admin(self):
        return self.role == ROLE_ADMIN

    @property
    def role_label(self):
        return ROLES.get(self.role, self.role)


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)


class SupportTicket(db.Model):
    __tablename__ = "support_tickets"
    __table_args__ = (
        db.UniqueConstraint("year", "seq", name="uq_ticket_year_seq"),
    )

    id = db.Column(db.Integer, primary_key=True)
    # Kayıt no: YYYY-NNNNN (yıl + yıl içi sıra)
    ticket_no = db.Column(db.String(20), unique=True, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    seq = db.Column(db.Integer, nullable=False)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now, index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False, index=True)

    # KVKK: talep sahibi için yalnızca ad ve (isteğe bağlı) telefon tutulur
    requester_name = db.Column(db.String(100), nullable=False)
    requester_phone = db.Column(db.String(20))

    channel = db.Column(db.String(20), nullable=False)
    source = db.Column(db.String(20), nullable=False, index=True)
    priority = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    resolution = db.Column(db.Text)
    duration_minutes = db.Column(db.Integer)

    updated_at = db.Column(db.DateTime)
    updated_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    resolved_at = db.Column(db.DateTime)

    archived = db.Column(db.Boolean, nullable=False, default=False, index=True)
    archived_at = db.Column(db.DateTime)
    archived_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    is_demo = db.Column(db.Boolean, nullable=False, default=False)

    created_by = db.relationship("User", foreign_keys=[created_by_id])
    updated_by = db.relationship("User", foreign_keys=[updated_by_id])
    archived_by = db.relationship("User", foreign_keys=[archived_by_id])
    project = db.relationship("Project")
    category = db.relationship("Category")

    @property
    def source_label(self):
        return SOURCES.get(self.source, self.source)

    @property
    def status_label(self):
        return STATUSES.get(self.status, self.status)

    @property
    def priority_label(self):
        return PRIORITIES.get(self.priority, self.priority)

    @property
    def channel_label(self):
        return CHANNELS.get(self.channel, self.channel)

    @property
    def is_done(self):
        return self.status in DONE_STATUSES


class AuditLog(db.Model):
    """Basit işlem geçmişi: kim, ne zaman, neyi değiştirdi."""
    __tablename__ = "audit_logs"
    __table_args__ = (db.Index("ix_audit_entity", "entity_type", "entity_id"),)

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    entity_type = db.Column(db.String(30), nullable=False)   # ticket, project, category, user, setting
    entity_id = db.Column(db.Integer)
    action = db.Column(db.String(30), nullable=False)        # create, update, status, archive, restore
    # {"Alan adı": ["eski", "yeni"]} biçiminde JSON
    changes = db.Column(db.Text)

    user = db.relationship("User")

    ACTION_LABELS = {
        "create": "Oluşturuldu",
        "update": "Güncellendi",
        "status": "Durum değişti",
        "archive": "Arşivlendi",
        "restore": "Arşivden çıkarıldı",
    }

    @property
    def action_label(self):
        return self.ACTION_LABELS.get(self.action, self.action)

    @property
    def changes_dict(self):
        if not self.changes:
            return {}
        try:
            return json.loads(self.changes)
        except ValueError:
            return {}


class Setting(db.Model):
    """Basit anahtar/değer sistem ayarları."""
    __tablename__ = "settings"

    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(500))

    DEFAULTS = {
        "org_name": "Kurum İçi Teknik Destek",
    }

    @classmethod
    def get(cls, key):
        row = db.session.get(cls, key)
        return row.value if row else cls.DEFAULTS.get(key, "")

    @classmethod
    def set(cls, key, value):
        row = db.session.get(cls, key)
        if row is None:
            row = cls(key=key)
            db.session.add(row)
        row.value = value


def log_action(user, entity_type, entity_id, action, changes=None, at=None):
    """İşlem geçmişine bir satır ekler (commit çağırana aittir)."""
    db.session.add(AuditLog(
        created_at=at or datetime.now(),
        user_id=user.id if user else None,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        changes=json.dumps(changes, ensure_ascii=False) if changes else None,
    ))
