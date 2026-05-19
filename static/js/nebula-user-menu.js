/**
 * Nébula — menús desplegables de usuario, configuración y avatar.
 */
(function (global) {
    'use strict';

    var openMenu = null;
    var passwordDialog = null;

    function showToast(msg, isError) {
        var el = document.getElementById('nb-user-toast');
        if (!el) return;
        el.textContent = msg;
        el.classList.remove('hidden', 'nb-user-toast--error', 'is-visible');
        if (isError) el.classList.add('nb-user-toast--error');
        requestAnimationFrame(function () {
            el.classList.add('is-visible');
        });
        clearTimeout(showToast._tm);
        showToast._tm = setTimeout(function () {
            el.classList.remove('is-visible');
            setTimeout(function () { el.classList.add('hidden'); }, 280);
        }, 3200);
    }

    function closeMenu(menu) {
        if (!menu) return;
        var toggle = menu.querySelector('[data-nb-user-menu-toggle]');
        var panel = menu.querySelector('[data-nb-user-menu-panel]');
        menu.classList.remove('is-open');
        if (toggle) toggle.setAttribute('aria-expanded', 'false');
        if (panel) panel.setAttribute('hidden', '');
        if (openMenu === menu) openMenu = null;
    }

    function closeAllMenus(except) {
        document.querySelectorAll('.nb-user-menu.is-open').forEach(function (m) {
            if (m !== except) closeMenu(m);
        });
        document.querySelectorAll('.notificaciones-dropdown.is-open').forEach(function (d) {
            if (global.cerrarPanelNotificaciones) {
                global.cerrarPanelNotificaciones(d);
            }
        });
    }

    function openMenuEl(menu) {
        closeAllMenus(menu);
        var toggle = menu.querySelector('[data-nb-user-menu-toggle]');
        var panel = menu.querySelector('[data-nb-user-menu-panel]');
        if (!panel) return;
        panel.removeAttribute('hidden');
        menu.classList.add('is-open');
        if (toggle) toggle.setAttribute('aria-expanded', 'true');
        openMenu = menu;
    }

    function setAvatarLoading(menu, on) {
        if (!menu) {
            document.querySelectorAll('[data-nb-avatar-loader]').forEach(function (el) {
                if (on) el.removeAttribute('hidden');
                else el.setAttribute('hidden', '');
            });
            return;
        }
        var loader = menu.querySelector('[data-nb-avatar-loader]');
        if (loader) {
            if (on) loader.removeAttribute('hidden');
            else loader.setAttribute('hidden', '');
        }
    }

    function triggerFileInput(menu) {
        var input = menu && menu.querySelector('[data-nb-avatar-file]');
        if (!input) input = document.querySelector('[data-nb-avatar-file]');
        if (input) input.click();
    }

    async function removePhoto() {
        if (!confirm('¿Eliminar tu foto de perfil?')) return;
        setAvatarLoading(null, true);
        try {
            var res = await fetch('/api/perfil/foto', {
                method: 'DELETE',
                credentials: 'same-origin',
                headers: { Accept: 'application/json' },
            });
            var data = await res.json().catch(function () { return {}; });
            if (!res.ok || !data.ok) {
                showToast(data.mensaje || 'No se pudo eliminar la foto', true);
                return;
            }
            var store = global.NebulaUserProfile;
            var def = (store && store.getState().avatarDefault) || '';
            if (store) {
                store.setProfile({
                    avatarUrl: def,
                    avatar_url: def,
                    foto_version: String(Date.now()),
                });
            }
            showToast(data.mensaje || 'Foto eliminada');
        } catch (e) {
            showToast('Error al eliminar la foto', true);
        } finally {
            setAvatarLoading(null, false);
        }
    }

    function ensurePasswordDialog() {
        if (passwordDialog) return passwordDialog;
        var wrap = document.createElement('div');
        wrap.id = 'nb-password-dialog';
        wrap.className = 'nb-password-dialog';
        wrap.hidden = true;
        wrap.innerHTML =
            '<div class="nb-password-dialog__backdrop" data-nb-pw-close></div>' +
            '<div class="nb-password-dialog__card" role="document">' +
            '<h3>Cambiar contraseña</h3>' +
            '<form id="nb-password-form">' +
            '<label>Contraseña actual<input type="password" name="password_actual" required autocomplete="current-password"></label>' +
            '<label>Nueva contraseña<input type="password" name="password_nueva" required minlength="6" autocomplete="new-password"></label>' +
            '<label>Confirmar contraseña<input type="password" name="password_confirmar" required minlength="6" autocomplete="new-password"></label>' +
            '<div class="nb-password-dialog__actions">' +
            '<button type="button" class="nb-password-dialog__cancel" data-nb-pw-close>Cancelar</button>' +
            '<button type="submit" class="nb-password-dialog__submit">Guardar</button>' +
            '</div></form></div>';
        document.body.appendChild(wrap);
        passwordDialog = wrap;
        wrap.querySelectorAll('[data-nb-pw-close]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                wrap.hidden = true;
            });
        });
        wrap.querySelector('#nb-password-form').addEventListener('submit', async function (e) {
            e.preventDefault();
            var fd = new FormData(e.target);
            try {
                var res = await fetch('/api/perfil/password', {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
                    body: JSON.stringify({
                        password_actual: fd.get('password_actual'),
                        password_nueva: fd.get('password_nueva'),
                        password_confirmar: fd.get('password_confirmar'),
                    }),
                });
                var data = await res.json().catch(function () { return {}; });
                if (!res.ok || !data.ok) {
                    showToast(data.mensaje || 'No se pudo cambiar la contraseña', true);
                    return;
                }
                wrap.hidden = true;
                e.target.reset();
                showToast(data.mensaje || 'Contraseña actualizada');
            } catch (err) {
                showToast('Error de conexión', true);
            }
        });
        return wrap;
    }

    function openPasswordDialog() {
        closeAllMenus();
        var dlg = ensurePasswordDialog();
        dlg.hidden = false;
        dlg.querySelector('input')?.focus();
    }

    function handleMenuAction(action, menu) {
        closeMenu(menu);
        if (action === 'edit-profile') {
            var onPerfil = /\/perfil\/?$/.test(global.location.pathname);
            if (onPerfil) {
                document.getElementById('btn-editar-perfil')?.click();
            } else {
                global.location.href = '/perfil?editar=1';
            }
            return;
        }
        if (action === 'upload-photo') {
            triggerFileInput(menu);
            return;
        }
        if (action === 'remove-photo') {
            removePhoto();
            return;
        }
        if (action === 'change-password') {
            openPasswordDialog();
            return;
        }
        if (action === 'notifications-prefs') {
            showToast('Preferencias de notificaciones próximamente', false);
        }
    }

    function bindFileInputs() {
        document.querySelectorAll('[data-nb-avatar-file]').forEach(function (input) {
            if (input.dataset.nbAvatarBound) return;
            input.dataset.nbAvatarBound = '1';
            input.addEventListener('change', async function () {
                var file = input.files && input.files[0];
                input.value = '';
                if (!file || !global.NebulaAvatarUpload) return;
                var menu = input.closest('[data-nb-user-menu]');
                await global.NebulaAvatarUpload.upload(file, {
                    onLoading: function () { setAvatarLoading(menu, true); },
                    onSuccess: function (msg) {
                        setAvatarLoading(menu, false);
                        showToast(msg);
                    },
                    onError: function (msg) {
                        setAvatarLoading(menu, false);
                        showToast(msg, true);
                    },
                });
            });
        });
    }

    function initMenus() {
        document.querySelectorAll('[data-nb-user-menu]').forEach(function (menu) {
            if (menu.dataset.nbMenuInit) return;
            menu.dataset.nbMenuInit = '1';
            if (menu.classList.contains('nb-user-menu--sidebar-compact')) {
                menu.classList.add('nb-user-menu--align-start');
            } else if (menu.closest('header') || menu.closest('.shrink-0')) {
                menu.classList.add('nb-user-menu--align-end');
            } else {
                menu.classList.add('nb-user-menu--align-start');
            }
            var toggle = menu.querySelector('[data-nb-user-menu-toggle]');
            if (!toggle) return;
            toggle.addEventListener('click', function (e) {
                e.stopPropagation();
                if (menu.classList.contains('is-open')) {
                    closeMenu(menu);
                } else {
                    openMenuEl(menu);
                }
            });
            menu.querySelectorAll('[data-nb-menu-action]').forEach(function (btn) {
                btn.addEventListener('click', function () {
                    handleMenuAction(btn.getAttribute('data-nb-menu-action'), menu);
                });
            });
            menu.querySelector('[data-nb-user-menu-panel]')?.addEventListener('click', function (e) {
                e.stopPropagation();
            });
        });

        document.addEventListener('click', function () {
            closeAllMenus();
        });

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                closeAllMenus();
                if (passwordDialog && !passwordDialog.hidden) passwordDialog.hidden = true;
            }
        });

        bindFileInputs();
    }

    function openEditIfQuery() {
        var params = new URLSearchParams(global.location.search);
        if (params.get('editar') === '1') {
            setTimeout(function () {
                document.getElementById('btn-editar-perfil')?.click();
            }, 400);
        }
    }

    function init() {
        initMenus();
        openEditIfQuery();
        global.NebulaUserMenu = {
            showToast: showToast,
            closeAll: closeAllMenus,
            openPasswordDialog: openPasswordDialog,
        };
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})(typeof window !== 'undefined' ? window : this);
