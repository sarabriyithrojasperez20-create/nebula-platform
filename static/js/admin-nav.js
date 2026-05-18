/**
 * Navegación admin: dropdown de perfil y transición suave entre vistas.
 */
(function () {
    'use strict';

    var trigger = document.getElementById('admin-profile-trigger');
    var menu = document.getElementById('admin-profile-dropdown');
    var root = document.getElementById('admin-profile-menu-root');

    function cerrarMenu() {
        if (!menu || !trigger) return;
        menu.classList.add('hidden');
        trigger.setAttribute('aria-expanded', 'false');
    }

    function abrirMenu() {
        if (!menu || !trigger) return;
        menu.classList.remove('hidden');
        trigger.setAttribute('aria-expanded', 'true');
    }

    if (trigger && menu) {
        trigger.addEventListener('click', function (e) {
            e.stopPropagation();
            if (menu.classList.contains('hidden')) {
                abrirMenu();
            } else {
                cerrarMenu();
            }
        });

        document.addEventListener('click', function (e) {
            if (root && !root.contains(e.target)) {
                cerrarMenu();
            }
        });

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                cerrarMenu();
            }
        });
    }

    document.body.classList.add('admin-page-enter');
})();
