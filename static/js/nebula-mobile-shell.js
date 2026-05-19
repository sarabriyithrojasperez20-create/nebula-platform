/**
 * Menú lateral móvil — dashboard estudiante (drawer + overlay).
 */
(function () {
    'use strict';

    var sidebar = document.getElementById('nb-estudiante-sidebar');
    if (!sidebar) return;

    var overlay = document.getElementById('nb-est-sidebar-overlay');
    var toggle = document.getElementById('nb-est-sidebar-toggle');

    function open() {
        sidebar.classList.add('nb-est-sidebar--open');
        if (overlay) overlay.classList.add('nb-est-sidebar-overlay--visible');
        document.body.classList.add('nb-drawer-open');
    }

    function close() {
        sidebar.classList.remove('nb-est-sidebar--open');
        if (overlay) overlay.classList.remove('nb-est-sidebar-overlay--visible');
        document.body.classList.remove('nb-drawer-open');
    }

    if (toggle) {
        toggle.addEventListener('click', function () {
            if (sidebar.classList.contains('nb-est-sidebar--open')) close();
            else open();
        });
    }

    if (overlay) {
        overlay.addEventListener('click', close);
    }

    sidebar.querySelectorAll('a').forEach(function (link) {
        link.addEventListener('click', function () {
            if (window.matchMedia('(max-width: 1023px)').matches) close();
        });
    });

    window.addEventListener('resize', function () {
        if (window.matchMedia('(min-width: 1024px)').matches) close();
    });
})();
