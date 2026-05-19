/**
 * Estado global del perfil del estudiante (Context + localStorage + eventos).
 */
(function (global) {
    'use strict';

    function storageKey() {
        var uid = state.id_usuario || 0;
        return 'nebula_user_profile_v1_u' + uid;
    }
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
            var raw = localStorage.getItem(storageKey());
            return raw ? JSON.parse(raw) : null;
        } catch (e) {
            return null;
        }
    }

    function saveStorage() {
        try {
            localStorage.setItem(storageKey(), JSON.stringify(state));
        } catch (e) {
            /* quota */
        }
    }

    /**
     * Añade ?v= o &v= para evitar caché del navegador.
     * @param {string} url
     * @param {string|number} [forceVersion] — timestamp explícito tras subida
     */
    function bustUrl(url, forceVersion) {
        if (!url || url.indexOf('data:') === 0 || url.indexOf('blob:') === 0) {
            return url;
        }
        var v =
            forceVersion != null && forceVersion !== ''
                ? String(forceVersion)
                : state.foto_version || String(Date.now());
        var base = url.split('?')[0].split('#')[0];
        return base + '?v=' + encodeURIComponent(v);
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

    function assignImgSrc(img, src, opts) {
        if (!img || img.tagName !== 'IMG' || !src) return;
        opts = opts || {};
        var next = bustUrl(src, opts.forceVersion);
        var prevBase = (img.dataset.nebulaAvatarApplied || '').split('?')[0];
        var nextBase = next.split('?')[0];

        if (opts.force || prevBase !== nextBase || img.src !== next) {
            if (opts.force && img.src && prevBase === nextBase) {
                img.removeAttribute('src');
                void img.offsetHeight;
            }
            img.src = next;
            img.dataset.nebulaAvatarApplied = next;
            bindAvatarFallback(img);
        }
    }

    function applyAvatarToDom(url, opts) {
        opts = opts || {};
        var forceVersion = opts.force ? opts.forceVersion || String(Date.now()) : null;
        var src = bustUrl(url || state.avatarUrl || state.avatarDefault, forceVersion);
        if (!src) return;

        document.querySelectorAll('[data-nebula-avatar]').forEach(function (el) {
            if (el.tagName === 'IMG') {
                if (!el.getAttribute('data-avatar-fallback') && state.avatarDefault) {
                    el.setAttribute('data-avatar-fallback', state.avatarDefault);
                }
                assignImgSrc(el, src, { force: opts.force, forceVersion: forceVersion });
            } else {
                el.style.backgroundImage =
                    'url("' + src.replace(/"/g, '\\"') + '")';
                el.style.backgroundSize = 'cover';
                el.style.backgroundPosition = 'center';
            }
        });

        document.querySelectorAll('.perfil-avatar-link').forEach(function (el) {
            if (el.tagName === 'IMG') {
                assignImgSrc(el, src, { force: opts.force, forceVersion: forceVersion });
            } else {
                var inner = el.querySelector('[data-nebula-avatar], img');
                if (inner && inner.tagName === 'IMG') {
                    assignImgSrc(inner, src, { force: opts.force, forceVersion: forceVersion });
                } else {
                    el.style.backgroundImage =
                        'url("' + src.replace(/"/g, '\\"') + '")';
                    el.style.backgroundSize = 'cover';
                    el.style.backgroundPosition = 'center';
                }
            }
        });

        document.querySelectorAll('.nb-avatar, .nb-admin-avatar').forEach(function (img) {
            assignImgSrc(img, src, { force: opts.force, forceVersion: forceVersion });
        });

        [
            '#perfil-avatar-main',
            '#perfil-modal-avatar',
            '#admin-perfil-avatar',
            '.perfil-edit-aside__avatar',
            '.perfil-header img',
            '.perfil-avatar-link img',
        ].forEach(function (sel) {
            document.querySelectorAll(sel).forEach(function (img) {
                assignImgSrc(img, src, { force: opts.force, forceVersion: forceVersion });
            });
        });
    }

    function setAvatarLoading(on) {
        document.querySelectorAll('[data-nebula-avatar]').forEach(function (el) {
            if (el.tagName === 'IMG') {
                el.classList.toggle('nebula-avatar--loading', !!on);
                el.setAttribute('aria-busy', on ? 'true' : 'false');
            }
        });
    }

    function normalizePatch(data) {
        if (!data || typeof data !== 'object') return {};
        var patch = Object.assign({}, data);
        if (patch.avatar_url && !patch.avatarUrl) {
            patch.avatarUrl = patch.avatar_url;
        }
        if (patch.profile_image && !patch.foto_perfil) {
            patch.foto_perfil = patch.profile_image;
        }
        if (patch.foto_actualizada_en) {
            patch.foto_version = patch.foto_actualizada_en;
        } else if (patch.avatarUrl || patch.avatar_url) {
            patch.foto_version = String(Date.now());
        }
        return patch;
    }

    function setProfile(patch) {
        if (!patch || typeof patch !== 'object') return getState();
        patch = normalizePatch(patch);

        var avatarChanged = !!(patch.avatarUrl || patch.avatar_url);
        var prevAvatarBase = (state.avatarUrl || '').split('?')[0];

        Object.assign(state, patch);
        if (patch.avatarUrl || patch.avatar_url) {
            state.avatarUrl = patch.avatarUrl || patch.avatar_url;
        }
        if (avatarChanged) {
            if (!patch.foto_version && !patch.foto_actualizada_en) {
                state.foto_version = String(Date.now());
            }
        }

        saveStorage();

        var force =
            avatarChanged &&
            state.avatarUrl.split('?')[0] !== prevAvatarBase;
        applyAvatarToDom(state.avatarUrl, {
            force: force || avatarChanged,
            forceVersion: state.foto_version,
        });
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

        var stored = loadStorage();

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
        setAvatarLoading: setAvatarLoading,
        refreshFromServer: refreshFromServer,
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})(typeof window !== 'undefined' ? window : this);
