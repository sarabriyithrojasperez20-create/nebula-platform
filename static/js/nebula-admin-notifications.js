/**
 * Nébula Admin — notificaciones en tiempo real (estado global + polling).
 * Equivalente a NotificationProvider / useNotifications() en React.
 */
(function (global) {
    'use strict';

    var API = '/api/admin/notificaciones';
    var POLL_MS = 18000;
    var STORAGE_KEY = 'nebula_admin_notif_v1';

    var state = {
        notificaciones: [],
        no_leidas: 0,
        ultimo_id: 0,
        open: false,
        polling: null,
    };
    var listeners = new Set();
    var soundEnabled = true;

    function $(id) { return document.getElementById(id); }

    function loadPrefs() {
        try {
            var raw = localStorage.getItem(STORAGE_KEY);
            if (raw) {
                var p = JSON.parse(raw);
                soundEnabled = p.sound !== false;
                state.ultimo_id = p.ultimo_id || 0;
            }
        } catch (e) { /* ignore */ }
    }

    function savePrefs() {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify({
                sound: soundEnabled,
                ultimo_id: state.ultimo_id,
            }));
        } catch (e) { /* ignore */ }
    }

    function emit() {
        var snap = {
            notificaciones: state.notificaciones.slice(),
            no_leidas: state.no_leidas,
            ultimo_id: state.ultimo_id,
        };
        listeners.forEach(function (fn) {
            try { fn(snap); } catch (e) { console.warn(e); }
        });
        document.dispatchEvent(new CustomEvent('nebula:admin-notifications', { detail: snap }));
    }

    function escapeHtml(s) {
        return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function playPing() {
        if (!soundEnabled) return;
        try {
            var ctx = new (global.AudioContext || global.webkitAudioContext)();
            var o = ctx.createOscillator();
            var g = ctx.createGain();
            o.connect(g);
            g.connect(ctx.destination);
            o.frequency.value = 880;
            g.gain.value = 0.04;
            o.start();
            o.stop(ctx.currentTime + 0.12);
        } catch (e) { /* sin audio */ }
    }

    function showToast(n) {
        var host = $('nb-notif-toast-host');
        if (!host) return;
        var el = document.createElement('div');
        el.className = 'nb-notif-toast';
        el.innerHTML =
            '<span class="material-symbols-outlined">' + escapeHtml(n.icon || 'notifications') + '</span>' +
            '<div><strong>' + escapeHtml(n.title) + '</strong><p>' + escapeHtml(n.message) + '</p></div>';
        host.appendChild(el);
        requestAnimationFrame(function () { el.classList.add('is-visible'); });
        setTimeout(function () {
            el.classList.remove('is-visible');
            setTimeout(function () { el.remove(); }, 300);
        }, 4200);
    }

    function renderBadge() {
        var badge = $('nb-notif-badge');
        if (!badge) return;
        var n = state.no_leidas;
        if (n > 0) {
            badge.textContent = n > 99 ? '99+' : String(n);
            badge.classList.remove('hidden');
            badge.classList.add('nb-notif__badge--pulse');
        } else {
            badge.classList.add('hidden');
            badge.classList.remove('nb-notif__badge--pulse');
        }
    }

    function renderList() {
        var list = $('nb-notif-list');
        if (!list) return;
        if (!state.notificaciones.length) {
            list.innerHTML = '<li class="nb-notif__empty">No hay notificaciones recientes.</li>';
            return;
        }
        list.innerHTML = state.notificaciones.map(function (n) {
            var unread = !n.read;
            var av = n.avatar
                ? '<img class="nb-notif__avatar" src="' + escapeHtml(n.avatar) + '" alt="">'
                : '<span class="nb-notif__avatar nb-notif__avatar--icon"><span class="material-symbols-outlined">' +
                  escapeHtml(n.icon || 'notifications') + '</span></span>';
            return '<li class="nb-notif__item' + (unread ? ' is-unread' : '') + '" data-id="' + n.id + '" role="listitem">' +
                av +
                '<div class="nb-notif__body">' +
                '<p class="nb-notif__title">' + escapeHtml(n.title) + '</p>' +
                '<p class="nb-notif__msg">' + escapeHtml(n.message) + '</p>' +
                '<time class="nb-notif__time">' + escapeHtml(n.relativo || '') + '</time>' +
                '</div>' +
                (unread ? '<span class="nb-notif__dot" aria-hidden="true"></span>' : '') +
                '</li>';
        }).join('');

        list.querySelectorAll('.nb-notif__item').forEach(function (item) {
            item.addEventListener('click', function () {
                var id = parseInt(item.dataset.id, 10);
                if (id) markRead(id);
            });
        });
    }

    function render() {
        renderBadge();
        renderList();
    }

    async function fetchAll(isPoll) {
        try {
            var url = API;
            if (isPoll && state.ultimo_id) {
                url += '?desde_id=' + state.ultimo_id;
            }
            var res = await fetch(url, { credentials: 'same-origin' });
            var data = await res.json().catch(function () { return {}; });
            if (!res.ok || !data.ok) return;

            var prevMax = state.ultimo_id;
            var nuevas = data.notificaciones || [];

            if (isPoll && nuevas.length) {
                nuevas.forEach(function (n) {
                    if (int(n.id) > prevMax && !n.read) {
                        showToast(n);
                        playPing();
                    }
                });
            }

            if (!isPoll) {
                state.notificaciones = nuevas;
            } else if (nuevas.length) {
                var ids = new Set(state.notificaciones.map(function (x) { return x.id; }));
                nuevas.forEach(function (n) {
                    if (!ids.has(n.id)) state.notificaciones.unshift(n);
                });
                state.notificaciones = state.notificaciones.slice(0, 50);
            }

            state.no_leidas = data.no_leidas || 0;
            if (data.ultimo_id) state.ultimo_id = data.ultimo_id;
            savePrefs();
            render();
            emit();
        } catch (e) {
            console.warn('Notificaciones admin:', e);
        }
    }

    function int(v) { return parseInt(v, 10) || 0; }

    async function markRead(id) {
        try {
            var res = await fetch(API + '/' + id + '/leer', {
                method: 'POST',
                credentials: 'same-origin',
            });
            var data = await res.json().catch(function () { return {}; });
            state.notificaciones.forEach(function (n) {
                if (n.id === id) n.read = true;
            });
            state.no_leidas = data.no_leidas != null ? data.no_leidas : Math.max(0, state.no_leidas - 1);
            render();
            emit();
        } catch (e) { /* ignore */ }
    }

    async function markAllRead() {
        try {
            await fetch(API + '/leer-todas', { method: 'POST', credentials: 'same-origin' });
            state.notificaciones.forEach(function (n) { n.read = true; });
            state.no_leidas = 0;
            render();
            emit();
        } catch (e) { /* ignore */ }
    }

    function togglePanel(open) {
        var panel = $('nb-notif-panel');
        var trigger = $('nb-notif-trigger');
        if (!panel || !trigger) return;
        state.open = open != null ? open : !state.open;
        panel.classList.toggle('hidden', !state.open);
        trigger.setAttribute('aria-expanded', state.open ? 'true' : 'false');
        if (state.open) fetchAll(false);
    }

    function startPolling() {
        if (state.polling) return;
        state.polling = setInterval(function () { fetchAll(true); }, POLL_MS);
    }

    function bind() {
        var trigger = $('nb-notif-trigger');
        var markAll = $('nb-notif-mark-all');
        var verTodas = $('nb-notif-ver-todas');

        if (trigger) {
            trigger.addEventListener('click', function (e) {
                e.stopPropagation();
                togglePanel();
            });
        }
        if (markAll) markAll.addEventListener('click', function (e) { e.stopPropagation(); markAllRead(); });
        if (verTodas) {
            verTodas.addEventListener('click', function () {
                togglePanel(false);
                if (global.location.pathname.indexOf('/admin') < 0) {
                    global.location.href = '/admin';
                }
            });
        }

        document.addEventListener('click', function (e) {
            var root = $('nb-notif-root');
            if (state.open && root && !root.contains(e.target)) togglePanel(false);
        });
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && state.open) togglePanel(false);
        });
    }

    function init() {
        if (!$('nb-notif-root')) return;
        loadPrefs();
        bind();
        fetchAll(false).then(startPolling);
    }

    global.NebulaAdminNotifications = {
        init: init,
        fetch: fetchAll,
        markRead: markRead,
        markAllRead: markAllRead,
        subscribe: function (fn) { listeners.add(fn); return function () { listeners.delete(fn); }; },
        getState: function () { return { no_leidas: state.no_leidas, notificaciones: state.notificaciones }; },
        setSoundEnabled: function (v) { soundEnabled = !!v; savePrefs(); },
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})(typeof window !== 'undefined' ? window : this);
