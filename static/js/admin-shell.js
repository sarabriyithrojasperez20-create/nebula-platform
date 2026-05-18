/**
 * Shell admin premium: sidebar móvil y navegación a paneles.
 */
(function () {
    'use strict';

    var sidebar = document.getElementById('nb-sidebar');
    var overlay = document.getElementById('nb-sidebar-overlay');
    var toggle = document.getElementById('nb-sidebar-toggle');

    function openSidebar() {
        if (sidebar) sidebar.classList.add('nb-sidebar--open');
        if (overlay) overlay.classList.add('nb-sidebar-overlay--visible');
    }

    function closeSidebar() {
        if (sidebar) sidebar.classList.remove('nb-sidebar--open');
        if (overlay) overlay.classList.remove('nb-sidebar-overlay--visible');
    }

    if (toggle) {
        toggle.addEventListener('click', function () {
            if (sidebar && sidebar.classList.contains('nb-sidebar--open')) {
                closeSidebar();
            } else {
                openSidebar();
            }
        });
    }

    if (overlay) {
        overlay.addEventListener('click', closeSidebar);
    }

    document.querySelectorAll('[data-admin-open]').forEach(function (link) {
        link.addEventListener('click', function () {
            var panel = link.getAttribute('data-admin-open');
            if (!panel) return;
            try {
                sessionStorage.setItem('nebula_admin_panel', panel);
            } catch (e) {
                /* ignore */
            }
        });
    });
})();
