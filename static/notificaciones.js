(function () {
  function cerrarPanel(dropdown) {
    const toggle = dropdown.querySelector(".notificaciones-toggle");
    const panel = dropdown.querySelector(".notificaciones-panel");
    if (!toggle || !panel) return;
    panel.hidden = true;
    toggle.setAttribute("aria-expanded", "false");
    dropdown.classList.remove("is-open");
  }

  window.cerrarPanelNotificaciones = cerrarPanel;

  function cerrarMenusUsuario() {
    document.querySelectorAll(".nb-user-menu.is-open").forEach(function (menu) {
      menu.classList.remove("is-open");
      var t = menu.querySelector("[data-nb-user-menu-toggle]");
      var p = menu.querySelector("[data-nb-user-menu-panel]");
      if (t) t.setAttribute("aria-expanded", "false");
      if (p) p.setAttribute("hidden", "");
    });
  }

  function abrirPanel(dropdown) {
    const toggle = dropdown.querySelector(".notificaciones-toggle");
    const panel = dropdown.querySelector(".notificaciones-panel");
    if (!toggle || !panel) return;
    cerrarMenusUsuario();
    document.querySelectorAll(".notificaciones-dropdown.is-open").forEach(cerrarPanel);
    panel.hidden = false;
    toggle.setAttribute("aria-expanded", "true");
    dropdown.classList.add("is-open");
  }

  function initNotificaciones() {
    document.querySelectorAll(".notificaciones-dropdown").forEach(function (dropdown) {
      const toggle = dropdown.querySelector(".notificaciones-toggle");
      if (!toggle || toggle.dataset.notificacionesInit === "true") return;
      toggle.dataset.notificacionesInit = "true";

      toggle.addEventListener("click", function (e) {
        e.stopPropagation();
        const panel = dropdown.querySelector(".notificaciones-panel");
        if (panel && panel.hidden) {
          abrirPanel(dropdown);
        } else {
          cerrarPanel(dropdown);
        }
      });

      dropdown.querySelector(".notificaciones-panel")?.addEventListener("click", function (e) {
        e.stopPropagation();
      });
    });

    document.addEventListener("click", function () {
      document.querySelectorAll(".notificaciones-dropdown.is-open").forEach(cerrarPanel);
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        document.querySelectorAll(".notificaciones-dropdown.is-open").forEach(cerrarPanel);
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initNotificaciones);
  } else {
    initNotificaciones();
  }
})();
