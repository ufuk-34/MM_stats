"""İstatistikler sayfası: günlük, haftalık, aylık veya özel tarih aralığı."""
from datetime import date, timedelta

from flask import Blueprint, render_template, request
from flask_login import current_user, login_required

from .extensions import db
from .models import Category, Project, User
from .queries import (
    PERIODS, STATUS_GROUPS, TicketFilters, by_category, by_day, by_project, by_user, change_pct,
    parse_date, period_range, previous_range, stat_conditions, summary,
)

bp = Blueprint("stats", __name__, url_prefix="/stats")


def resolve_period(args):
    """URL parametrelerinden dönem ve tarih aralığını belirler."""
    period = args.get("period", "month")
    if period not in PERIODS:
        period = "month"
    if period == "custom":
        date_from = parse_date(args.get("date_from")) or date.today().replace(day=1)
        date_to = parse_date(args.get("date_to")) or date.today()
        if date_to < date_from:
            date_from, date_to = date_to, date_from
        return period, date_from, date_to, None
    ref = parse_date(args.get("ref")) or date.today()
    date_from, date_to = period_range(period, ref)
    return period, date_from, date_to, ref


def shift_ref(period, ref, direction):
    """Önceki / sonraki dönem için referans tarih."""
    if period == "day":
        return ref + timedelta(days=direction)
    if period == "week":
        return ref + timedelta(weeks=direction)
    start = ref.replace(day=1)
    if direction < 0:
        return (start - timedelta(days=1)).replace(day=1)
    return (start + timedelta(days=32)).replace(day=1)


@bp.route("/")
@login_required
def index():
    period, date_from, date_to, ref = resolve_period(request.args)
    filters = TicketFilters.from_args(request.args)
    filters.date_from, filters.date_to = date_from, date_to
    if not current_user.is_admin:
        filters.user_id = None
    conds = stat_conditions(filters, current_user)

    stats = summary(conds)
    # Devam eden dönem bugüne kadar olan kısmıyla, önceki dönemin aynı uzunluktaki kısmıyla karşılaştırılır
    cmp_to = min(date_to, date.today()) if date_from <= date.today() else date_to
    prev_from, prev_to = previous_range(date_from, cmp_to, period)
    prev_filters = TicketFilters(**{**filters.__dict__, "date_from": prev_from, "date_to": prev_to})
    prev_total = summary(stat_conditions(prev_filters, current_user))["total"]

    projects = by_project(conds)
    categories = by_category(conds)
    days = by_day(conds, date_from, date_to)
    workload = by_user(conds) if current_user.is_admin else None

    nav = None
    if ref:
        nav = {"prev": shift_ref(period, ref, -1).isoformat(), "next": shift_ref(period, ref, 1).isoformat()}

    return render_template(
        "stats/index.html",
        period=period, periods=PERIODS, date_from=date_from, date_to=date_to, nav=nav,
        filters=filters, stats=stats,
        prev={"from": prev_from, "to": prev_to, "total": prev_total, "change": change_pct(stats["total"], prev_total)},
        projects=projects, categories=categories, workload=workload,
        users=db.session.execute(db.select(User).order_by(User.full_name)).scalars().all() if current_user.is_admin else [],
        all_projects=db.session.execute(db.select(Project).order_by(Project.sort_order, Project.id)).scalars().all(),
        all_categories=db.session.execute(db.select(Category).order_by(Category.sort_order, Category.name)).scalars().all(),
        status_groups=STATUS_GROUPS,
        chart_data={
            "projects": {"labels": [p["name"] for p in projects], "values": [p["count"] for p in projects]},
            "source": {"system": stats["system"], "user": stats["user"]},
            "days": days,
            "categories": {"labels": [c["name"] for c in categories], "values": [c["count"] for c in categories]},
        },
        list_args=filters.to_args(),
        nav_args=filters.to_args(date_from=None, date_to=None),
    )
