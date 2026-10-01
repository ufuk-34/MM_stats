"""Demo / test verisi oluşturma ve temizleme.

Demo kayıtlar ve demo personeller `is_demo=True` olarak işaretlenir; böylece
gerçek kayıtlara dokunmadan tek komutla temizlenebilir.
"""
import random
from datetime import date, datetime, time, timedelta

from .constants import (
    CHANNELS, DEFAULT_CATEGORIES, DEFAULT_PROJECTS, DONE_STATUSES, ROLE_STAFF, SOURCE_SYSTEM,
    SOURCE_USER, STATUS_CLOSED, STATUS_IN_REVIEW, STATUS_OPEN, STATUS_RESOLVED,
)
from .extensions import db
from .models import AuditLog, Category, Project, SupportTicket as T, User

DEMO_PASSWORD = "Demo.12345"
DEMO_STAFF = [
    ("demo.ayse", "Ayşe Demir"),
    ("demo.mehmet", "Mehmet Yılmaz"),
    ("demo.zeynep", "Zeynep Kaya"),
    ("demo.ali", "Ali Şahin"),
    ("demo.elif", "Elif Çelik"),
]
REQUESTERS = [
    "Ahmet Yıldız", "Fatma Arslan", "Mustafa Koç", "Emine Aydın", "Hüseyin Öztürk",
    "Hatice Polat", "İbrahim Kurt", "Zehra Erdem", "Hasan Güneş", "Merve Aksoy",
    "Osman Bulut", "Selin Tekin", "Murat Kılıç", "Gizem Uçar", "Burak Şimşek",
]
# (kategori, kaynak, açıklama, çözüm)
SCENARIOS = [
    ("Giriş / Oturum", SOURCE_SYSTEM, "Kullanıcı doğru bilgilerle giriş yapmasına rağmen sisteme erişemiyor.",
     "Oturum servisi kontrol edildi, önbellek temizlendi ve problem giderildi."),
    ("Giriş / Oturum", SOURCE_USER, "Kullanıcı şifresini unuttuğu için giriş yapamıyor.",
     "Şifre sıfırlama adımları anlatıldı, kullanıcı giriş yaptı."),
    ("Kullanıcı işlemleri", SOURCE_USER, "Başvuru kaydının nasıl tamamlanacağı soruldu.",
     "İşlem adımları telefonda birlikte uygulandı."),
    ("Veri girişi", SOURCE_USER, "Formda tarih alanı hatalı biçimde girildiği için kayıt kaydedilemiyor.",
     "Doğru tarih biçimi açıklandı, kayıt tamamlandı."),
    ("Veri girişi", SOURCE_SYSTEM, "Kaydedilen bilgiler listede eksik görünüyor.",
     "Veri senkronizasyonu yeniden çalıştırıldı, kayıtlar düzeldi."),
    ("Yetkilendirme", SOURCE_USER, "Kullanıcı yetkisi olmayan bir menüye erişmeye çalışıyor.",
     "Yetki talebi için izlenecek yol anlatıldı."),
    ("Yetkilendirme", SOURCE_SYSTEM, "Tanımlı yetkisine rağmen rapor ekranı açılmıyor.",
     "Rol tanımı güncellendi, ekran erişimi sağlandı."),
    ("Teknik hata", SOURCE_SYSTEM, "Belge yükleme sırasında hata mesajı alınıyor.",
     "Hata yazılım ekibine iletildi, geçici çözüm uygulandı."),
    ("Bağlantı problemi", SOURCE_SYSTEM, "Sistem sayfaları açılırken zaman aşımı yaşanıyor.",
     "Sunucu bağlantısı kontrol edildi, sorun giderildi."),
    ("Sistem performansı", SOURCE_SYSTEM, "Liste ekranları çok yavaş yükleniyor.",
     "Performans sorunu ilgili ekibe bildirildi."),
    ("Entegrasyon", SOURCE_SYSTEM, "Dış sistemden gelen bilgiler güncellenmiyor.",
     "Entegrasyon servisi yeniden başlatıldı."),
    ("Bilgi talebi", SOURCE_USER, "Raporun hangi menüden alınacağı soruldu.",
     "Menü yolu tarif edildi."),
    ("Diğer", SOURCE_USER, "Ekranda bir alanın ne anlama geldiği soruldu.",
     "Alan hakkında bilgi verildi."),
]


def ensure_base_data():
    """Başlangıç projeleri ve kategorileri yoksa oluşturur."""
    if db.session.execute(db.select(db.func.count(Project.id))).scalar() == 0:
        for i, name in enumerate(DEFAULT_PROJECTS, start=1):
            db.session.add(Project(name=name, sort_order=i))
    if db.session.execute(db.select(db.func.count(Category.id))).scalar() == 0:
        for i, name in enumerate(DEFAULT_CATEGORIES, start=1):
            db.session.add(Category(name=name, sort_order=i))
    db.session.commit()


