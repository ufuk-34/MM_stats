"""Destek kayıtları: oluşturma, listeleme, detay, düzenleme, durum ve arşiv."""
import re
from datetime import datetime

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from .auth import admin_required
from .constants import (
    CHANNEL_PHONE, CHANNELS, DONE_STATUSES, MAX_DURATION_MINUTES, PRIORITIES, PRIORITY_NORMAL,
    QUICK_DURATIONS, SOURCE_HINTS, SOURCES, STATUS_OPEN, STATUSES,
)
from .extensions import db
from .models import AuditLog, Category, Project, SupportTicket as T, User, log_action
from .queries import STATUS_GROUPS, TicketFilters, ticket_query

bp = Blueprint("tickets", __name__, url_prefix="/tickets")

PHONE_RE = re.compile(r"^[0-9+()\s-]{0,20}$")
MAX_TEXT = 4000

# İşlem geçmişinde gösterilecek alan adları
FIELD_LABELS = {
    "project_id": "Proje",
    "requester_name": "Talep sahibi",
    "requester_phone": "Telefon",
    "channel": "İletişim kanalı",
    "source": "Sorun kaynağı",
    "category_id": "Sorun kategorisi",
    "description": "Açıklama",
    "priority": "Öncelik",
    "duration_minutes": "İşlem süresi (dk)",
    "resolution": "Yapılan işlem / çözüm",
    "status": "Durum",
}
EDITABLE_FIELDS = tuple(FIELD_LABELS)
# "Benzer kayıt": talep sahibi dışındaki tüm alanlar kopyalanır
COPY_FIELDS = tuple(f for f in EDITABLE_FIELDS if f not in ("requester_name", "requester_phone"))


# --------------------------------------------------------------------------- #
# Yardımcılar
# --------------------------------------------------------------------------- #

def get_ticket_or_404(ticket_id):
    """Personel yalnızca kendi kayıtlarına erişebilir; diğerleri için 404 döner."""
    ticket = db.session.get(T, ticket_id)
    if ticket is None:
        abort(404)
    if not current_user.is_admin and (ticket.created_by_id != current_user.id or ticket.archived):
        abort(404)
    return ticket


def active_projects(include_id=None):
    q = db.select(Project).where((Project.active.is_(True)) | (Project.id == include_id))
    return db.session.execute(q.order_by(Project.sort_order, Project.id)).scalars().all()


def active_categories(include_id=None):
    q = db.select(Category).where((Category.active.is_(True)) | (Category.id == include_id))
    return db.session.execute(q.order_by(Category.sort_order, Category.name)).scalars().all()


def display_value(field, value):
    """İşlem geçmişi için okunur değer."""
    if value in (None, ""):
        return "-"
    if field == "project_id":
        p = db.session.get(Project, value)
        return p.name if p else str(value)
    if field == "category_id":
        c = db.session.get(Category, value)
        return c.name if c else str(value)
    labels = {"source": SOURCES, "status": STATUSES, "priority": PRIORITIES, "channel": CHANNELS}
    if field in labels:
        return labels[field].get(value, value)
    text = str(value)
    return text if len(text) <= 120 else text[:117] + "..."


def parse_ticket_form(form, ticket=None):
    """Form verisini doğrular. (veri, hatalar) döndürür."""
    errors = {}
    data = {}

    def text(name, max_len):
        return form.get(name, "").strip()[:max_len]

    project_id = form.get("project_id", type=int)
    allowed_projects = {p.id for p in active_projects(ticket.project_id if ticket else None)}
    if project_id not in allowed_projects:
        errors["project_id"] = "Proje seçiniz."
    data["project_id"] = project_id

    category_id = form.get("category_id", type=int)
    allowed_categories = {c.id for c in active_categories(ticket.category_id if ticket else None)}
    if category_id not in allowed_categories:
        errors["category_id"] = "Sorun kategorisi seçiniz."
    data["category_id"] = category_id

    data["requester_name"] = text("requester_name", 100)
    if not data["requester_name"]:
        errors["requester_name"] = "Talep sahibinin adını giriniz."

    phone = form.get("requester_phone", "").strip()
    if not PHONE_RE.match(phone):
        errors["requester_phone"] = "Telefon yalnızca rakam, boşluk, +, -, ( ) içerebilir (en fazla 20 karakter)."
    data["requester_phone"] = phone[:20] or None

    for name, options, label in (
        ("channel", CHANNELS, "İletişim kanalı"),
        ("source", SOURCES, "Sorun kaynağı"),
        ("priority", PRIORITIES, "Öncelik"),
        ("status", STATUSES, "Kayıt durumu"),
    ):
        value = form.get(name, "")
        if value not in options:
            errors[name] = f"{label} seçiniz."
        data[name] = value

    data["description"] = text("description", MAX_TEXT)
    if not data["description"]:
        errors["description"] = "Sorunun açıklamasını giriniz."
    data["resolution"] = text("resolution", MAX_TEXT) or None

    raw_duration = form.get("duration_minutes", "").strip()
    duration = None
    if raw_duration:
        try:
            duration = int(raw_duration)
            if not 0 < duration <= MAX_DURATION_MINUTES:
                raise ValueError
        except ValueError:
            errors["duration_minutes"] = f"İşlem süresi 1 ile {MAX_DURATION_MINUTES} dakika arasında bir tam sayı olmalıdır."
            duration = None
    if duration is None and data.get("status") in DONE_STATUSES and "duration_minutes" not in errors:
        errors["duration_minutes"] = "Çözülen / kapatılan kayıt için işlem süresini giriniz."
    data["duration_minutes"] = duration
    return data, errors


