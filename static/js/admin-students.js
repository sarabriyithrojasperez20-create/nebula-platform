/**
 * Admin — acciones sobre estudiantes (eliminar, suspender, menú).
 */
(function () {
    'use strict';

    var pendingDeleteId = null;
    var pendingDeleteNombre = '';
    var usuariosData = [];
    var deleting = false;

    function $(id) { return document.getElementById(id); }

    function loadUsuarios() {
        var el = document.getElementById('admin-usuarios-json');
        if (!el) return [];
        try { return JSON.parse(el.textContent); } catch (e) { return []; }
    }

    function toast(msg, err) {
        var t = $('admin-student-toast');
        if (!t) {
            if (err) console.error(msg);
            return;
        }
        t.textContent = msg;
        t.className = 'nb-toast' + (err ? ' nb-toast--err' : '');
        t.classList.remove('hidden');
        clearTimeout(toast._tm);
        toast._tm = setTimeout(function () { t.classList.add('hidden'); }, 3500);
    }

    function closeMenus() {
        document.querySelectorAll('.admin-row-menu').forEach(function (m) {
            m.classList.add('hidden');
        });
    }

    function setDeleteModalBusy(on) {
        deleting = on;
        var confirm = $('admin-delete-confirm');
        var modal = $('admin-delete-modal');
        if (confirm) {
            confirm.disabled = on;
            confirm.setAttribute('aria-busy', on ? 'true' : 'false');
            confirm.textContent = on ? 'Eliminando…' : 'Eliminar';
        }
        document.querySelectorAll('[data-delete-close]').forEach(function (btn) {
            btn.disabled = on;
        });
        if (modal) modal.classList.toggle('is-loading', on);
    }

    function openDeleteModal(id, nombre) {
        if (deleting) return;
        pendingDeleteId = id;
        pendingDeleteNombre = nombre || '';
        var modal = $('admin-delete-modal');
        var nameEl = $('admin-delete-name');
        if (nameEl) nameEl.textContent = pendingDeleteNombre;
        if (modal) {
            modal.classList.remove('hidden');
            modal.setAttribute('aria-hidden', 'false');
            document.body.classList.add('nb-modal-open');
        }
        var confirm = $('admin-delete-confirm');
        if (confirm) confirm.focus();
    }

    function hideDeleteModal() {
        pendingDeleteId = null;
        pendingDeleteNombre = '';
        var modal = $('admin-delete-modal');
        if (modal) {
            modal.classList.add('hidden');
            modal.setAttribute('aria-hidden', 'true');
        }
        document.body.classList.remove('nb-modal-open');
    }

    function closeDeleteModal() {
        if (deleting) return;
        hideDeleteModal();
    }

    function removeRowFromTable(id) {
        var row = document.querySelector('tr[data-usuario-id="' + id + '"]');
        if (row) row.remove();
        usuariosData = usuariosData.filter(function (u) {
            return String(u.id_usuario) !== String(id);
        });
        var jsonEl = document.getElementById('admin-usuarios-json');
        if (jsonEl) jsonEl.textContent = JSON.stringify(usuariosData);
        var count = document.querySelector('#admin-panel-usuarios .text-body-md.text-outline');
        if (count) count.textContent = usuariosData.length + ' usuarios en el sistema';
        var detalle = document.getElementById('admin-usuario-detalle');
        if (detalle && detalle.getAttribute('data-usuario-id') === String(id)) {
            detalle.classList.add('hidden');
        }
    }

    async function parseJsonResponse(res) {
        var ct = (res.headers.get('content-type') || '').toLowerCase();
        if (ct.indexOf('application/json') >= 0) {
            return res.json();
        }
        var text = await res.text();
        console.error('[admin-students] Respuesta no JSON', res.status, text.slice(0, 300));
        if (res.status === 401 || res.status === 403) {
            throw new Error('Sesión expirada o sin permisos de administrador.');
        }
        throw new Error('El servidor devolvió una respuesta inesperada (código ' + res.status + ').');
    }

    async function confirmDelete() {
        if (!pendingDeleteId || deleting) return;
        var id = pendingDeleteId;
        setDeleteModalBusy(true);
        try {
            var res = await fetch('/api/admin/estudiantes/' + encodeURIComponent(id), {
                method: 'DELETE',
                credentials: 'same-origin',
                headers: { Accept: 'application/json' },
            });
            var data = await parseJsonResponse(res);
            if (!res.ok || !data.ok) {
                throw new Error(data.mensaje || 'No se pudo eliminar el estudiante.');
            }
            removeRowFromTable(id);
            hideDeleteModal();
            toast(data.mensaje || 'Estudiante eliminado correctamente.', false);
        } catch (err) {
            console.error('[admin-students] Error al eliminar estudiante id=' + id + ':', err);
            toast(err.message || 'No se pudo eliminar el estudiante.', true);
        } finally {
            setDeleteModalBusy(false);
        }
    }

    async function toggleSuspend(id, activo) {
        try {
            var res = await fetch('/api/admin/estudiantes/' + encodeURIComponent(id) + '/suspender', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
                body: JSON.stringify({ activo: activo }),
            });
            var data = await parseJsonResponse(res);
            if (!res.ok || !data.ok) throw new Error(data.mensaje || 'Error al actualizar estado.');
            var row = document.querySelector('tr[data-usuario-id="' + id + '"]');
            if (row) {
                var badge = row.querySelector('.admin-estado-badge');
                if (badge) {
                    badge.textContent = activo ? 'Activo' : 'Suspendido';
                    badge.className = 'admin-estado-badge ' + (activo ? 'admin-estado-badge--ok' : 'admin-estado-badge--off');
                }
            }
            var u = usuariosData.find(function (x) { return String(x.id_usuario) === String(id); });
            if (u) u.activo = activo;
            toast(activo ? 'Estudiante reactivado.' : 'Estudiante suspendido.');
        } catch (err) {
            console.error('[admin-students] suspender:', err);
            toast(err.message, true);
        }
    }

    function bindMenus() {
        document.addEventListener('click', function (e) {
            var trigger = e.target.closest('[data-admin-menu-toggle]');
            if (trigger) {
                e.stopPropagation();
                var menu = trigger.parentElement.querySelector('.admin-row-menu');
                closeMenus();
                if (menu) menu.classList.toggle('hidden');
                return;
            }
            if (!e.target.closest('.admin-row-menu')) closeMenus();
        });

        document.querySelectorAll('[data-admin-action]').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.stopPropagation();
                closeMenus();
                var action = btn.getAttribute('data-admin-action');
                var id = btn.getAttribute('data-usuario-id');
                var nombre = btn.getAttribute('data-usuario-nombre') || '';
                if (action === 'ver') {
                    var ver = document.querySelector('.admin-ver-usuario[data-usuario-id="' + id + '"]');
                    if (ver) ver.click();
                } else if (action === 'eliminar') {
                    openDeleteModal(id, nombre);
                } else if (action === 'suspender') {
                    toggleSuspend(id, false);
                } else if (action === 'reactivar') {
                    toggleSuspend(id, true);
                }
            });
        });
    }

    function bindDeleteModal() {
        document.querySelectorAll('[data-delete-close]').forEach(function (el) {
            el.addEventListener('click', closeDeleteModal);
        });
        var confirm = $('admin-delete-confirm');
        if (confirm) confirm.addEventListener('click', confirmDelete);
        var modal = $('admin-delete-modal');
        if (modal) {
            modal.addEventListener('click', function (e) {
                if (e.target === modal.querySelector('.nb-modal__backdrop')) closeDeleteModal();
            });
        }
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && modal && !modal.classList.contains('hidden')) {
                closeDeleteModal();
            }
        });
    }

    function init() {
        usuariosData = loadUsuarios();
        bindMenus();
        bindDeleteModal();
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else init();
})();