def seed_demo(count=45, days=60, rng_seed=2026):
    """5 demo personel ve `count` adet demo destek kaydı oluşturur."""
    from .tickets import create_ticket  # döngüsel import olmaması için

    ensure_base_data()
    rng = random.Random(rng_seed)

    staff = []
    for username, full_name in DEMO_STAFF:
        user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
        if user is None:
            user = User(username=username, full_name=full_name, role=ROLE_STAFF, is_demo=True)
            user.set_password(DEMO_PASSWORD)
            db.session.add(user)
        staff.append(user)
    db.session.commit()

    projects = db.session.execute(db.select(Project).where(Project.active.is_(True))).scalars().all()
    categories = {c.name: c for c in db.session.execute(db.select(Category)).scalars()}
    fallback_category = next(iter(categories.values()))

    # Tarihler: bir kısmı bugün, kalanı son `days` gün içinde (mesai saatleri)
    today = date.today()
    now = datetime.now()
    moments = []
    for i in range(count):
        day = today if i < 6 else today - timedelta(days=rng.randint(1, days))
        moment = datetime.combine(day, time(rng.randint(8, 16), rng.randint(0, 59)))
        if moment > now:
            moment = now - timedelta(minutes=rng.randint(1, 90))
        moments.append(moment)
    moments.sort()

    project_weights = [5, 3, 2][: len(projects)] + [2] * max(0, len(projects) - 3)
    statuses = [STATUS_RESOLVED] * 6 + [STATUS_CLOSED] * 2 + [STATUS_OPEN] * 2 + [STATUS_IN_REVIEW]
    for moment in moments:
        category_name, source, description, resolution = rng.choice(SCENARIOS)
        status = rng.choice(statuses)
        # Bugünkü kayıtların bir kısmı açık kalsın
        if moment.date() == today and rng.random() < 0.4:
            status = STATUS_OPEN
        done = status in DONE_STATUSES
        data = {
            "project_id": rng.choices(projects, weights=project_weights)[0].id,
            "category_id": categories.get(category_name, fallback_category).id,
            "requester_name": rng.choice(REQUESTERS),
            "requester_phone": f"0{rng.choice([312, 216, 532, 505, 542])} {rng.randint(100, 999)} "
                               f"{rng.randint(10, 99)} {rng.randint(10, 99)}",
            "channel": rng.choices(list(CHANNELS), weights=[8, 2, 1, 1, 1])[0],
            "source": source,
            "priority": rng.choices(["normal", "high", "urgent"], weights=[7, 2, 1])[0],
            "status": status,
            "description": description,
            "resolution": resolution if done else None,
            "duration_minutes": rng.choice([3, 4, 5, 7, 8, 10, 12, 15, 20, 25]) if done or rng.random() < 0.5 else None,
        }
        create_ticket(data, rng.choice(staff), created_at=moment, is_demo=True)
    return count


def demo_counts():
    tickets = db.session.execute(db.select(db.func.count(T.id)).where(T.is_demo.is_(True))).scalar()
    users = db.session.execute(db.select(db.func.count(User.id)).where(User.is_demo.is_(True))).scalar()
    return tickets, users


def clear_demo():
    """Demo kayıtları ve demo personelleri kaldırır. Gerçek veriye dokunulmaz.

    Gerçek bir kayıtta izi olan demo personel silinmez, pasife alınır.
    """
    demo_ids = db.select(T.id).where(T.is_demo.is_(True)).scalar_subquery()
    db.session.execute(db.delete(AuditLog).where(AuditLog.entity_type == "ticket", AuditLog.entity_id.in_(demo_ids)))
    deleted_tickets = db.session.execute(db.delete(T).where(T.is_demo.is_(True))).rowcount

    deleted_users = deactivated_users = 0
    for user in db.session.execute(db.select(User).where(User.is_demo.is_(True))).scalars().all():
        in_use = db.session.execute(
            db.select(db.func.count(T.id)).where(
                (T.created_by_id == user.id) | (T.updated_by_id == user.id) | (T.archived_by_id == user.id))
        ).scalar() or db.session.execute(
            db.select(db.func.count(AuditLog.id)).where(AuditLog.user_id == user.id)
        ).scalar()
        if in_use:
            user.active = False
            deactivated_users += 1
        else:
            db.session.delete(user)
            deleted_users += 1
    db.session.commit()
    return deleted_tickets, deleted_users, deactivated_users
