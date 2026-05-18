/**
 * Admin — acciones sobre estudiantes (eliminar, suspender, menú).
 */
(function () {
    'use strict';

    var pendingDeleteId = null;
    var usuariosData = [];

    function $(id) { return document.getElementById(id); }

    function loadUsuarios() {
        var el = document.getElementById('admin-usuarios-json');
        if (!el) return [];
        try { return JSON.parse(el.textContent); } catch (e) { return []; }
    }

    function toast(msg, err) {
        var t = $('admin-student-toast');
        if (!t) {
            if (err) alert(msg);
            return;
        }
        t.textContent = msg;
        t.className = 'nb-toast' + (err ? ' nb-toast--err' : '');
        t.classList.remove('hidden');
        clearTimeout(toast._tm);
        toast._tm = setTimeout(function () { t.classList.add('hidden'); }, 3000);
    }

    function closeMenus() {
        document.querySelectorAll('.admin-row-menu').forEach(function (m) {
            m.classList.add('hidden');
        });
    }

    function openDeleteModal(id, nombre) {
        pendingDeleteId = id;
        var modal = $('admin-delete-modal');
        var nameEl = $('admin-delete-name');
        if (nameEl) nameEl.textContent = nombre || '';
        if (modal) {
            modal.classList.remove('hidden');
            document.body.classList.add('nb-modal-open');
        }
    }

    function closeDeleteModal() {
        pendingDeleteId = null;
        var modal = $('admin-delete-modal');
        if (modal) modal.classList.add('hidden');
        document.body.classList.remove('nb-modal-open');
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
    }

    async function confirmDelete() {
        if (!pendingDeleteId) return;
        var btn = $('admin-delete-confirm');
        if (btn) btn.disabled = true;
        try {
            var res = await fetch('/api/admin/estudiantes/' + pendingDeleteId, {
                method: 'DELETE',
                credentials: 'same-origin',
            });
            var data = await res.json().catch(function () { return {}; });
            if (!res.ok || !data.ok) throw new Error(data.mensaje || 'No se pudo eliminar.');
            removeRowFromTable(pendingDeleteId);
            closeDeleteModal();
            toast('Estudiante eliminado correctamente.');
        } catch (err) {
            toast(err.message, true);
        } finally {
            if (btn) btn.disabled = false;
        }
    }

    async function toggleSuspend(id, activo) {
        try {
            var res = await fetch('/api/admin/estudiantes/' + id + '/suspender', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ activo: activo }),
            });
            var data = await res.json().catch(function () { return {}; });
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
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && $('admin-delete-modal') && !$('admin-delete-modal').classList.contains('hidden')) {
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
