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
| Excel | openpyxl | Grafikli .xlsx raporu (Excel'in kendi grafikleri) |
| Sunucu | waitress | Windows ve Linux'ta çalışan üretim WSGI sunucusu |

## Windows'ta tek bilgisayara kurulum (önerilen)

Program **tek bir bilgisayara** kurulur ve yalnızca o bilgisayarda kullanılır. Sunucu sadece
`127.0.0.1` adresini dinler (ayrıca uygulama yerel olmayan istekleri 403 ile reddeder); ağdaki diğer
bilgisayarlar bağlanamaz, internet bağlantısı gerekmez. Tüm personel kayıtlarını bu bilgisayarda
kendi hesabıyla girer; ortak kullanım için 15 dakika hareketsizlikte oturum kendiliğinden kapanır
(`IDLE_TIMEOUT_MINUTES`).

1. Kurulum dosyası (giriş gerektirmez, her zaman en son sürüm):
   **https://github.com/ufuk-34/MM_stats/releases/latest/download/DestekKayit-Kurulum.exe**
   Tüm sürümler ve kurulumsuz (zip) sürüm: https://github.com/ufuk-34/MM_stats/releases
2. `DestekKayit-Kurulum.exe` çalıştırılır (C:\DestekKayit klasörüne kurar, masaüstü kısayolu ve
   isteğe bağlı otomatik başlatma).
3. Program ilk açıldığında tarayıcıda **İlk Kurulum** ekranı gelir; yönetici hesabı burada oluşturulur.

Ayrıntılı, teknik olmayan kılavuz: [KURULUM.md](KURULUM.md)

.exe, `.github/workflows/windows-build.yml` iş akışında Windows makinesinde
PyInstaller (`packaging/DestekKayit.spec`) ve Inno Setup (`packaging/installer.iss`) ile üretilir;
testler ve .exe duman testi geçmeden kurulum dosyası oluşmaz.

## Kaynak koddan çalıştırma (geliştirme / Linux)

```bash
# 1) Sanal ortam ve bağımlılıklar
python -m venv .venv
.venv/bin/pip install -r requirements.txt          # Windows: .venv\Scripts\pip install -r requirements.txt

# 2) Veritabanı (veri/destek.db) + başlangıç projeleri/kategorileri
.venv/bin/flask --app app init-db

# 3) Yönetici hesabı: ilk açılıştaki "İlk Kurulum" ekranından veya komutla (şifre sorulur)
.venv/bin/flask --app app create-admin
#    veya etkileşimsiz:
.venv/bin/flask --app app create-admin --username admin --full-name "Sistem Yöneticisi" --password "GucluSifre.123"

# 4) (İsteğe bağlı) Demo veri: 5 demo personel + 45 kayıt (demo personel şifresi: Demo.12345)
.venv/bin/flask --app app seed-demo

# 5) Uygulamayı başlat  ->  http://127.0.0.1:8000 (yalnızca bu bilgisayardan)
.venv/bin/python run.py                             # Windows: .venv\Scripts\python run.py
#    Seçenekler: --port 8080, --no-browser, --yonetici-sifirla
```

Ortam değişkenleri (isteğe bağlı): `DESTEK_DATA_DIR` (veri klasörü; varsayılan programın yanındaki
`veri/`), `PORT`, `IDLE_TIMEOUT_MINUTES` (varsayılan 15), `SECRET_KEY` (verilmezse veri klasöründe bir kez üretilir), `DATABASE_URL`,
`SESSION_COOKIE_SECURE=1` (HTTPS arkasında çalışılıyorsa).

`create-admin` mevcut bir kullanıcı adıyla çalıştırılırsa o kullanıcıyı yönetici yapar ve şifresini sıfırlar
(şifresi unutulan yönetici için kurtarma yolu).

**Demo verileri temizlemek:** Yönetim → Sistem Ayarları → "Demo Verileri Temizle" veya
`flask --app app clear-demo`. Yalnızca `is_demo` işaretli kayıt/personel silinir; gerçek kayıtlara dokunulmaz.

**Yedekleme:** Tüm veri `veri/destek.db` dosyasındadır. Program açıkken günde bir kez
`veri/yedekler/` klasörüne otomatik yedek alınır (son 30 yedek); Yönetim → Sistem Ayarları →
"Şimdi Yedek Al" ile anında yedek alınabilir.

## Testler

```bash
.venv/bin/python -m pytest -q
```

`tests/test_app.py` gereksinimlerdeki 12 senaryoyu ve ek iş kurallarını (ilk kurulum ekranı, yedekleme, durum değişikliği, yeniden açma,
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
| `app/reports.py` | Raporlar sayfası ve Excel indirme |
| `app/excel_report.py` | Grafikli Excel raporu: "Rapor" (özet kutuları + 5 grafik, tek A4), "Tablolar", "Kayıtlar"; sayılar Kayıtlar'dan formülle hesaplanır |
| `app/admin.py` | Projeler, kategoriler, personel, sistem ayarları |
| `app/demo.py`, `app/cli.py` | Demo veri ve komut satırı komutları |
| `app/backup.py` | Günlük otomatik ve elle veritabanı yedeği |
| `run.py` | Başlatıcı (.exe giriş noktası): yalnızca localhost'ta sunucu, tarayıcı, yedek zamanlayıcı |
| `packaging/` | PyInstaller tanımı ve Inno Setup kurulum betiği |

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
