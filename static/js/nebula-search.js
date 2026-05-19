/**
 * Búsqueda en tiempo real — estudiante, plan de estudios, progreso, tutor, admin.
 */
(function (global) {
    'use strict';

    var U = global.NebulaSearchUtils;
    if (!U) return;

    function initMisCursos() {
        var grid = document.getElementById('mis-cursos-grid');
        var input = document.getElementById('mis-cursos-busqueda');
        var contador = document.getElementById('mis-cursos-contador');
        var emptyState = document.getElementById('mis-cursos-empty');
        var emptySearch = document.getElementById('mis-cursos-empty-search');
        if (!grid || !input) return;

        var applySearch = function (query) {
            if (typeof global.aplicarFiltrosMisCursos === 'function') {
                global.aplicarFiltrosMisCursos(query);
                return;
            }
            var cards = grid.querySelectorAll('.mis-cursos-card[data-slug]');
            var visibles = U.filterElements(cards, query);
            if (contador) {
                var n = visibles;
                contador.textContent =
                    n === 1 ? 'Mostrando 1 curso activo' : 'Mostrando ' + n + ' cursos activos';
            }
            var hasCards = cards.length > 0;
            if (emptyState) emptyState.classList.add('hidden');
            if (emptySearch) {
                emptySearch.classList.toggle('hidden', !query || visibles > 0 || !hasCards);
            }
        };

        U.bindInput(input, applySearch);
    }

    function initProgreso() {
        var input = document.getElementById('progreso-busqueda');
        var scope = document.querySelector('.perfil-page, body');
        if (!input) {
            input = document.querySelector('header input[placeholder*="conocimiento"]');
            if (input) input.id = 'progreso-busqueda';
        }
        if (!input) return;

        var items = document.querySelectorAll('[data-progreso-search]');
        var extra = document.getElementById('progreso-busqueda-extra');
        var extraWrap = document.getElementById('progreso-busqueda-extra-wrap');

        U.bindInput(input, function (query) {
            var vis = U.filterElements(items, query);
            if (extra) {
                var extraItems = extra.querySelectorAll('[data-progreso-search]');
                vis += U.filterElements(extraItems, query);
            }
            if (extraWrap) {
                extraWrap.classList.toggle('hidden', !query);
            }
            U.showEmptyMessage(
                document.getElementById('progreso-busqueda-empty-anchor') || extraWrap,
                !!query && vis === 0,
                'No se encontraron resultados relacionados con tu búsqueda.'
            );
        });
    }

    function initDashboard() {
        var input = document.getElementById('dashboard-busqueda');
        if (!input) return;

        U.bindInput(input, function (query) {
            var selectors = [
                '.dash-class-card',
                '#dashboard-eval-list > li',
                '#dashboard-eval-list [data-search]',
            ];
            var all = [];
            selectors.forEach(function (sel) {
                document.querySelectorAll(sel).forEach(function (el) {
                    all.push(el);
                });
            });
            var vis = U.filterElements(all, query);
            var empty = document.getElementById('dashboard-busqueda-empty');
            if (empty) {
                empty.classList.toggle('hidden', !query || vis > 0);
            }
        });
    }

    function initTutor() {
        var input = document.getElementById('tutor-sidebar-search');
        if (!input) return;

        U.bindInput(input, function (query) {
            var sidebarItems = document.querySelectorAll(
                '#tutor-recientes-list button, .tutor-ai-sidebar .tutor-ai-sidebar-btn'
            );
            U.filterElements(sidebarItems, query);

            var messages = document.querySelectorAll('#tutor-chat-messages .tutor-ai-msg-row');
            if (messages.length) {
                U.filterElements(messages, query);
            }
        });
    }

    function initClase() {
        var input = document.getElementById('clase-busqueda');
        if (!input) return;

        U.bindInput(input, function (query) {
            var lessons = document.querySelectorAll('aside [data-leccion-search], aside a[data-leccion-id]');
            if (!lessons.length) {
                lessons = document.querySelectorAll('aside .space-y-1 a, aside .space-y-2 a');
            }
            U.filterElements(lessons, query);
            U.showEmptyMessage(
                document.querySelector('aside .flex-1.overflow-y-auto'),
                !!query && U.filterElements(lessons, query) === 0,
                'No se encontraron lecciones con ese término.'
            );
        });
    }

    function initPerfil() {
        var input = document.getElementById('perfil-busqueda');
        if (!input) return;

        U.bindInput(input, function (query) {
            var sections = document.querySelectorAll('[data-perfil-search]');
            U.filterElements(sections, query);
            U.showEmptyMessage(
                document.querySelector('.perfil-main'),
                !!query && U.filterElements(sections, query) === 0,
                'No hay información en tu perfil que coincida con la búsqueda.'
            );
        });
    }

    function initAdmin() {
        var input =
            document.getElementById('admin-global-search') ||
            document.querySelector('.nb-search input[type="search"]');
        if (!input) return;
        if (!input.id) input.id = 'admin-global-search';

        function getScope() {
            var panel = document.querySelector('.admin-detail-panel:not(.hidden)');
            return panel || document.querySelector('.nb-canvas') || document.body;
        }

        function runSearch(query) {
            var scope = getScope();
            var rows = scope.querySelectorAll(
                'table tbody tr, .nb-timeline-item, .nb-table tbody tr, .admin-data-table tbody tr'
            );
            var cards = scope.querySelectorAll('.nb-kpi-card, .nb-glass-card');
            var vis = U.filterElements(rows, query);
            if (!query) {
                cards.forEach(function (c) {
                    c.style.display = '';
                });
            } else {
                cards.forEach(function (card) {
                    var innerRows = card.querySelectorAll('tbody tr, .nb-timeline-item');
                    if (!innerRows.length) {
                        card.style.display = U.matches(query, U.textFromElement(card)) ? '' : 'none';
                        return;
                    }
                    var any = false;
                    innerRows.forEach(function (r) {
                        if (r.style.display !== 'none') any = true;
                    });
                    card.style.display = any ? '' : 'none';
                });
            }

            var empty = document.getElementById('admin-search-empty');
            if (empty) {
                empty.classList.toggle('hidden', !query || vis > 0);
            }
        }

        U.bindInput(input, runSearch);

        document.querySelectorAll('[data-admin-panel], .admin-panel-back').forEach(function (btn) {
            btn.addEventListener('click', function () {
                setTimeout(function () {
                    runSearch((input.value || '').trim());
                }, 50);
            });
        });
    }

    function initPlanHeaderBridge() {
        if (typeof global.NebulaPlanSearch !== 'undefined') return;
        var header = document.getElementById('header-search');
        if (!header || header._nebulaPlanBridge) return;
        header._nebulaPlanBridge = true;
        U.bindInput(header, function (query) {
            if (typeof global.setPlanSearchQuery === 'function') {
                global.setPlanSearchQuery(query);
            }
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        initMisCursos();
        initProgreso();
        initDashboard();
        initTutor();
        initClase();
        initPerfil();
        initAdmin();
        initPlanHeaderBridge();
    });
})(typeof window !== 'undefined' ? window : this);
