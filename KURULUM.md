TEKNİK DESTEK KAYIT PROGRAMI - KURULUM VE KULLANIM KILAVUZU
=============================================================

NASIL ÇALIŞIR?
--------------
Program TEK BİR BİLGİSAYARA kurulur. Kayıtlar o bilgisayarda tutulur.

  * O bilgisayarda: masaüstündeki "Teknik Destek Kayıt" simgesine çift tıklanır,
    tarayıcı kendiliğinden açılır.
  * Aynı ağdaki diğer bilgisayarlarda: hiçbir şey kurulmaz. Chrome / Edge açılıp
    programın ekranında yazan adres girilir (ör. http://192.168.1.25:8000).
    Bu adresi tarayıcıda "sık kullanılanlara" eklemeniz yeterlidir.

Herkes kendi kullanıcı adı ve şifresiyle giriş yapar. Tek bir ortak bilgisayar
kullanılıyorsa personel işini bitirince sol alttan "Çıkış yap"a basmalıdır.


1) KURULUM (bir kez, programın duracağı bilgisayarda)
------------------------------------------------------
1. "DestekKayit-Kurulum.exe" dosyasını çift tıklayın.
   - Windows "Bilgisayarınız korundu" (SmartScreen) uyarısı verirse:
     "Ek bilgi" -> "Yine de çalıştır" seçin. (Program imzalı olmadığı için bu uyarı normaldir.)
2. Kurulum klasörü olarak önerilen C:\DestekKayit klasörünü değiştirmeyin.
3. Seçenekler:
   [x] Masaüstüne kısayol oluştur
   [x] Ağdaki diğer bilgisayarların bağlanmasına izin ver  (diğer bilgisayarlar kullanacaksa işaretli kalsın)
   [ ] Windows açıldığında otomatik başlat  (önerilir: bilgisayar yeniden başlayınca program kendiliğinden açılır)
4. "Programı şimdi başlat" ile bitirin.

Not: Kurulum yönetici (admin) yetkisi ister. Yetkiniz yoksa bilgi işlemden destek alın.


2) İLK AÇILIŞ - YÖNETİCİ HESABI
--------------------------------
Program ilk açıldığında tarayıcıda "İlk Kurulum" ekranı gelir:
  - Kurum / birim adı
  - Yönetici ad soyad, kullanıcı adı ve şifre (en az 8 karakter)
  - İsterseniz "Demo veri yükle" ile örnek kayıtlarla deneyebilirsiniz
    (sonra Yönetim -> Sistem Ayarları -> "Demo Verileri Temizle" ile silinir).

Bu ekran güvenlik nedeniyle yalnızca programın kurulu olduğu bilgisayardan açılabilir.

Ardından Yönetim -> Personel bölümünden en fazla 5 personelin hesabını oluşturun ve
her birine kullanıcı adı / şifresini iletin.


3) GÜNLÜK KULLANIM
------------------
* Program açıkken siyah bir pencere görünür. BU PENCEREYİ KAPATMAYIN; kapatırsanız
  program durur ve diğer bilgisayarlar bağlanamaz. Pencereyi küçültebilirsiniz.
* Pencerede "Diğer bilgisayarlardan: http://..." satırında yazan adres, diğer
  bilgisayarların kullanacağı adrestir. (Yönetim -> Sistem Ayarları'nda da görünür.)
* Programın kurulu olduğu bilgisayar KAPALIYKEN veya UYKUDAYKEN diğer bilgisayarlar
  programa ulaşamaz. Bu bilgisayarın mesai boyunca açık kalması ve uyku moduna
  geçmemesi gerekir (Ayarlar -> Sistem -> Güç -> Uyku: "Hiçbir zaman").


4) YEDEKLEME (ÖNEMLİ)
---------------------
* Tüm kayıtlar C:\DestekKayit\veri klasöründedir.
* Program açıkken her gün otomatik yedek alınır: C:\DestekKayit\veri\yedekler
  (son 30 yedek saklanır). Yönetim -> Sistem Ayarları -> "Şimdi Yedek Al" ile
  istediğiniz an yedek alabilirsiniz.
* Bilgisayar arızasına karşı "yedekler" klasörünü haftada bir USB belleğe veya ağ
  klasörüne kopyalayın.

Yedekten geri dönmek için: programı kapatın, veri klasöründeki destek.db,
destek.db-wal ve destek.db-shm dosyalarını başka bir yere taşıyın, istediğiniz
yedek dosyasını veri klasörüne kopyalayıp adını "destek.db" yapın, programı açın.

Programı BAŞKA BİR BİLGİSAYARA TAŞIMAK için: yeni bilgisayara programı kurun,
programı kapatın ve eski bilgisayardaki C:\DestekKayit\veri klasörünün tamamını
yenisinin üzerine kopyalayın.


5) SORUNLAR
-----------
Diğer bilgisayarlar bağlanamıyor:
  - Program penceresi açık mı? Bilgisayar uykuda mı?
  - Adresi doğru mu yazdınız? (http://IP-ADRESİ:8000)
  - Ağ bağlantısı "Ortak (Public)" olarak ayarlıysa güvenlik duvarı izin vermez.
    Windows Ayarları -> Ağ ve İnternet -> bağlantı özellikleri -> "Özel (Private)"
    seçin veya bilgi işlemden 8000 numaralı TCP portunun açılmasını isteyin.
  - Bilgisayarın IP adresi değişebilir; bilgi işlemden sabit IP verilmesini isteyin.

Yönetici şifresi unutuldu:
  Başlat menüsü -> Teknik Destek Kayıt -> "Yönetici Şifresini Sıfırla"
  (önce açık olan program penceresini kapatın).

Program açılmıyor / "zaten çalışıyor" diyor:
  Program zaten açıktır; tarayıcı kendiliğinden açılır. Görev çubuğundaki siyah
  pencereyi kontrol edin.


6) GÜNCELLEME VE KALDIRMA
-------------------------
* Yeni sürüm: yeni "DestekKayit-Kurulum.exe" dosyasını aynı şekilde çalıştırın.
  Kayıtlarınız korunur (yine de öncesinde yedek alın).
* Kaldırma: Windows Ayarları -> Uygulamalar -> "Teknik Destek Kayıt Programı" -> Kaldır.
  C:\DestekKayit\veri klasörü (kayıtlar ve yedekler) SİLİNMEZ; isterseniz elle silebilirsiniz.
