/**
 * Nébula — módulo compartido de subida de avatar (estudiante + admin).
 */
(function (global) {
    'use strict';

    var API_FOTO = '/upload-profile-image';
    var API_FOTO_FALLBACK = '/api/perfil/foto';
    var MAX_BYTES = 5 * 1024 * 1024;
    var ALLOWED_TYPES = ['image/jpeg', 'image/jpg', 'image/pjpeg', 'image/png', 'image/webp', 'image/x-png'];

    var MSG = {
        loading: 'Actualizando foto…',
        ok: 'Imagen subida correctamente',
        format: 'Formato no permitido. Usa JPG, PNG o WEBP.',
        size: 'La imagen supera el tamaño permitido (máx. 5 MB).',
        error: 'Error al subir la imagen',
        empty: 'No se recibió ninguna imagen',
    };

    var activeBlobUrl = null;

    function profileStore() {
        return global.NebulaUserProfile || null;
    }

    function setLoadingState(on) {
        var store = profileStore();
        if (store && store.setAvatarLoading) {
            store.setAvatarLoading(on);
        }
    }

    function isAllowedType(file) {
        if (!file) return false;
        var t = (file.type || '').toLowerCase();
        if (ALLOWED_TYPES.indexOf(t) >= 0) return true;
        var name = (file.name || '').toLowerCase();
        return /\.(jpe?g|png|webp)$/i.test(name);
    }

    function validateFile(file) {
        if (!file) return { ok: false, message: MSG.empty };
        if (!isAllowedType(file)) return { ok: false, message: MSG.format };
        if (file.size > MAX_BYTES) return { ok: false, message: MSG.size };
        return { ok: true };
    }

    function parseApiResponse(res, data) {
        if (data && data.mensaje) return data.mensaje;
        if (res.status === 401) return 'Debes iniciar sesión.';
        if (res.status === 413) return MSG.size;
        if (res.status >= 500) return MSG.error;
        return MSG.error;
    }

    async function parseJsonSafe(res) {
        var text = await res.text();
        try {
            return JSON.parse(text);
        } catch (e) {
            if (text && text.indexOf('<') >= 0) return { ok: false, mensaje: MSG.error };
            return { ok: false, mensaje: text || MSG.error };
        }
    }

    function revokeBlob() {
        if (activeBlobUrl) {
            try {
                URL.revokeObjectURL(activeBlobUrl);
            } catch (e) {
                /* ignore */
            }
            activeBlobUrl = null;
        }
    }

    function applyPreview(file, selectors) {
        revokeBlob();
        var url = URL.createObjectURL(file);
        activeBlobUrl = url;
        var store = profileStore();
        if (store) {
            document.querySelectorAll('[data-nebula-avatar]').forEach(function (el) {
                if (el.tagName === 'IMG') {
                    el.src = url;
                    el.dataset.nebulaAvatarApplied = url;
                }
            });
        } else {
            (selectors || ['[data-nebula-avatar]', '.nb-avatar', '.nb-admin-avatar']).forEach(function (sel) {
                document.querySelectorAll(sel).forEach(function (el) {
                    if (el.tagName === 'IMG') {
                        el.src = url;
                    }
                });
            });
        }
        return url;
    }

    function buildProfilePatch(data) {
        if (data.usuario) {
            return data.usuario;
        }
        var ts = data.foto_actualizada_en || String(Date.now());
        return {
            avatar_url: data.avatar_url,
            avatarUrl: data.avatar_url,
            foto_perfil: data.foto_perfil,
            profile_image: data.foto_perfil || data.profile_image,
            foto_actualizada_en: ts,
            foto_version: ts,
        };
    }

    function syncGlobalFromResponse(data) {
        var store = profileStore();
        revokeBlob();
        var patch = buildProfilePatch(data);
        if (!patch.avatar_url && !patch.avatarUrl) {
            return null;
        }
        if (store) {
            return store.setProfile(patch);
        }
        var url = patch.avatarUrl || patch.avatar_url;
        var ts = patch.foto_actualizada_en || String(Date.now());
        var busted = url.split('?')[0] + '?v=' + encodeURIComponent(String(ts));
        document.querySelectorAll('[data-nebula-avatar], .nb-avatar, .nb-admin-avatar').forEach(function (el) {
            if (el.tagName === 'IMG') {
                el.removeAttribute('src');
                void el.offsetHeight;
                el.src = busted;
            }
        });
        return patch;
    }

    async function postFoto(fd) {
        var res = await fetch(API_FOTO, {
            method: 'POST',
            body: fd,
            credentials: 'same-origin',
        });
        if (res.ok) return res;
        return fetch(API_FOTO_FALLBACK, {
            method: 'POST',
            body: fd,
            credentials: 'same-origin',
        });
    }

    /**
     * @param {File} file
     * @param {{ onLoading?: Function, onSuccess?: Function, onError?: Function, previewSelectors?: string[], preview?: boolean }} hooks
     */
    async function uploadAvatar(file, hooks) {
        hooks = hooks || {};
        var validation = validateFile(file);
        if (!validation.ok) {
            if (hooks.onError) hooks.onError(validation.message);
            return { ok: false, message: validation.message };
        }

        if (hooks.preview !== false) {
            applyPreview(file, hooks.previewSelectors);
        }

        setLoadingState(true);
        if (hooks.onLoading) hooks.onLoading(MSG.loading);

        var fd = new FormData();
        fd.append('foto', file, file.name || 'avatar.jpg');

        try {
            var res = await postFoto(fd);
            var data = await parseJsonSafe(res);

            if (!res.ok || !data.ok) {
                var msg = parseApiResponse(res, data);
                revokeBlob();
                setLoadingState(false);
                if (profileStore()) {
                    await profileStore().refreshFromServer();
                }
                if (hooks.onError) hooks.onError(msg);
                return { ok: false, message: msg };
            }

            if (!data.avatar_url && data.usuario && data.usuario.avatar_url) {
                data.avatar_url = data.usuario.avatar_url;
            }

            syncGlobalFromResponse(data);
            setLoadingState(false);

            if (hooks.onSuccess) hooks.onSuccess(data.mensaje || MSG.ok, data);
            return { ok: true, data: data };
        } catch (e) {
            revokeBlob();
            setLoadingState(false);
            if (profileStore()) {
                await profileStore().refreshFromServer().catch(function () {});
            }
            var errMsg = MSG.error;
            if (hooks.onError) hooks.onError(errMsg);
            return { ok: false, message: errMsg };
        }
    }

    global.NebulaAvatarUpload = {
        upload: uploadAvatar,
        validate: validateFile,
        applyPreview: applyPreview,
        syncFromResponse: syncGlobalFromResponse,
        MSG: MSG,
        MAX_BYTES: MAX_BYTES,
    };
})(typeof window !== 'undefined' ? window : this);
