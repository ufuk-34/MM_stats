"""Ana ekran: seçilen döneme ait özet sayılar, dağılımlar ve son kayıtlar."""
from datetime import date, timedelta

from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .constants import MONTHS_TR, PENDING_STATUSES
from .extensions import db
from .models import SupportTicket as T
from .queries import (
    TicketFilters, by_category, by_project, by_user, change_pct, period_range, stat_conditions,
    summary, ticket_query,
)

bp = Blueprint("dashboard", __name__)

DASHBOARD_PERIODS = {"day": "Bugün", "week": "Bu Hafta", "month": "Bu Ay"}


@bp.route("/")
@login_required
def index():
    period = request.args.get("period", "day")
    if period not in DASHBOARD_PERIODS:
        return redirect(url_for("dashboard.index"))
    today = date.today()
    date_from, date_to = period_range(period, today)
    filters = TicketFilters(date_from=date_from, date_to=date_to)
    conds = stat_conditions(filters, current_user)

    # Tarihten bağımsız toplam bekleyen iş (tüm zamanlar)
    all_conds = stat_conditions(TicketFilters(), current_user)
    backlog = db.session.execute(
        db.select(db.func.count(T.id)).where(*all_conds, T.status.in_(PENDING_STATUSES))
    ).scalar()

    # Bu ay ile geçen ayın aynı dönemi (1. günden bugünün gün sayısına kadar)
    month_start = today.replace(day=1)
    prev_month_end = month_start - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)
    prev_same_day = prev_month_start + timedelta(days=min(today.day, prev_month_end.day) - 1)
    this_month = summary(stat_conditions(TicketFilters(date_from=month_start, date_to=today), current_user))["total"]
    prev_month_same = summary(stat_conditions(
        TicketFilters(date_from=prev_month_start, date_to=prev_same_day), current_user))["total"]
    prev_month_full = summary(stat_conditions(
        TicketFilters(date_from=prev_month_start, date_to=prev_month_end), current_user))["total"]

    projects = by_project(conds)
    categories = by_category(conds)
    stats = summary(conds)
    recent = db.session.execute(ticket_query(all_conds).limit(10)).unique().scalars().all()

    return render_template(
        "dashboard.html",
        period=period, periods=DASHBOARD_PERIODS, date_from=date_from, date_to=date_to,
        stats=stats, backlog=backlog,
        projects=projects, categories=categories[:5],
        workload=by_user(conds) if current_user.is_admin else None,
        recent=recent,
        month={
            "current": this_month, "prev_same": prev_month_same, "prev_full": prev_month_full,
            "change": change_pct(this_month, prev_month_same),
            "label": f"1–{today.day} {MONTHS_TR[today.month]}",
            "prev_label": f"1–{prev_same_day.day} {MONTHS_TR[prev_month_start.month]}",
            "prev_name": MONTHS_TR[prev_month_start.month],
        },
        chart_data={
            "source": {"system": stats["system"], "user": stats["user"]},
        },
        filter_args=filters.to_args(),
    )

