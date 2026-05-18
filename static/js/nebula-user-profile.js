/**
 * Estado global del perfil del estudiante (Context + localStorage + eventos).
 * Equivalente a useUserProfile() / Zustand para la app Flask multi-página.
 */
(function (global) {
    'use strict';

    var STORAGE_KEY = 'nebula_user_profile_v1';
    var listeners = new Set();
    var state = {
        id_usuario: null,
        nombre_completo: '',
        username: '',
        correo: '',
        sobre_mi: '',
        nivel_academico: '',
        preferencia_dominante: 'visual',
        avatarUrl: '',
        avatarDefault: '',
        foto_version: '',
    };

    function parseBoot() {
        var el = document.getElementById('nebula-user-boot');
        if (!el) return null;
        try {
            return JSON.parse(el.textContent);
        } catch (e) {
            return null;
        }
    }

    function loadStorage() {
        try {
            var raw = localStorage.getItem(STORAGE_KEY);
            return raw ? JSON.parse(raw) : null;
        } catch (e) {
            return null;
        }
    }

    function saveStorage() {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
        } catch (e) {
            /* quota */
        }
    }

    function bustUrl(url) {
        if (!url || url.indexOf('data:') === 0 || url.indexOf('blob:') === 0) {
            return url;
        }
        var v = state.foto_version || Date.now();
        var sep = url.indexOf('?') >= 0 ? '&' : '?';
        return url.split('?')[0] + sep + 'v=' + encodeURIComponent(String(v));
    }

    function getState() {
        return Object.assign({}, state);
    }

    function emit() {
        var snapshot = getState();
        listeners.forEach(function (fn) {
            try {
                fn(snapshot);
            } catch (e) {
                console.warn(e);
            }
        });
        document.dispatchEvent(
            new CustomEvent('nebula:profile-updated', { detail: snapshot })
        );
    }

    function bindAvatarFallback(img) {
        if (!img || img.tagName !== 'IMG' || img.dataset.nebulaFallbackBound) return;
        var fallback = img.getAttribute('data-avatar-fallback') || state.avatarDefault;
        if (!fallback) return;
        img.dataset.nebulaFallbackBound = '1';
        img.addEventListener('error', function onErr() {
            if (fallback && img.src !== fallback) {
                img.src = fallback;
            }
        });
    }

    function applyAvatarToDom(url) {
        var src = bustUrl(url || state.avatarUrl || state.avatarDefault);
        if (!src) return;
        var safeSrc = src;
        var fallback = state.avatarDefault || '';

        document.querySelectorAll('[data-nebula-avatar]').forEach(function (el) {
            if (el.tagName === 'IMG') {
                if (!el.getAttribute('data-avatar-fallback') && fallback) {
                    el.setAttribute('data-avatar-fallback', fallback);
                }
                el.src = safeSrc;
                bindAvatarFallback(el);
            } else {
                el.style.backgroundImage = 'url("' + safeSrc.replace(/"/g, '\\"') + '")';
                el.style.backgroundSize = 'cover';
                el.style.backgroundPosition = 'center';
            }
        });

        document.querySelectorAll('.perfil-avatar-link').forEach(function (el) {
            if (el.tagName === 'IMG') {
                el.src = src;
            } else {
                var inner = el.querySelector('[data-nebula-avatar], img');
                if (inner && inner.tagName === 'IMG') inner.src = src;
                else {
                    el.style.backgroundImage = 'url("' + src.replace(/"/g, '\\"') + '")';
                    el.style.backgroundSize = 'cover';
                    el.style.backgroundPosition = 'center';
                }
            }
        });

        document.querySelectorAll('.nb-avatar, .nb-admin-avatar').forEach(function (img) {
            if (img && img.tagName === 'IMG') img.src = src;
        });

        [
            '#perfil-avatar-main',
            '#perfil-modal-avatar',
            '.perfil-edit-aside__avatar',
            '.perfil-header img',
            '.perfil-avatar-link img',
        ].forEach(function (sel) {
            document.querySelectorAll(sel).forEach(function (img) {
                if (img && img.tagName === 'IMG') img.src = src;
            });
        });
    }

    function setProfile(patch) {
        if (!patch || typeof patch !== 'object') return getState();
        if (patch.avatar_url) {
            patch.avatarUrl = patch.avatar_url;
        }
        if (patch.foto_actualizada_en) {
            patch.foto_version = patch.foto_actualizada_en;
        }
        Object.assign(state, patch);
        if (patch.avatarUrl || patch.avatar_url) {
            state.avatarUrl = patch.avatarUrl || patch.avatar_url;
        }
        saveStorage();
        applyAvatarToDom(state.avatarUrl);
        emit();
        return getState();
    }

    function subscribe(fn) {
        if (typeof fn === 'function') listeners.add(fn);
        return function () {
            listeners.delete(fn);
        };
    }

    function init() {
        var boot = parseBoot();
        var stored = loadStorage();

        if (boot) {
            state.avatarDefault = boot.avatarDefault || '';
            var u = boot.user || {};
            state.id_usuario = u.id_usuario || boot.id_usuario || null;
            state.nombre_completo = u.nombre_completo || '';
            state.username = u.username || '';
            state.correo = u.correo || '';
            state.sobre_mi = u.sobre_mi || '';
            state.nivel_academico = u.nivel_academico || '';
            state.preferencia_dominante =
                (u.preferencias_aprendizaje && u.preferencias_aprendizaje.dominante) ||
                u.preferencia_dominante ||
                'visual';
            state.avatarUrl = boot.avatarUrl || u.avatar_url || '';
            state.foto_version = boot.foto_version || u.foto_actualizada_en || '';
        }

        if (stored && stored.id_usuario === state.id_usuario && stored.avatarUrl) {
            if (!boot || !boot.avatarUrl) {
                state.avatarUrl = stored.avatarUrl;
            }
            if (stored.foto_version) state.foto_version = stored.foto_version;
        }

        if (!state.avatarUrl && state.avatarDefault) {
            state.avatarUrl = state.avatarDefault;
        }

        applyAvatarToDom(state.avatarUrl || state.avatarDefault);
        saveStorage();
    }

    async function refreshFromServer() {
        try {
            var res = await fetch('/api/perfil/me', { credentials: 'same-origin' });
            if (!res.ok) return getState();
            var data = await res.json();
            if (data.ok && data.usuario) {
                return setProfile(data.usuario);
            }
        } catch (e) {
            /* offline */
        }
        return getState();
    }

    global.NebulaUserProfile = {
        init: init,
        getState: getState,
        setProfile: setProfile,
        subscribe: subscribe,
        applyAvatarToDom: applyAvatarToDom,
        bustUrl: bustUrl,
        refreshFromServer: refreshFromServer,
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})(typeof window !== 'undefined' ? window : this);
