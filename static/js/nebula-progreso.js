/**
 * Progreso dinámico Nébula — dashboard, mis cursos y lecciones.
 */
(function (global) {
  "use strict";

  function animateNumber(el, target, suffix) {
    if (!el) return;
    var start = parseInt(el.textContent, 10) || 0;
    if (start === target) {
      el.textContent = target + (suffix || "");
      return;
    }
    var t0 = performance.now();
    var dur = 520;
    function frame(now) {
      var p = Math.min(1, (now - t0) / dur);
      var eased = 1 - Math.pow(1 - p, 3);
      var val = Math.round(start + (target - start) * eased);
      el.textContent = val + (suffix || "");
      if (p < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  function setBarWidth(bar, pct) {
    if (!bar) return;
    bar.style.width = Math.max(0, Math.min(100, pct)) + "%";
    bar.setAttribute("aria-valuenow", String(pct));
  }

  function confettiBurst() {
    var canvas = document.createElement("canvas");
    canvas.className = "nebula-confetti-canvas";
    document.body.appendChild(canvas);
    var ctx = canvas.getContext("2d");
    var w = (canvas.width = window.innerWidth);
    var h = (canvas.height = window.innerHeight);
    var colors = ["#6a4bd8", "#9f7aea", "#c4b5fd", "#fbbf24", "#34d399"];
    var parts = [];
    for (var i = 0; i < 80; i++) {
      parts.push({
        x: w * 0.5 + (Math.random() - 0.5) * 200,
        y: h * 0.35,
        vx: (Math.random() - 0.5) * 10,
        vy: Math.random() * -12 - 4,
        r: Math.random() * 6 + 3,
        c: colors[Math.floor(Math.random() * colors.length)],
        life: 1,
      });
    }
    var start = performance.now();
    function draw(now) {
      ctx.clearRect(0, 0, w, h);
      var alive = false;
      parts.forEach(function (p) {
        if (p.life <= 0) return;
        alive = true;
        p.x += p.vx;
        p.y += p.vy;
        p.vy += 0.35;
        p.life -= 0.012;
        ctx.globalAlpha = Math.max(0, p.life);
        ctx.fillStyle = p.c;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fill();
      });
      if (alive && now - start < 4000) requestAnimationFrame(draw);
      else canvas.remove();
    }
    requestAnimationFrame(draw);
  }

  function updateDashboardCard(card, data) {
    var pct = parseInt(data.porcentaje, 10) || 0;
    card.dataset.porcentaje = String(pct);
    card.classList.toggle("dash-class-card--completed", pct >= 100);

    var stats = card.querySelectorAll(".dash-class-stat strong");
    if (stats[0]) animateNumber(stats[0], pct, "%");

    var headEm = card.querySelector(".dash-class-card__progress-head em");
    if (headEm) animateNumber(headEm, pct, "%");

    var meta = card.querySelector(".dash-class-card__meta");
    if (meta && data.estado_texto) {
      var parts = meta.textContent.split("·");
      var suffix = parts.length > 1 ? parts.slice(1).join("·").trim() : "";
      meta.textContent =
        (data.estado_curso || data.estado_texto) + (suffix ? " · " + suffix : "");
    }

    setBarWidth(card.querySelector(".dashboard-progress-fill"), pct);
  }

  function refreshDashboard(resumen) {
    if (!resumen || !resumen.clases_activas) return;
    var cards = document.querySelectorAll(".dash-class-card[data-slug]");
  var map = {};
    resumen.clases_activas.forEach(function (c) {
      map[c.slug] = c;
    });
    cards.forEach(function (card) {
      var slug = card.getAttribute("data-slug");
      if (slug && map[slug]) updateDashboardCard(card, map[slug]);
    });

    if (resumen.cursos_completados > 0) {
      var prev = parseInt(sessionStorage.getItem("nebula_confetti_done") || "0", 10);
      if (resumen.cursos_completados > prev) confettiBurst();
      sessionStorage.setItem("nebula_confetti_done", String(resumen.cursos_completados));
    }

    updateTrendChart(resumen.tendencia);
  }

  function updateTrendChart(tendencia) {
    var svg = document.getElementById("progreso-tendencia-chart");
    if (!svg || !tendencia || !tendencia.length) return;
    var vals = tendencia.map(function (t) {
      return Math.max(0, Math.min(100, parseInt(t.valor, 10) || 0));
    });
    var max = Math.max.apply(null, vals.concat([1]));
    var pts = vals.map(function (v, i) {
      var x = (i / Math.max(1, vals.length - 1)) * 100;
      var y = 38 - (v / max) * 32;
      return x.toFixed(1) + "," + y.toFixed(1);
    });
    var line = "M" + pts.join(" L");
    var area = line + " L100,40 L0,40 Z";
    var lineEl = svg.querySelector("#progreso-trend-line");
    var areaEl = svg.querySelector("#progreso-trend-area");
    if (lineEl) lineEl.setAttribute("d", line);
    if (areaEl) areaEl.setAttribute("d", area);
    var labels = document.getElementById("progreso-trend-labels");
    if (labels) {
      labels.innerHTML = tendencia
        .map(function (t) {
          return (
            '<span class="text-[10px] text-slate-400 font-bold uppercase">' +
            (t.etiqueta || "") +
            "</span>"
          );
        })
        .join("");
    }
  }

  function updateCursoDetalle(pct) {
    var fill = document.querySelector(".curso-detalle-progress-fill");
    var label = document.querySelector(".curso-detalle-progress-pct");
    setBarWidth(fill, pct);
    if (label) animateNumber(label, pct, "%");
  }

  function updateMisCursosCard(slug, pct) {
    var card = document.querySelector('.mis-cursos-card[data-slug="' + slug + '"]');
    if (!card) return;
    var text = card.querySelector(".mis-cursos-progress-text");
    var arc = card.querySelector(".mis-cursos-progress-arc");
    if (text) animateNumber(text, pct, "%");
    if (arc) arc.setAttribute("stroke-dashoffset", String(Math.max(0, 100 - pct)));
  }

  function fetchResumen() {
    return fetch("/api/progreso/resumen", {
      credentials: "same-origin",
      headers: { Accept: "application/json", "X-Requested-With": "XMLHttpRequest" },
    }).then(function (r) {
      return r.json();
    });
  }

  function onCursoUpdated(slug, progreso) {
    if (!progreso) return;
    var pct = progreso.porcentaje || 0;
    updateMisCursosCard(slug, pct);
    updateCursoDetalle(pct);
    if (progreso.completado) confettiBurst();
    fetchResumen().then(function (data) {
      if (data && data.ok) refreshDashboard(data);
    });
  }

  function initDashboard() {
    var grid = document.querySelector(".dashboard-classes-grid");
    if (!grid) return;
    fetchResumen()
      .then(function (data) {
        if (data && data.ok) refreshDashboard(data);
      })
      .catch(function () {});
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "visible") {
        fetchResumen()
          .then(function (data) {
            if (data && data.ok) refreshDashboard(data);
          })
          .catch(function () {});
      }
    });
  }

  global.NebulaProgreso = {
    initDashboard: initDashboard,
    refreshDashboard: refreshDashboard,
    onCursoUpdated: onCursoUpdated,
    fetchResumen: fetchResumen,
    confettiBurst: confettiBurst,
    updateTrendChart: updateTrendChart,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initDashboard);
  } else {
    initDashboard();
  }
})(window);
