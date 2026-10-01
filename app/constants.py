"""Sabit seçenek listeleri.

Proje ve kategoriler veritabanında tutulur (yönetici değiştirebilir).
Buradaki değerler ise iş kuralının parçası olan, değişmeyecek seçeneklerdir.
Veritabanında kısa İngilizce anahtarlar, arayüzde Türkçe etiketler kullanılır.
"""

# Roller
ROLE_ADMIN = "admin"
ROLE_STAFF = "staff"
ROLES = {
    ROLE_ADMIN: "Yönetici",
    ROLE_STAFF: "Personel",
}

# Sorun kaynağı: istatistiklerin ana ayrımı. Sadece iki seçenek vardır.
SOURCE_SYSTEM = "system"
SOURCE_USER = "user"
SOURCES = {
    SOURCE_SYSTEM: "Sistem Kaynaklı",
    SOURCE_USER: "Kullanıcı İşlemi Kaynaklı",
}
# Formda yol gösterici örnekler (kurum içi sınıflandırma; suçlayıcı değildir)
SOURCE_HINTS = {
    SOURCE_SYSTEM: "Yazılım hatası, sistemin çalışmaması, bağlantı, entegrasyon, "
                   "veri veya performans problemi, diğer sistemsel hatalar",
    SOURCE_USER: "İşlem adımlarının bilinmemesi, hatalı veri girişi veya işlem, "
                 "yetki/izin nedeniyle yapılamayan işlem, diğer kullanıcı işlemleri",
}

# Kayıt durumları
STATUS_OPEN = "open"
STATUS_IN_REVIEW = "in_review"
STATUS_RESOLVED = "resolved"
STATUS_CLOSED = "closed"
STATUSES = {
    STATUS_OPEN: "Açık",
    STATUS_IN_REVIEW: "İnceleniyor",
    STATUS_RESOLVED: "Çözüldü",
    STATUS_CLOSED: "Kapatıldı",
}
# İstatistik grupları
DONE_STATUSES = (STATUS_RESOLVED, STATUS_CLOSED)       # "Çözülen"
PENDING_STATUSES = (STATUS_OPEN, STATUS_IN_REVIEW)     # "Açık / Bekleyen"

# Öncelik (basit, SLA yok)
PRIORITY_NORMAL = "normal"
PRIORITIES = {
    PRIORITY_NORMAL: "Normal",
    "high": "Yüksek",
    "urgent": "Acil",
}

# İletişim kanalı (sadece bilgi amaçlı; hiçbir entegrasyon yoktur)
CHANNEL_PHONE = "phone"
CHANNELS = {
    CHANNEL_PHONE: "Telefon",
    "email": "E-posta",
    "in_person": "Yüz yüze",
    "message": "Yazılı mesaj",
    "other": "Diğer",
}

# İşlem süresi hızlı seçim düğmeleri (dakika)
QUICK_DURATIONS = (3, 5, 10, 15, 30)
MAX_DURATION_MINUTES = 1440

# Kurulumda oluşturulan başlangıç verileri (sonradan yönetimden değiştirilebilir)
DEFAULT_PROJECTS = (
    "Dijital Otomasyon Projesi 1",
    "Dijital Otomasyon Projesi 2",
    "Dijital Otomasyon Projesi 3",
)
DEFAULT_CATEGORIES = (
    "Giriş / Oturum",
    "Kullanıcı işlemleri",
    "Veri girişi",
    "Yetkilendirme",
    "Teknik hata",
    "Bağlantı problemi",
    "Sistem performansı",
    "Entegrasyon",
    "Bilgi talebi",
    "Diğer",
)
