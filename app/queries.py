"""Kayıt filtreleri ve istatistik sorguları.

Kayıt listesi, istatistik sayfası, dashboard ve Excel çıktısı aynı filtre
mantığını kullanır; böylece ekranda görülen sayı ile Excel'deki satır sayısı
her zaman eşleşir.
"""
from dataclasses import dataclass, fields
from datetime import date, datetime, timedelta

from sqlalchemy import case, func, or_

from .constants import (
    DONE_STATUSES, PENDING_STATUSES, SOURCE_SYSTEM, SOURCE_USER, SOURCES, STATUSES,
)
from .extensions import db
from . import tr_lower
from .models import Category, Project, SupportTicket as T, User

# Durum filtresinde tekil durumlara ek olarak iki grup seçeneği
STATUS_GROUPS = {
    "pending": ("Açık / Bekleyen", PENDING_STATUSES),
    "done": ("Çözülen (Çözüldü + Kapatıldı)", DONE_STATUSES),
}

PERIODS = {
    "day": "Günlük",
    "week": "Haftalık",
    "month": "Aylık",
    "custom": "Özel Aralık",
}


def parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date() if value else None
    except ValueError:
        return None


def parse_int(value):
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def period_range(period, today=None):
    """Seçilen döneme göre (başlangıç, bitiş) tarihlerini döndürür. Hafta pazartesi başlar."""
    today = today or date.today()
    if period == "week":
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=6)
    if period == "month":
        start = today.replace(day=1)
        next_month = (start + timedelta(days=32)).replace(day=1)
        return start, next_month - timedelta(days=1)
    return today, today


def previous_range(date_from, date_to, period=None):
    """Karşılaştırma için bir önceki dönem (aynı uzunlukta).

    Aylık dönemde önceki ayın aynı günleri alınır: 1-15 Ekim için 1-15 Eylül.
    """
    if period == "month":
        prev_start = (date_from - timedelta(days=1)).replace(day=1)
        prev_end = min(prev_start + (date_to - date_from), date_from - timedelta(days=1))
        return prev_start, prev_end
    length = (date_to - date_from).days + 1
    return date_from - timedelta(days=length), date_from - timedelta(days=1)


@dataclass
class TicketFilters:
    q: str = ""
    date_from: date = None
    date_to: date = None
    project_id: int = None
    user_id: int = None
    source: str = ""
    category_id: int = None
    status: str = ""
    archived: str = ""   # "" = arşivlenmemiş, "1" = yalnızca arşiv (sadece yönetici)

    @classmethod
    def from_args(cls, args):
        source = args.get("source", "")
        status = args.get("status", "")
        return cls(
            q=args.get("q", "").strip()[:100],
            date_from=parse_date(args.get("date_from")),
            date_to=parse_date(args.get("date_to")),
            project_id=parse_int(args.get("project_id")),
            user_id=parse_int(args.get("user_id")),
            source=source if source in SOURCES else "",
            category_id=parse_int(args.get("category_id")),
            status=status if status in STATUSES or status in STATUS_GROUPS else "",
            archived="1" if args.get("archived") == "1" else "",
        )

    def to_args(self, **overrides):
        """URL parametresi olarak kullanılabilecek sözlük (boş değerler hariç)."""
        out = {}
        for f in fields(self):
            value = overrides.get(f.name, getattr(self, f.name))
            if value in (None, ""):
                continue
            out[f.name] = value.isoformat() if isinstance(value, date) else value
        return out

    def conditions(self, user, include_archived_filter=True):
        """SQLAlchemy WHERE koşulları. Personel her zaman yalnızca kendi kayıtlarını görür."""
        conds = []
        if not user.is_admin:
            conds.append(T.created_by_id == user.id)
            conds.append(T.archived.is_(False))
        else:
            if self.user_id:
                conds.append(T.created_by_id == self.user_id)
            if include_archived_filter:
                conds.append(T.archived.is_(self.archived == "1"))
            else:
                conds.append(T.archived.is_(False))

        if self.date_from:
            conds.append(T.created_at >= datetime.combine(self.date_from, datetime.min.time()))
        if self.date_to:
            conds.append(T.created_at < datetime.combine(self.date_to + timedelta(days=1), datetime.min.time()))
        if self.project_id:
            conds.append(T.project_id == self.project_id)
        if self.source:
            conds.append(T.source == self.source)
        if self.category_id:
            conds.append(T.category_id == self.category_id)
        if self.status in STATUS_GROUPS:
            conds.append(T.status.in_(STATUS_GROUPS[self.status][1]))
        elif self.status:
            conds.append(T.status == self.status)
        if self.q:
            # Türkçe büyük/küçük harf duyarsız arama (tr_lower: bkz. app/__init__.py)
            like = "%" + tr_lower(self.q).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            conds.append(or_(*(
                func.tr_lower(col).like(like, escape="\\")
                for col in (T.ticket_no, T.requester_name, T.requester_phone, T.description, T.resolution)
            )))
        return conds


def stat_conditions(filters, user):
    """İstatistikler arşivlenmiş kayıtları hiçbir zaman saymaz."""
    return filters.conditions(user, include_archived_filter=False)


def ticket_query(conds):
    return (
        db.select(T)
        .where(*conds)
        .options(db.joinedload(T.project), db.joinedload(T.category), db.joinedload(T.created_by))
        .order_by(T.created_at.desc(), T.id.desc())
    )


