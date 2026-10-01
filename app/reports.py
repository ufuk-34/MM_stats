"""Raporlar: filtrelenmiş kayıtların grafikli Excel raporu olarak aktarılması (yalnızca yönetici)."""
from datetime import date, datetime
from io import BytesIO

from flask import Blueprint, render_template, request, send_file
from flask_login import current_user

from .auth import admin_required
from .excel_report import build_report_workbook
from .extensions import db
from .models import Category, Project, Setting, User
from .queries import STATUS_GROUPS, TicketFilters, stat_conditions, summary
from .constants import SOURCES, STATUSES

bp = Blueprint("reports", __name__, url_prefix="/reports")


@bp.route("/")
@admin_required
def index():
    filters = TicketFilters.from_args(request.args)
    if not request.args:
        # Varsayılan: bu ayın kayıtları
        filters.date_from, filters.date_to = date.today().replace(day=1), date.today()
    count = summary(filters.conditions(current_user))["total"]
    return render_template(
        "reports/index.html", filters=filters, count=count, status_groups=STATUS_GROUPS,
        users=db.session.execute(db.select(User).order_by(User.full_name)).scalars().all(),
        projects=db.session.execute(db.select(Project).order_by(Project.sort_order, Project.id)).scalars().all(),
        categories=db.session.execute(db.select(Category).order_by(Category.sort_order, Category.name)).scalars().all(),
    )


def filter_description(filters):
    """Tarih dışındaki filtrelerin okunur özeti (tarih aralığı raporda ayrıca yazılır)."""
    parts = []
    if filters.project_id:
        p = db.session.get(Project, filters.project_id)
        parts.append(f"Proje: {p.name if p else '-'}")
    if filters.user_id:
        u = db.session.get(User, filters.user_id)
        parts.append(f"Personel: {u.full_name if u else '-'}")
    if filters.source:
        parts.append(f"Sorun kaynağı: {SOURCES[filters.source]}")
    if filters.category_id:
        c = db.session.get(Category, filters.category_id)
        parts.append(f"Kategori: {c.name if c else '-'}")
    if filters.status:
        label = STATUS_GROUPS[filters.status][0] if filters.status in STATUS_GROUPS else STATUSES[filters.status]
        parts.append(f"Durum: {label}")
    if filters.q:
        parts.append(f"Arama: {filters.q}")
    if filters.archived:
        parts.append("Yalnızca arşivlenmiş kayıtlar")
    return "; ".join(parts) or "Ek filtre yok"


def period_description(filters):
    if not filters.date_from and not filters.date_to:
        return "Tüm tarihler"
    d1 = filters.date_from.strftime("%d.%m.%Y") if filters.date_from else "…"
    d2 = filters.date_to.strftime("%d.%m.%Y") if filters.date_to else "…"
    return d1 if d1 == d2 else f"{d1} – {d2}"


def build_workbook(filters, user):
    """Grafikli Excel raporu (bkz. excel_report.py)."""
    conds = filters.conditions(user)
    stat_conds = conds if filters.archived else stat_conditions(filters, user)
    return build_report_workbook(
        filters, user, conds, stat_conds,
        org_name=Setting.get("org_name"),
        period_text=period_description(filters),
        filter_text="Filtreler: " + filter_description(filters),
    )


@bp.route("/export")
@admin_required
def export():
    filters = TicketFilters.from_args(request.args)
    wb, _ = build_workbook(filters, current_user)
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"destek_raporu_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(
        buf, as_attachment=True, download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