def next_seq(year):
    return (db.session.execute(db.select(func.max(T.seq)).where(T.year == year)).scalar() or 0) + 1


def create_ticket(data, user, created_at=None, is_demo=False):
    """Yeni kaydı numaralandırarak kaydeder. Aynı anda iki kayıt numara çakışırsa yeniden dener."""
    created_at = created_at or datetime.now()
    for _ in range(5):
        seq = next_seq(created_at.year)
        ticket = T(
            ticket_no=f"{created_at.year}-{seq:05d}",
            year=created_at.year,
            seq=seq,
            created_at=created_at,
            created_by_id=user.id,
            is_demo=is_demo,
            **data,
        )
        if ticket.status in DONE_STATUSES:
            ticket.resolved_at = created_at
        db.session.add(ticket)
        try:
            db.session.flush()
        except IntegrityError:
            db.session.rollback()
            continue
        log_action(user, "ticket", ticket.id, "create", at=created_at)
        db.session.commit()
        return ticket
    raise RuntimeError("Kayıt numarası oluşturulamadı.")


def apply_status(ticket, new_status):
    """Durum değişikliğine bağlı alanları günceller."""
    if new_status in DONE_STATUSES and ticket.status not in DONE_STATUSES:
        ticket.resolved_at = datetime.now()
    elif new_status not in DONE_STATUSES:
        ticket.resolved_at = None
    ticket.status = new_status


def default_project_id(user):
    """Personelin son kullandığı aktif proje varsayılan seçilir (daha az tıklama)."""
    last = db.session.execute(
        db.select(T.project_id).join(Project).where(T.created_by_id == user.id, Project.active.is_(True))
        .order_by(T.created_at.desc()).limit(1)
    ).scalar()
    return last


# --------------------------------------------------------------------------- #
# Sayfalar
# --------------------------------------------------------------------------- #

@bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    errors = {}
    if request.method == "POST":
        data, errors = parse_ticket_form(request.form)
        if not errors:
            ticket = create_ticket(data, current_user)
            if request.form.get("save_and_similar"):
                # Aynı özelliklerle yeni kayıt: yalnızca talep sahibi değiştirilir
                flash(f"{ticket.ticket_no} numaralı kayıt oluşturuldu. Benzer kayıt için yeni talep sahibini giriniz.",
                      "success")
                return redirect(url_for("tickets.new", kopya=ticket.id))
            if request.form.get("save_and_new"):
                flash(f"{ticket.ticket_no} numaralı kayıt oluşturuldu.", "success")
                return redirect(url_for("tickets.new", project_id=ticket.project_id))
            flash(f"{ticket.ticket_no} numaralı kayıt oluşturuldu.", "success")
            return redirect(url_for("tickets.detail", ticket_id=ticket.id))
        flash("Lütfen işaretli alanları kontrol ediniz.", "danger")
        values = request.form
        copied_from = None
    elif request.args.get("kopya", type=int):
        # Benzer kayıt: kaynak kaydın alanları, talep sahibi boş
        copied_from = get_ticket_or_404(request.args.get("kopya", type=int))
        values = {f: "" if getattr(copied_from, f) is None else str(getattr(copied_from, f)) for f in COPY_FIELDS}
    else:
        copied_from = None
        values = {
            "project_id": str(request.args.get("project_id", type=int) or default_project_id(current_user) or ""),
            "channel": CHANNEL_PHONE,
            "priority": PRIORITY_NORMAL,
            "status": STATUS_OPEN,
        }
    return render_template(
        "tickets/form.html", ticket=None, values=values, errors=errors, copied_from=copied_from,
        projects=active_projects(), categories=active_categories(),
        source_hints=SOURCE_HINTS, quick_durations=QUICK_DURATIONS, now=datetime.now(),
    ), (400 if errors else 200)


@bp.route("/")
@login_required
def index():
    filters = TicketFilters.from_args(request.args)
    page = request.args.get("page", 1, type=int)
    pagination = db.paginate(
        ticket_query(filters.conditions(current_user)),
        page=page, per_page=current_app.config["TICKETS_PER_PAGE"], error_out=False,
    )
    users = db.session.execute(db.select(User).order_by(User.full_name)).scalars().all() if current_user.is_admin else []
    return render_template(
        "tickets/list.html", pagination=pagination, filters=filters, users=users,
        projects=db.session.execute(db.select(Project).order_by(Project.sort_order, Project.id)).scalars().all(),
        categories=db.session.execute(db.select(Category).order_by(Category.sort_order, Category.name)).scalars().all(),
        status_groups=STATUS_GROUPS,
    )


