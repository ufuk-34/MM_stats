TEKNİK DESTEK KAYIT PROGRAMI - KURULUM VE KULLANIM KILAVUZU
=============================================================

NASIL ÇALIŞIR?
--------------
* Program TEK BİR BİLGİSAYARA kurulur ve YALNIZCA O BİLGİSAYARDA kullanılır.
* İnternet bağlantısı GEREKMEZ. Ağdaki diğer bilgisayarlar programa BAĞLANAMAZ.
* Tüm personel kayıtları bu bilgisayara girer. Herkes kendi kullanıcı adı ve
  şifresiyle giriş yapar; böylece "kaydı kim girdi" bilgisi doğru tutulur.
* Program tarayıcı (Chrome / Edge) içinde açılır, ama internete çıkmaz;
  yalnızca bilgisayarın kendi içinde çalışır (adres: http://127.0.0.1:8000).


1) KURULUM (bir kez)
--------------------
1. "DestekKayit-Kurulum.exe" dosyasını çift tıklayın.
   - Windows "Bilgisayarınız korundu" (SmartScreen) uyarısı verirse:
     "Ek bilgi" -> "Yine de çalıştır" seçin. (Program imzalı olmadığı için bu uyarı normaldir.)
2. Kurulum klasörü olarak önerilen C:\DestekKayit klasörünü değiştirmeyin.
3. Seçenekler:
   [x] Masaüstüne kısayol oluştur
   [ ] Windows açıldığında otomatik başlat (isteğe bağlı)
4. "Programı şimdi başlat" ile bitirin.

Not: Kurulum yönetici (admin) yetkisi ister. Yetkiniz yoksa bilgi işlemden destek alın.


2) İLK AÇILIŞ - YÖNETİCİ HESABI
--------------------------------
Program ilk açıldığında "İlk Kurulum" ekranı gelir:
  - Kurum / birim adı
  - Yönetici ad soyad, kullanıcı adı ve şifre (en az 8 karakter)
  - İsterseniz "Demo veri yükle" ile örnek kayıtlarla deneyebilirsiniz
    (sonra Yönetim -> Sistem Ayarları -> "Demo Verileri Temizle" ile silinir).

Ardından Yönetim -> Personel bölümünden personelin hesaplarını oluşturun ve
her birine kendi kullanıcı adı / şifresini iletin.


3) GÜNLÜK KULLANIM (ORTAK BİLGİSAYAR)
-------------------------------------
1. Masaüstündeki "Teknik Destek Kayıt" simgesine çift tıklayın; tarayıcı açılır.
2. Kendi kullanıcı adınız ve şifrenizle giriş yapın.
3. "+ Yeni Kayıt" ile kaydı girin. Kayıt otomatik olarak SİZİN adınıza yazılır.
4. İşiniz bitince sol alttan "ÇIKIŞ YAP"a basın. Sıradaki personel kendi hesabıyla girer.

Güvenlik:
* 15 dakika boyunca klavye/fare kullanılmazsa oturum kendiliğinden kapanır ve ekran
  giriş sayfasına döner. Form doldururken (yazarken) oturum kapanmaz.
* Tarayıcı "Şifre kaydedilsin mi?" diye sorarsa "Hiçbir zaman" seçin. Aksi halde
  başkası sizin hesabınızla giriş yapabilir.

Program açıkken siyah bir pencere görünür. Bu pencere programın kendisidir;
kapatırsanız program durur. Küçültebilirsiniz. Tekrar açmak için masaüstü simgesine
çift tıklamanız yeterlidir.


4) YEDEKLEME (ÖNEMLİ)
---------------------
* Tüm kayıtlar C:\DestekKayit\veri klasöründedir.
* Program açıkken her gün otomatik yedek alınır: C:\DestekKayit\veri\yedekler
  (son 30 yedek saklanır). Yönetim -> Sistem Ayarları -> "Şimdi Yedek Al" ile
  istediğiniz an yedek alabilirsiniz.
* Bilgisayar arızalanırsa veriler kaybolmasın diye "yedekler" klasörünü haftada bir
  USB belleğe kopyalayın.

Yedekten geri dönmek için: programı kapatın, veri klasöründeki destek.db,
destek.db-wal ve destek.db-shm dosyalarını başka bir yere taşıyın, istediğiniz
yedek dosyasını veri klasörüne kopyalayıp adını "destek.db" yapın, programı açın.

Programı BAŞKA BİR BİLGİSAYARA TAŞIMAK için: yeni bilgisayara programı kurun,
programı kapatın ve eski bilgisayardaki C:\DestekKayit\veri klasörünün tamamını
yenisinin üzerine kopyalayın.


5) SORUNLAR
-----------
Yönetici şifresi unutuldu:
  Başlat menüsü -> Teknik Destek Kayıt -> "Yönetici Şifresini Sıfırla"
  (önce açık olan siyah program penceresini kapatın).
  Personel şifresini ise yönetici, Yönetim -> Personel -> Düzenle ekranından sıfırlar.

Program "zaten çalışıyor" diyor:
  Program zaten açıktır; tarayıcı kendiliğinden açılır. Görev çubuğundaki siyah
  pencereyi kontrol edin.

Tarayıcıda "Bu siteye ulaşılamıyor" hatası:
  Program kapalıdır. Masaüstündeki simgeye çift tıklayarak açın.


6) GÜNCELLEME VE KALDIRMA
-------------------------
* Yeni sürüm: yeni "DestekKayit-Kurulum.exe" dosyasını aynı şekilde çalıştırın.
  Kayıtlarınız korunur (yine de öncesinde yedek alın).
* Kaldırma: Windows Ayarları -> Uygulamalar -> "Teknik Destek Kayıt Programı" -> Kaldır.
  C:\DestekKayit\veri klasörü (kayıtlar ve yedekler) SİLİNMEZ; isterseniz elle silebilirsiniz.
