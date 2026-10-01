# Kurum İçi Teknik Destek Kayıt ve İstatistik Programı

3 dijital otomasyon projesi için telefon ve diğer kanallardan gelen destek taleplerinin
personel tarafından **manuel** kaydedildiği ve istatistiklerinin tutulduğu küçük bir kurum içi web uygulaması.
Çağrı merkezi, santral, CRM, e-posta/SMS entegrasyonu veya yapay zekâ **içermez**.

## Teknoloji

| Katman | Seçim | Neden |
|---|---|---|
| Dil / çatı | Python 3.10+ · Flask 3 | Basit, tek süreç, bakımı kolay |
| Veritabanı | SQLite (WAL modu) · SQLAlchemy 2 | Kurulum gerektirmez, tek dosya, ≤5 kullanıcı için fazlasıyla yeterli |
| Oturum | Flask-Login · Werkzeug şifre hash'i (scrypt) | Kullanıcı adı/şifre, rol bazlı erişim |
| Arayüz | Jinja2 şablonları · sade CSS · Chart.js (yerel kopya) | İnternet/CDN bağımlılığı yok |
| Excel | openpyxl | .xlsx çıktısı |
| Sunucu | waitress | Windows ve Linux'ta çalışan üretim WSGI sunucusu |

## Kurulum ve çalıştırma

```bash
# 1) Sanal ortam ve bağımlılıklar
python -m venv .venv
.venv/bin/pip install -r requirements.txt          # Windows: .venv\Scripts\pip install -r requirements.txt

# 2) Veritabanı (instance/destek.db) + başlangıç projeleri/kategorileri
.venv/bin/flask --app app init-db

# 3) Varsayılan yönetici hesabı (şifre sorulur, en az 8 karakter)
.venv/bin/flask --app app create-admin
#    veya etkileşimsiz:
.venv/bin/flask --app app create-admin --username admin --full-name "Sistem Yöneticisi" --password "GucluSifre.123"

# 4) (İsteğe bağlı) Demo veri: 5 demo personel + 45 kayıt (demo personel şifresi: Demo.12345)
.venv/bin/flask --app app seed-demo

# 5) Uygulamayı başlat  ->  http://SUNUCU_IP:8000
.venv/bin/python run.py                             # Windows: .venv\Scripts\python run.py
```

Ortam değişkenleri (isteğe bağlı): `PORT` (varsayılan 8000), `HOST` (0.0.0.0), `SECRET_KEY`
(verilmezse `instance/secret_key` dosyasında bir kez üretilir), `DATABASE_URL`,
`SESSION_COOKIE_SECURE=1` (HTTPS arkasında çalışılıyorsa).

`create-admin` mevcut bir kullanıcı adıyla çalıştırılırsa o kullanıcıyı yönetici yapar ve şifresini sıfırlar
(şifresi unutulan yönetici için kurtarma yolu).

**Demo verileri temizlemek:** Yönetim → Sistem Ayarları → "Demo Verileri Temizle" veya
`flask --app app clear-demo`. Yalnızca `is_demo` işaretli kayıt/personel silinir; gerçek kayıtlara dokunulmaz.

**Yedekleme:** Tüm veri `instance/destek.db` dosyasındadır. Uygulama durdurulup bu dosyanın
(varsa `-wal`/`-shm` dosyalarıyla birlikte) kopyalanması yeterlidir.

## Testler

```bash
.venv/bin/python -m pytest -q
```

`tests/test_app.py` gereksinimlerdeki 12 senaryoyu ve ek iş kurallarını (durum değişikliği, yeniden açma,
arşiv, işlem geçmişi, yönetim ekranları, demo temizleme, CSRF, giriş kilidi) kapsar.

## Modüller

| Dosya | İçerik |
|---|---|
| `app/__init__.py` | Uygulama fabrikası, güvenlik başlıkları, CSRF, şablon yardımcıları |
| `app/models.py` | Veritabanı modelleri ve işlem geçmişi yardımcısı |
| `app/constants.py` | Sorun kaynağı, durum, öncelik, kanal seçenekleri ve başlangıç verileri |
| `app/auth.py` | Giriş/çıkış, şifre değiştirme, `admin_required`, giriş deneme kilidi |
| `app/tickets.py` | Yeni kayıt, liste/filtre, detay, düzenleme, hızlı durum değişikliği, arşiv |
| `app/queries.py` | Ortak filtre mantığı ve tüm istatistik sorguları |
| `app/dashboard.py` | Ana ekran (Bugün / Bu Hafta / Bu Ay, bu ay–geçen ay karşılaştırması) |
| `app/stats.py` | İstatistikler (günlük, haftalık, aylık, özel aralık + önceki dönemle karşılaştırma) |
| `app/reports.py` | Excel'e aktarma ("Kayıtlar" + "Özet" sayfaları) |
| `app/admin.py` | Projeler, kategoriler, personel, sistem ayarları |
| `app/demo.py`, `app/cli.py` | Demo veri ve komut satırı komutları |

## Veritabanı

```
users            id, username (benzersiz), full_name, password_hash, role (admin|staff), active, is_demo,
                 created_at, last_login_at
projects         id, name (benzersiz), active, sort_order, created_at
categories       id, name (benzersiz), active, sort_order, created_at
support_tickets  id, ticket_no (YYYY-NNNNN, benzersiz), year, seq,
                 created_at*, created_by_id* → users, project_id* → projects, category_id* → categories,
                 requester_name, requester_phone, channel, source*, priority, status*,
                 description, resolution, duration_minutes,
                 updated_at, updated_by_id → users, resolved_at,
                 archived*, archived_at, archived_by_id → users, is_demo
audit_logs       id, created_at, user_id → users, entity_type, entity_id, action, changes (JSON: alan → [eski, yeni])
settings         key, value   (ör. kurum adı)
                 (* indeksli alanlar)
```

## Roller ve yetkiler

| | Yönetici | Personel |
|---|---|---|
| Yeni kayıt, durum değiştirme, yeniden açma | ✓ | ✓ (kendi kayıtları) |
| Kayıtları görme / düzenleme / arama | Tümü | Yalnızca kendi oluşturdukları |
| Arşivleme (silme yok) | ✓ | – |
| Dashboard / İstatistikler | Tüm kayıtlar + personel iş yükü | Yalnızca kendi kayıtları, diğer personel bilgisi yok |
| Raporlar / Excel | ✓ | – |
| Yönetim (proje, kategori, personel, ayarlar) | ✓ | – (menüde görünmez, 403) |

## İş kuralları

- **Sorun kaynağı** yalnızca iki seçeneklidir: *Sistem Kaynaklı* / *Kullanıcı İşlemi Kaynaklı*; tüm istatistiklerde ayrı gösterilir.
- **Çözülen** = Çözüldü + Kapatıldı; **Bekleyen** = Açık + İnceleniyor.
- Çözüldü/Kapatıldı durumundaki kayıtlarda **işlem süresi zorunludur**; ortalama süre yalnızca süre girilmiş kayıtlardan hesaplanır.
- Arşivlenen kayıtlar listede ayrıca görülebilir, istatistiklere dahil edilmez. Proje, kategori ve personel silinmez, pasif yapılır.
- Personelin yeni kayıt formunda son kullandığı proje otomatik seçili gelir; "Kaydet ve Yeni Kayıt" ile art arda kayıt girilebilir.