# --------------------------------------------------------------------------- #
# İstatistik sorguları
# --------------------------------------------------------------------------- #

def _done_case():
    return func.sum(case((T.status.in_(DONE_STATUSES), 1), else_=0))


def _pending_case():
    return func.sum(case((T.status.in_(PENDING_STATUSES), 1), else_=0))


def summary(conds):
    """Temel sayılar: toplam, kaynak ayrımı, çözülen, bekleyen, süreler."""
    row = db.session.execute(
        db.select(
            func.count(T.id),
            func.sum(case((T.source == SOURCE_SYSTEM, 1), else_=0)),
            func.sum(case((T.source == SOURCE_USER, 1), else_=0)),
            _done_case(),
            _pending_case(),
            func.avg(T.duration_minutes),
            func.sum(T.duration_minutes),
        ).where(*conds)
    ).one()
    total = row[0] or 0
    system, user = row[1] or 0, row[2] or 0
    return {
        "total": total,
        "system": system,
        "user": user,
        "system_pct": percent(system, total),
        "user_pct": percent(user, total),
        "done": row[3] or 0,
        "pending": row[4] or 0,
        "avg_duration": round(row[5], 1) if row[5] is not None else None,
        "total_duration": row[6] or 0,
    }


def percent(part, total):
    return round(part * 100 / total, 1) if total else 0.0


def change_pct(current, previous):
    if not previous:
        return None
    return round((current - previous) * 100 / previous, 1)


def by_project(conds):
    """Proje bazlı kayıt sayısı. Aktif projeler kayıt olmasa da 0 ile listelenir."""
    counts = dict(db.session.execute(
        db.select(T.project_id, func.count(T.id)).where(*conds).group_by(T.project_id)
    ).all())
    projects = db.session.execute(db.select(Project).order_by(Project.sort_order, Project.id)).scalars()
    total = sum(counts.values())
    rows = []
    for p in projects:
        if p.active or p.id in counts:
            n = counts.get(p.id, 0)
            rows.append({"id": p.id, "name": p.name, "count": n, "pct": percent(n, total), "active": p.active})
    return rows


def by_user(conds):
    """Personel iş yükü: kayıt, çözülen, bekleyen, toplam süre."""
    result = db.session.execute(
        db.select(
            T.created_by_id,
            func.count(T.id),
            _done_case(),
            _pending_case(),
            func.coalesce(func.sum(T.duration_minutes), 0),
            func.avg(T.duration_minutes),
        ).where(*conds).group_by(T.created_by_id)
    ).all()
    stats = {r[0]: r for r in result}
    users = db.session.execute(db.select(User).order_by(User.full_name)).scalars()
    rows = []
    for u in users:
        r = stats.get(u.id)
        # Kaydı olmayan aktif personel de iş yükü tablosunda 0 olarak görünür
        if r is None and not (u.active and not u.is_admin):
            continue
        rows.append({
            "id": u.id,
            "name": u.full_name,
            "active": u.active,
            "total": r[1] if r else 0,
            "done": (r[2] or 0) if r else 0,
            "pending": (r[3] or 0) if r else 0,
            "duration": r[4] if r else 0,
            "avg_duration": round(r[5], 1) if r and r[5] is not None else None,
        })
    rows.sort(key=lambda x: (-x["total"], x["name"]))
    return rows


def by_category(conds):
    """Sorun kategorisi dağılımı (çoktan aza), kaynak ayrımıyla birlikte."""
    result = db.session.execute(
        db.select(
            Category.id, Category.name, func.count(T.id),
            func.sum(case((T.source == SOURCE_SYSTEM, 1), else_=0)),
            func.sum(case((T.source == SOURCE_USER, 1), else_=0)),
        )
        .join(T, T.category_id == Category.id)
        .where(*conds)
        .group_by(Category.id, Category.name)
        .order_by(func.count(T.id).desc(), Category.name)
    ).all()
    total = sum(r[2] for r in result)
    return [
        {"id": r[0], "name": r[1], "count": r[2], "system": r[3] or 0, "user": r[4] or 0,
         "pct": percent(r[2], total)}
        for r in result
    ]


def by_day(conds, date_from, date_to, max_days=93):
    """Günlere göre kayıt sayısı (kaynak ayrımıyla). Boş günler 0 olarak doldurulur."""
    if not date_from or not date_to or date_to < date_from:
        return None
    if (date_to - date_from).days >= max_days:
        date_from = date_to - timedelta(days=max_days - 1)
    day_col = func.date(T.created_at)
    result = db.session.execute(
        db.select(
            day_col,
            func.sum(case((T.source == SOURCE_SYSTEM, 1), else_=0)),
            func.sum(case((T.source == SOURCE_USER, 1), else_=0)),
        ).where(*conds).group_by(day_col)
    ).all()
    data = {str(r[0]): (r[1] or 0, r[2] or 0) for r in result}
    labels, system, user = [], [], []
    d = date_from
    while d <= date_to:
        s, u = data.get(d.isoformat(), (0, 0))
        labels.append(d.strftime("%d.%m"))
        system.append(s)
        user.append(u)
        d += timedelta(days=1)
    return {"labels": labels, "system": system, "user": user}
