/* Küçük arayüz yardımcıları (CSP uyumlu: satır içi script yok). */
(function () {
  // Tablo satırına tıklayınca kayıt detayına git
  document.querySelectorAll("tr[data-href]").forEach(function (row) {
    row.addEventListener("click", function (e) {
      if (e.target.closest("a, button, input, select")) return;
      window.location = row.dataset.href;
    });
  });

  // İşlem süresi hızlı seçim düğmeleri
  var duration = document.getElementById("duration");
  document.querySelectorAll("[data-duration]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      if (duration) { duration.value = btn.dataset.duration; duration.focus(); }
    });
  });

  // Onay isteyen formlar (arşivleme, demo veri temizleme)
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!window.confirm(form.dataset.confirm)) e.preventDefault();
    });
  });

  // Dönem seçimi değişince formu gönder
  document.querySelectorAll("[data-autosubmit]").forEach(function (input) {
    input.addEventListener("change", function () { input.form.submit(); });
  });

  // Ortak bilgisayar: hareketsizlikte oturumu kapat, kullanım sürerken açık tut.
  // Sunucu, son istekten bu yana süre dolduysa oturumu kapatır. Kullanıcı formu doldururken
  // (klavye/fare hareketi) arka planda kısa bir istek gönderilir; böylece uzun telefon
  // görüşmesinde yazılan kayıt kaybolmaz. Gerçekten hareketsiz kalınırsa sayfa yenilenir ve
  // giriş ekranına dönülür (ekranda kişisel veri açık kalmaz).
  var idleMinutes = parseInt(document.body.dataset.idleMinutes || "0", 10);
  if (idleMinutes > 0) {
    var lastActivity = Date.now(), lastPing = Date.now();
    var mark = function () { lastActivity = Date.now(); };
    ["keydown", "mousedown", "mousemove", "wheel", "touchstart"].forEach(function (ev) {
      document.addEventListener(ev, mark, { passive: true });
    });
    setInterval(function () {
      var now = Date.now();
      if (now - lastActivity > idleMinutes * 60000) {
        window.location.reload();
      } else if (now - lastActivity < 120000 && now - lastPing > 120000) {
        lastPing = now;
        fetch(document.body.dataset.keepaliveUrl, { credentials: "same-origin" }).catch(function () {});
      }
    }, 20000);
  }

  // Aynı formun iki kez gönderilmesini engelle (mükerrer kayıt önlemi)
  document.querySelectorAll("form[method=post]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (e.defaultPrevented) return;
      if (form.dataset.submitted) { e.preventDefault(); return; }
      form.dataset.submitted = "1";
    });
  });
})();