@bp.route("/<int:ticket_id>")
@login_required
def detail(ticket_id):
    ticket = get_ticket_or_404(ticket_id)
    history = db.session.execute(
        db.select(AuditLog).where(AuditLog.entity_type == "ticket", AuditLog.entity_id == ticket.id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    ).scalars().all()
    return render_template("tickets/detail.html", ticket=ticket, history=history,
                           done_statuses=DONE_STATUSES)


@bp.route("/<int:ticket_id>/edit", methods=["GET", "POST"])
@login_required
def edit(ticket_id):
    ticket = get_ticket_or_404(ticket_id)
    if ticket.archived:
        flash("Arşivlenmiş kayıt düzenlenemez. Önce arşivden çıkarınız.", "warning")
        return redirect(url_for("tickets.detail", ticket_id=ticket.id))

    errors = {}
    if request.method == "POST":
        data, errors = parse_ticket_form(request.form, ticket)
        if not errors:
            changes = {}
            for field in EDITABLE_FIELDS:
                old, new_value = getattr(ticket, field), data[field]
                if old != new_value:
                    changes[FIELD_LABELS[field]] = [display_value(field, old), display_value(field, new_value)]
            if changes:
                status_changed = ticket.status != data["status"]
                apply_status(ticket, data.pop("status"))
                for field, value in data.items():
                    setattr(ticket, field, value)
                ticket.updated_at = datetime.now()
                ticket.updated_by_id = current_user.id
                log_action(current_user, "ticket", ticket.id, "status" if status_changed and len(changes) == 1 else "update", changes)
                db.session.commit()
                flash("Kayıt güncellendi.", "success")
            else:
                flash("Değişiklik yapılmadı.", "info")
            return redirect(url_for("tickets.detail", ticket_id=ticket.id))
        flash("Lütfen işaretli alanları kontrol ediniz.", "danger")
        values = request.form
    else:
        values = {field: "" if getattr(ticket, field) is None else str(getattr(ticket, field))
                  for field in EDITABLE_FIELDS}
    return render_template(
        "tickets/form.html", ticket=ticket, values=values, errors=errors,
        projects=active_projects(ticket.project_id), categories=active_categories(ticket.category_id),
        source_hints=SOURCE_HINTS, quick_durations=QUICK_DURATIONS, now=ticket.created_at,
    ), (400 if errors else 200)


@bp.route("/<int:ticket_id>/status", methods=["POST"])
@login_required
def change_status(ticket_id):
    """Detay ekranındaki hızlı durum düğmeleri (yeniden açma dahil)."""
    ticket = get_ticket_or_404(ticket_id)
    if ticket.archived:
        abort(400, description="Arşivlenmiş kaydın durumu değiştirilemez.")
    new_status = request.form.get("status", "")
    if new_status not in STATUSES:
        abort(400, description="Geçersiz durum.")
    if new_status == ticket.status:
        return redirect(url_for("tickets.detail", ticket_id=ticket.id))

    changes = {}
    if new_status in DONE_STATUSES and ticket.duration_minutes is None:
        try:
            duration = int(request.form.get("duration_minutes", ""))
            if not 0 < duration <= MAX_DURATION_MINUTES:
                raise ValueError
        except ValueError:
            flash("Kaydı çözüldü / kapatıldı olarak işaretlemek için işlem süresini giriniz.", "danger")
            return redirect(url_for("tickets.detail", ticket_id=ticket.id))
        changes[FIELD_LABELS["duration_minutes"]] = ["-", str(duration)]
        ticket.duration_minutes = duration

    changes[FIELD_LABELS["status"]] = [ticket.status_label, STATUSES[new_status]]
    apply_status(ticket, new_status)
    ticket.updated_at = datetime.now()
    ticket.updated_by_id = current_user.id
    log_action(current_user, "ticket", ticket.id, "status", changes)
    db.session.commit()
    flash(f"Durum güncellendi: {STATUSES[new_status]}", "success")
    return redirect(url_for("tickets.detail", ticket_id=ticket.id))


@bp.route("/<int:ticket_id>/archive", methods=["POST"])
@admin_required
def archive(ticket_id):
    """Kayıtlar silinmez; yönetici arşivleyebilir veya arşivden çıkarabilir."""
    ticket = get_ticket_or_404(ticket_id)
    restore = request.form.get("restore") == "1"
    if restore and ticket.archived:
        ticket.archived, ticket.archived_at, ticket.archived_by_id = False, None, None
        log_action(current_user, "ticket", ticket.id, "restore")
        flash("Kayıt arşivden çıkarıldı.", "success")
    elif not restore and not ticket.archived:
        ticket.archived, ticket.archived_at, ticket.archived_by_id = True, datetime.now(), current_user.id
        log_action(current_user, "ticket", ticket.id, "archive")
        flash("Kayıt arşivlendi. Arşivdeki kayıtlar istatistiklere dahil edilmez.", "success")
    db.session.commit()
    return redirect(url_for("tickets.detail", ticket_id=ticket.id))
