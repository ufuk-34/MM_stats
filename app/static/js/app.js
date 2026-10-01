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

  // Aynı formun iki kez gönderilmesini engelle (mükerrer kayıt önlemi)
  document.querySelectorAll("form[method=post]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (e.defaultPrevented) return;
      if (form.dataset.submitted) { e.preventDefault(); return; }
      form.dataset.submitted = "1";
    });
  });
})();
