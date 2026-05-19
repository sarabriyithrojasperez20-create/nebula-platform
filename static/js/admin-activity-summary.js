/**
 * Resumen de actividad — dashboard admin (gráfico + KPIs + filtro de periodo).
 */
(function () {
    'use strict';

    function $(id) {
        return document.getElementById(id);
    }

    function escapeHtml(s) {
        return String(s || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function loadBoot() {
        var el = $('admin-resumen-actividad-boot');
        if (!el) return null;
        try {
            return JSON.parse(el.textContent);
        } catch (e) {
            return null;
        }
    }

    function renderChart(data) {
        var chart = $('admin-resumen-chart');
        var empty = $('admin-resumen-empty');
        var wrap = $('admin-resumen-chart-wrap');
        if (!chart || !empty) return;

        if (data.vacio || !data.columnas || !data.columnas.length) {
            chart.innerHTML = '';
            chart.classList.add('hidden');
            empty.classList.remove('hidden');
            return;
        }

        chart.classList.remove('hidden');
        empty.classList.add('hidden');

        chart.innerHTML = data.columnas
            .map(function (col) {
                var segs = (col.segmentos_visibles || [])
                    .map(function (s) {
                        return (
                            '<div class="admin-activity-chart__seg" style="height:' +
                            s.altura_pct +
                            '%;background:' +
                            escapeHtml(s.color) +
                            ';" title="' +
                            escapeHtml(s.label + ': ' + s.valor) +
                            '"></div>'
                        );
                    })
                    .join('');
                var stackH = col.altura_pct || 12;
                return (
                    '<div class="admin-activity-chart__col">' +
                    '<div class="admin-activity-chart__stack" style="height:' +
                    stackH +
                    '%;" title="Total: ' +
                    (col.total || 0) +
                    '">' +
                    segs +
                    '</div>' +
                    '<span class="admin-activity-chart__label">' +
                    escapeHtml(col.etiqueta) +
                    '</span></div>'
                );
            })
            .join('');
    }

    function renderIndicadores(ind) {
        if (!ind) return;
        document.querySelectorAll('[data-ind]').forEach(function (el) {
            var key = el.getAttribute('data-ind');
            if (ind[key] === undefined) return;
            if (key === 'promedio_aprobacion') {
                el.textContent = ind[key] + '%';
            } else {
                el.textContent = ind[key];
            }
        });
    }

    function renderLeyenda(leyenda) {
        var box = $('admin-resumen-leyenda');
        if (!box) return;
        if (!leyenda || !leyenda.length) {
            box.innerHTML = '';
            return;
        }
        box.innerHTML = leyenda
            .map(function (item) {
                return (
                    '<span class="admin-activity-legend__item">' +
                    '<span class="admin-activity-legend__dot" style="background:' +
                    escapeHtml(item.color) +
                    '"></span>' +
                    escapeHtml(item.label) +
                    '</span>'
                );
            })
            .join('');
    }

    function renderActividadReciente(items) {
        var list = $('admin-actividad-reciente-list');
        if (!list) return;
        if (!items || !items.length) {
            list.innerHTML =
                '<p class="text-sm text-[var(--nb-text-muted)]">Sin actividad registrada en este periodo.</p>';
            return;
        }
        list.innerHTML = items
            .map(function (act) {
                return (
                    '<div class="nb-timeline-item">' +
                    '<div class="nb-timeline-icon">' +
                    '<span class="material-symbols-outlined text-[18px]">' +
                    escapeHtml(act.icono) +
                    '</span></div><div>' +
                    '<p class="text-sm font-semibold text-[var(--nb-text)]">' +
                    escapeHtml(act.titulo) +
                    '</p>' +
                    '<p class="text-xs text-[var(--nb-text-secondary)] mt-0.5">' +
                    escapeHtml(act.descripcion) +
                    '</p>' +
                    '<p class="text-[10px] font-bold text-[var(--nb-text-muted)] mt-1 uppercase tracking-wide">' +
                    escapeHtml(act.relativo) +
                    '</p></div></div>'
                );
            })
            .join('');
    }

    function applyResumen(data) {
        if (!data) return;
        var label = $('admin-resumen-periodo-label');
        if (label && data.periodo) {
            label.textContent = data.periodo.etiqueta || 'Actividad de la plataforma';
        }
        renderChart(data);
        renderIndicadores(data.indicadores);
        renderLeyenda(data.leyenda);
        renderActividadReciente(data.actividad_reciente);
    }

    function setLoading(on) {
        var card = $('admin-resumen-actividad-card');
        var sel = $('admin-resumen-periodo');
        if (card) card.classList.toggle('is-loading', !!on);
        if (sel) sel.disabled = !!on;
    }

    function fetchResumen(periodo) {
        setLoading(true);
        return fetch(
            '/api/admin/resumen-actividad?periodo=' + encodeURIComponent(periodo),
            {
                headers: { Accept: 'application/json' },
                credentials: 'same-origin',
            }
        )
            .then(function (r) {
                return r.json().then(function (body) {
                    if (!r.ok || !body.ok) {
                        throw new Error(body.mensaje || 'No se pudo cargar el resumen.');
                    }
                    return body.resumen;
                });
            })
            .finally(function () {
                setLoading(false);
            });
    }

    function init() {
        var sel = $('admin-resumen-periodo');
        if (!sel) return;

        applyResumen(loadBoot());

        sel.addEventListener('change', function () {
            fetchResumen(sel.value)
                .then(applyResumen)
                .catch(function (err) {
                    console.error(err);
                });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
