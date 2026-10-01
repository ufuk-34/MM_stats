"""Yönetim: projeler, kategoriler, personel ve sistem ayarları (yalnızca yönetici)."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from .auth import admin_required, validate_password
from .constants import ROLE_ADMIN, ROLES
from .demo import clear_demo, demo_counts
from .extensions import db
from .models import Category, Project, Setting, SupportTicket as T, User, log_action

bp = Blueprint("admin", __name__, url_prefix="/admin")

# Proje ve kategori aynı basit yapıya sahiptir: ad, sıra, aktif/pasif
NAMED_MODELS = {
    "projects": (Project, "project", "Proje", T.project_id),
    "categories": (Category, "category", "Kategori", T.category_id),
}


@bp.route("/")
@admin_required
def index():
    return redirect(url_for("admin.named_list", kind="projects"))


@bp.route("/<any(projects, categories):kind>", methods=["GET", "POST"])
@admin_required
def named_list(kind):
    model, entity_type, label, ticket_fk = NAMED_MODELS[kind]
    if request.method == "POST":
        name = request.form.get("name", "").strip()[:150]
        if not name:
            flash(f"{label} adı boş olamaz.", "danger")
        elif _name_taken(model, name):
            flash(f"Bu isimde bir {label.lower()} zaten var.", "danger")
        else:
            max_order = db.session.execute(db.select(db.func.max(model.sort_order))).scalar() or 0
            item = model(name=name, sort_order=max_order + 1)
            db.session.add(item)
            db.session.flush()
            log_action(current_user, entity_type, item.id, "create", {"Ad": ["-", name]})
            db.session.commit()
            flash(f"{label} eklendi: {name}", "success")
        return redirect(url_for("admin.named_list", kind=kind))

    items = db.session.execute(db.select(model).order_by(model.sort_order, model.id)).scalars().all()
    usage = dict(db.session.execute(db.select(ticket_fk, db.func.count(T.id)).group_by(ticket_fk)).all())
    return render_template("admin/named_list.html", kind=kind, label=label, items=items, usage=usage)


@bp.route("/<any(projects, categories):kind>/<int:item_id>", methods=["POST"])
@admin_required
def named_update(kind, item_id):
    model, entity_type, label, _ = NAMED_MODELS[kind]
    item = db.session.get(model, item_id) or abort(404)
    name = request.form.get("name", "").strip()[:150]
    sort_order = request.form.get("sort_order", type=int)
    active = request.form.get("active") == "1"

    if not name:
        flash(f"{label} adı boş olamaz.", "danger")
        return redirect(url_for("admin.named_list", kind=kind))
    if name != item.name and _name_taken(model, name, exclude_id=item.id):
        flash(f"Bu isimde bir {label.lower()} zaten var.", "danger")
        return redirect(url_for("admin.named_list", kind=kind))

    changes = {}
    if name != item.name:
        changes["Ad"] = [item.name, name]
        item.name = name
    if sort_order is not None and sort_order != item.sort_order:
        changes["Sıra"] = [str(item.sort_order), str(sort_order)]
        item.sort_order = sort_order
    if active != item.active:
        changes["Durum"] = ["Aktif" if item.active else "Pasif", "Aktif" if active else "Pasif"]
        item.active = active
    if changes:
        log_action(current_user, entity_type, item.id, "update", changes)
        db.session.commit()
        flash(f"{label} güncellendi.", "success")
    return redirect(url_for("admin.named_list", kind=kind))


def _name_taken(model, name, exclude_id=None):
    q = db.select(model.id).where(db.func.lower(model.name) == name.lower())
    if exclude_id:
        q = q.where(model.id != exclude_id)
    return db.session.execute(q).first() is not None


# --------------------------------------------------------------------------- #
# Personel
# --------------------------------------------------------------------------- #

@bp.route("/users", methods=["GET", "POST"])
@admin_required
def users():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        full_name = request.form.get("full_name", "").strip()[:100]
        role = request.form.get("role", "")
        password = request.form.get("password", "")
        error = validate_password(password, request.form.get("password2", ""))
        if not username or not full_name:
            error = "Kullanıcı adı ve ad soyad zorunludur."
        elif not username.replace(".", "").replace("_", "").replace("-", "").isalnum() or len(username) > 50:
            error = "Kullanıcı adı yalnızca harf, rakam, nokta, alt çizgi ve tire içerebilir."
        elif role not in ROLES:
            error = "Rol seçiniz."
        elif db.session.execute(db.select(User.id).filter_by(username=username)).first():
            error = "Bu kullanıcı adı zaten kullanılıyor."
        if error:
            flash(error, "danger")
        else:
            user = User(username=username, full_name=full_name, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.flush()
            log_action(current_user, "user", user.id, "create", {"Kullanıcı": ["-", f"{full_name} ({username})"]})
            db.session.commit()
            flash(f"Kullanıcı eklendi: {full_name}", "success")
            return redirect(url_for("admin.users"))

    items = db.session.execute(db.select(User).order_by(User.active.desc(), User.full_name)).scalars().all()
    return render_template("admin/users.html", items=items, form=request.form)


@bp.route("/users/<int:user_id>", methods=["GET", "POST"])
@admin_required
def user_edit(user_id):
    user = db.session.get(User, user_id) or abort(404)
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()[:100]
        role = request.form.get("role", "")
        active = request.form.get("active") == "1"
        password = request.form.get("password", "")

        error = None
        if not full_name:
            error = "Ad soyad zorunludur."
        elif role not in ROLES:
            error = "Rol seçiniz."
        elif user.id == current_user.id and (role != ROLE_ADMIN or not active):
            error = "Kendi yönetici yetkinizi kaldıramaz veya kendinizi pasife alamazsınız."
        elif password:
            error = validate_password(password, request.form.get("password2", ""))
        if error:
            flash(error, "danger")
            return render_template("admin/user_edit.html", user=user), 400

        changes = {}
        if full_name != user.full_name:
            changes["Ad Soyad"] = [user.full_name, full_name]
            user.full_name = full_name
        if role != user.role:
            changes["Rol"] = [ROLES[user.role], ROLES[role]]
            user.role = role
        if active != user.active:
            changes["Durum"] = ["Aktif" if user.active else "Pasif", "Aktif" if active else "Pasif"]
            user.active = active
        if password:
            changes["Şifre"] = ["", "Yönetici tarafından değiştirildi"]
            user.set_password(password)
        if changes:
            log_action(current_user, "user", user.id, "update", changes)
            db.session.commit()
            flash("Kullanıcı güncellendi.", "success")
        return redirect(url_for("admin.users"))
    return render_template("admin/user_edit.html", user=user)


# --------------------------------------------------------------------------- #
# Sistem ayarları
# --------------------------------------------------------------------------- #

@bp.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "save":
            org_name = request.form.get("org_name", "").strip()[:100]
            if not org_name:
                flash("Kurum / uygulama adı boş olamaz.", "danger")
            else:
                old = Setting.get("org_name")
                if old != org_name:
                    Setting.set("org_name", org_name)
                    log_action(current_user, "setting", None, "update", {"Kurum adı": [old, org_name]})
                    db.session.commit()
                flash("Ayarlar kaydedildi.", "success")
        elif action == "clear_demo":
            if request.form.get("confirm") != "1":
                flash("Demo verileri temizlemek için onay kutusunu işaretleyiniz.", "warning")
            else:
                tickets, users_deleted, deactivated = clear_demo()
                log_action(current_user, "setting", None, "update",
                           {"Demo veriler": ["", f"{tickets} kayıt, {users_deleted} personel silindi"]})
                db.session.commit()
                flash(f"Demo veriler temizlendi: {tickets} kayıt, {users_deleted} personel silindi"
                      + (f", {deactivated} personel pasife alındı." if deactivated else "."), "success")
        return redirect(url_for("admin.settings"))

    demo_tickets, demo_users = demo_counts()
    return render_template("admin/settings.html", demo_tickets=demo_tickets, demo_users=demo_users)
