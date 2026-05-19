/**
 * Mostrar / ocultar contraseña (login y registro).
 * Uso: togglePass('password', button) o data-toggle-password="password" en el botón.
 */
(function () {
  function togglePass(inputId, btn) {
    const id = inputId || "password";
    const input = document.getElementById(id);
    if (!input) return;

    const icon = btn
      ? btn.querySelector(".material-symbols-outlined")
      : document.getElementById("pass-icon");

    const willShow = input.type === "password";
    input.type = willShow ? "text" : "password";

    if (icon) {
      icon.textContent = willShow ? "visibility_off" : "visibility";
    }

    const control = btn || document.querySelector('[data-toggle-password="' + id + '"]');
    if (control) {
      control.setAttribute(
        "aria-label",
        willShow ? "Ocultar contraseña" : "Mostrar contraseña"
      );
      control.setAttribute("aria-pressed", willShow ? "true" : "false");
    }
  }

  window.togglePass = togglePass;

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-toggle-password]").forEach(function (button) {
      const targetId = button.getAttribute("data-toggle-password");
      if (!targetId) return;
      button.addEventListener("click", function (e) {
        e.preventDefault();
        togglePass(targetId, button);
      });
    });
  });
})();
