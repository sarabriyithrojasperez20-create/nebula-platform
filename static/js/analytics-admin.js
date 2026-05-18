/**
 * Analytics admin: filtro por periodo (API) + estados de carga.
 */
(function (win) {
    'use strict';

    win = win || (typeof window !== 'undefined' ? window : this);
    var meta = {};
    try {
        var metaEl = document.getElementById('analytics-meta-json');
        meta = metaEl ? JSON.parse(metaEl.textContent) : {};
    } catch (e) {
        meta = {};
    }

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

    function setLoading(on) {
        var root = $('analytics-root');
        var loading = $('analytics-loading');
        var periodo = $('analytics-periodo');
        var exportBtn = $('analytics-exportar');
        if (root) root.classList.toggle('aa-is-loading', !!on);
        if (loading) loading.classList.toggle('hidden', !on);
        if (periodo) periodo.disabled = !!on;
        if (exportBtn) exportBtn.disabled = !!on;
    }

    function updatePeriodLabel(etiqueta) {
        document.querySelectorAll('[data-analytics-period-label]').forEach(function (el) {
            el.textContent = etiqueta || '';
        });
    }

    function renderKpis(m) {
        if (!m) return;
        document.querySelectorAll('[data-kpi]').forEach(function (el) {
            var key = el.getAttribute('data-kpi');
            if (m[key] !== undefined) el.textContent = m[key];
        });
        var hintTotal = document.querySelector('[data-kpi-hint="total_estudiantes"]');
        if (hintTotal && m.total_estudiantes !== undefined) {
            hintTotal.textContent = m.total_estudiantes;
        }
        var hintCursos = document.querySelector('[data-kpi-hint="cursos_completados"]');
        if (hintCursos && m.cursos_completados !== undefined) {
            hintCursos.textContent = m.cursos_completados;
        }
    }

    function renderBarras(barras) {
        var container = $('analytics-barras');
        if (!container || !barras) return;
        if (!barras.length) {
            container.innerHTML = '<p class="aa-empty" style="grid-column:1/-1">Sin actividad en el periodo.</p>';
            return;
        }
        container.innerHTML = barras
            .map(function (b) {
                return (
                    '<div class="aa-bar-chart__col">' +
                    '<div class="aa-bar-chart__bar" style="height:' +
                    (b.altura || 12) +
                    '%;" title="' +
                    escapeHtml(String(b.valor || '')) +
                    '"></div>' +
                    '<span>' +
                    escapeHtml(b.etiqueta) +
                    '</span></div>'
                );
            })
            .join('');
    }

    function renderActividad(items) {
        var list = $('analytics-actividad');
        if (!list) return;
        if (!items || !items.length) {
            list.innerHTML = '<li class="aa-empty">Sin actividad en este periodo.</li>';
            return;
        }
        list.innerHTML = items
            .map(function (act) {
                return (
                    '<li><span class="material-symbols-outlined">' +
                    escapeHtml(act.icono) +
                    '</span><div><strong>' +
                    escapeHtml(act.titulo) +
                    '</strong><p>' +
                    escapeHtml(act.descripcion) +
                    '</p></div><time>' +
                    escapeHtml(act.relativo) +
                    '</time></li>'
                );
            })
            .join('');
    }

    function renderEstudiantes(filas) {
        var tbody = $('analytics-estudiantes-body');
        if (!tbody) return;
        if (!filas || !filas.length) {
            tbody.innerHTML =
                '<tr><td colspan="5" class="aa-empty">Sin datos de rendimiento en este periodo.</td></tr>';
            return;
        }
        tbody.innerHTML = filas
            .map(function (f) {
                var estado = (f.estado || 'pendiente').toLowerCase();
                return (
                    '<tr><td><div class="aa-table-user">' +
                    '<img class="aa-table-user__avatar aa-table-user__avatar--img" src="' +
                    escapeHtml(f.avatar_url) +
                    '" alt="' +
                    escapeHtml(f.nombre) +
                    '" data-avatar-fallback="https://lh3.googleusercontent.com/aida-public/AB6AXuBlwoGAr4OcQHRwHR-lcqSiVtRczHOqU4jSeFWxNy7vEHCCeSC_b1mKIRSSHlj-Uah3OA6pbCC0gL6OOi-k9lVNngXgPGI8SMaNT5qfa2MvmU_9BDlAs2sFfycz7MTtG1JhdpkytvtTvG0qlm796rX77xURSs3c0qR1vFJfRms9-GFoWgsllXenDXJ4WbdK-n98_bzU82KSmO2gh53b7AdV-AawOUYUnwE3qSGyNOAiyNmiNSUmRB79gyWgUowkW0vRWKOHp2m4EFo" onerror="if(this.dataset.avatarFallback){this.onerror=null;this.src=this.dataset.avatarFallback;}" />' +
                    '<div><strong>' +
                    escapeHtml(f.nombre) +
                    '</strong><small>#' +
                    f.id_usuario +
                    '</small></div></div></td>' +
                    '<td><span class="aa-pill">' +
                    (f.lecciones_periodo || 0) +
                    '</span></td>' +
                    '<td><span class="aa-pill">' +
                    (f.quizzes_periodo || 0) +
                    '</span></td>' +
                    '<td><div class="aa-table-progress"><i style="width:' +
                    (f.progreso || 0) +
                    '%"></i></div><span>' +
                    (f.progreso || 0) +
                    '%</span></td>' +
                    '<td><span class="aa-status aa-status--' +
                    estado +
                    '">' +
                    escapeHtml(f.estado) +
                    '</span></td></tr>'
                );
            })
            .join('');
    }

    function applyAnalytics(data) {
        if (!data) return;
        var m = data.metricas || {};
        renderKpis(m);
        renderBarras(data.barras_semana);
        renderActividad(data.actividad_reciente);
        renderEstudiantes(data.rendimiento_estudiantes);
        if (data.periodo) {
            meta.periodo = data.periodo;
            updatePeriodLabel(data.periodo.etiqueta);
        }
    }

    async function loadAnalytics(dias) {
        setLoading(true);
        try {
            var res = await fetch('/api/admin/analytics?dias=' + encodeURIComponent(dias), {
                credentials: 'same-origin',
            });
            var payload = await res.json().catch(function () {
                return {};
            });
            if (!res.ok || !payload.ok) {
                throw new Error(payload.mensaje || 'No se pudieron cargar los datos.');
            }
            applyAnalytics(payload.analytics);
        } catch (err) {
            console.warn(err);
            if (window.NebulaAdminExport && window.NebulaAdminExport.toast) {
                window.NebulaAdminExport.toast(err.message, true);
            }
        } finally {
            setLoading(false);
        }
    }

    function getPeriodoActual() {
        var sel = $('analytics-periodo');
        var dias = sel ? parseInt(sel.value, 10) : 30;
        if (meta.periodo && meta.periodo.dias === dias) {
            return meta.periodo;
        }
        var label = sel ? sel.options[sel.selectedIndex].text : 'Último mes';
        return { dias: dias, etiqueta: label, desde: '', hasta: '' };
    }

    function bind() {
        document.querySelectorAll('[data-admin-open-panel]').forEach(function (link) {
            link.addEventListener('click', function () {
                var panel = link.getAttribute('data-admin-open-panel');
                if (!panel) return;
                try {
                    sessionStorage.setItem('nebula_admin_panel', panel);
                } catch (err) {
                    /* ignore */
                }
            });
        });

        var periodo = $('analytics-periodo');
        if (periodo) {
            periodo.addEventListener('change', function () {
                var label = periodo.options[periodo.selectedIndex].text;
                updatePeriodLabel(label);
                loadAnalytics(periodo.value);
            });
        }

        var fab = $('analytics-fab');
        if (fab) {
            fab.addEventListener('click', function () {
                window.location.href = fab.getAttribute('data-href') || '/admin';
            });
        }

        var exportUno = $('analytics-exportar-uno');
        if (exportUno && window.NebulaAdminExport) {
            exportUno.addEventListener('click', function (e) {
                e.preventDefault();
                if (window.NebulaAdminExport.openModal) {
                    window.NebulaAdminExport.openModal(getPeriodoActual());
                }
            });
        }

        win.NebulaAnalyticsAdmin = {
            load: loadAnalytics,
            getPeriodo: getPeriodoActual,
            apply: applyAnalytics,
        };
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bind);
    } else {
        bind();
    }
})(typeof window !== 'undefined' ? window : this);
