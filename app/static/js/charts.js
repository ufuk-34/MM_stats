/* Dashboard ve İstatistikler grafikleri (Chart.js, yerel kopya). */
(function () {
  var el = document.getElementById("chart-data");
  if (!el || !window.Chart) return;
  var data = JSON.parse(el.textContent);

  // Renkler: kategorik paletin ilk üç sırası (renk körlüğü için doğrulanmış)
  var SYSTEM = "#2a78d6", USER = "#eb6834";
  var GRID = "#e8ebf0", TEXT = "#4a5566";

  Chart.defaults.font.family = '"Segoe UI", system-ui, -apple-system, Roboto, Arial, sans-serif';
  Chart.defaults.font.size = 12;
  Chart.defaults.color = TEXT;
  Chart.defaults.animation = false;
  Chart.defaults.maintainAspectRatio = false;
  Chart.defaults.plugins.tooltip.backgroundColor = "#1c2430";
  Chart.defaults.plugins.tooltip.padding = 8;

  function linear(extra) {
    return Object.assign({
      beginAtZero: true, grid: { color: GRID }, border: { display: false },
      ticks: { precision: 0 }
    }, extra || {});
  }
  var plainAxis = { grid: { display: false }, border: { color: "#c4ccd7" } };

  function bar(id, labels, values, horizontal) {
    var canvas = document.getElementById(id);
    if (!canvas) return;
    new Chart(canvas, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [{
          label: "Kayıt", data: values, backgroundColor: SYSTEM,
          borderRadius: 4, borderSkipped: "start", maxBarThickness: horizontal ? 18 : 48
        }]
      },
      options: {
        indexAxis: horizontal ? "y" : "x",
        plugins: { legend: { display: false } },
        scales: horizontal ? { x: linear(), y: plainAxis } : { x: plainAxis, y: linear() }
      }
    });
  }

  // Grafik 1: Projelere göre kayıtlar (tek seri -> tek renk)
  if (data.projects) bar("chart-projects", data.projects.labels, data.projects.values, true);

  // Grafik 2: Sorun kaynağı dağılımı
  var src = document.getElementById("chart-source");
  if (src && data.source) {
    var total = data.source.system + data.source.user;
    new Chart(src, {
      type: "doughnut",
      data: {
        labels: ["Sistem Kaynaklı", "Kullanıcı İşlemi Kaynaklı"],
        datasets: [{
          data: total ? [data.source.system, data.source.user] : [1],
          backgroundColor: total ? [SYSTEM, USER] : ["#e8ebf0"],
          borderColor: "#ffffff", borderWidth: 2
        }]
      },
      options: {
        cutout: "62%",
        plugins: {
          legend: { position: "right", labels: { boxWidth: 10, boxHeight: 10 } },
          tooltip: {
            enabled: total > 0,
            callbacks: {
              label: function (ctx) {
                var pct = total ? (ctx.parsed * 100 / total).toFixed(1).replace(".", ",") : 0;
                return " " + ctx.label + ": " + ctx.parsed + " (%" + pct + ")";
              }
            }
          }
        }
      }
    });
  }

  // Grafik 3: Günlere göre kayıtlar (kaynağa göre yığılmış)
  var days = document.getElementById("chart-days");
  if (days && data.days) {
    new Chart(days, {
      type: "bar",
      data: {
        labels: data.days.labels,
        datasets: [
          { label: "Sistem Kaynaklı", data: data.days.system, backgroundColor: SYSTEM, borderColor: "#fff", borderWidth: { top: 1 }, maxBarThickness: 28 },
          { label: "Kullanıcı İşlemi Kaynaklı", data: data.days.user, backgroundColor: USER, borderColor: "#fff", borderWidth: { bottom: 1 }, borderRadius: 4, borderSkipped: "bottom", maxBarThickness: 28 }
        ]
      },
      options: {
        interaction: { mode: "index", intersect: false },
        plugins: { legend: { position: "top", align: "end", labels: { boxWidth: 10, boxHeight: 10 } } },
        scales: {
          x: Object.assign({ stacked: true, ticks: { maxRotation: 0, autoSkip: true, autoSkipPadding: 8 } }, plainAxis),
          y: linear({ stacked: true })
        }
      }
    });
  }

  // Grafik 4: Sorun kategorilerine göre dağılım
  if (data.categories) bar("chart-categories", data.categories.labels, data.categories.values, true);
})();
