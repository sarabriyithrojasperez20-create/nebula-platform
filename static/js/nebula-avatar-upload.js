/**
 * Nébula — módulo compartido de subida de avatar (estudiante + admin).
 * Equivalente a useProfileImage() para la app Flask multi-página.
 */
(function (global) {
    'use strict';

    var API_FOTO = '/api/perfil/foto';
    var MAX_BYTES = 5 * 1024 * 1024;
    var ALLOWED_TYPES = ['image/jpeg', 'image/jpg', 'image/pjpeg', 'image/png', 'image/webp', 'image/x-png'];

    var MSG = {
        loading: 'Actualizando foto…',
        ok: 'Imagen subida correctamente',
        format: 'Formato no permitido',
        size: 'La imagen supera el tamaño permitido',
        error: 'Error al subir la imagen',
        empty: 'No se recibió ninguna imagen',
    };

    function profileStore() {
        return global.NebulaUserProfile || null;
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

    function applyPreview(file, selectors) {
        var url = URL.createObjectURL(file);
        (selectors || ['[data-nebula-avatar]', '.nb-avatar', '.nb-admin-avatar']).forEach(function (sel) {
            document.querySelectorAll(sel).forEach(function (el) {
                if (el.tagName === 'IMG') el.src = url;
                else {
                    el.style.backgroundImage = 'url("' + url.replace(/"/g, '\\"') + '")';
                    el.style.backgroundSize = 'cover';
                    el.style.backgroundPosition = 'center';
                }
            });
        });
        return url;
    }

    function syncGlobalFromResponse(data) {
        var store = profileStore();
        if (!store) return;
        if (data.usuario) {
            store.setProfile(data.usuario);
        } else if (data.avatar_url) {
            store.setProfile({
                avatarUrl: data.avatar_url,
                avatar_url: data.avatar_url,
                foto_version: data.foto_actualizada_en || String(Date.now()),
            });
        }
    }

    /**
     * @param {File} file
     * @param {{ onLoading?: Function, onSuccess?: Function, onError?: Function, previewSelectors?: string[] }} hooks
     */
    async function uploadAvatar(file, hooks) {
        hooks = hooks || {};
        var validation = validateFile(file);
        if (!validation.ok) {
            if (hooks.onError) hooks.onError(validation.message);
            return { ok: false, message: validation.message };
        }

        var blobUrl = null;
        if (hooks.preview !== false) {
            blobUrl = applyPreview(file, hooks.previewSelectors);
        }

        if (hooks.onLoading) hooks.onLoading(MSG.loading);

        var fd = new FormData();
        fd.append('foto', file, file.name || 'avatar.jpg');

        try {
            var res = await fetch(API_FOTO, {
                method: 'POST',
                body: fd,
                credentials: 'same-origin',
            });
            var data = await parseJsonSafe(res);

            if (!res.ok || !data.ok) {
                var msg = parseApiResponse(res, data);
                if (blobUrl && profileStore()) profileStore().refreshFromServer();
                if (hooks.onError) hooks.onError(msg);
                return { ok: false, message: msg };
            }

            syncGlobalFromResponse(data);
            if (hooks.onSuccess) hooks.onSuccess(data.mensaje || MSG.ok, data);
            return { ok: true, data: data };
        } catch (e) {
            if (profileStore()) profileStore().refreshFromServer().catch(function () {});
            var errMsg = MSG.error;
            if (hooks.onError) hooks.onError(errMsg);
            return { ok: false, message: errMsg };
        }
    }

    global.NebulaAvatarUpload = {
        upload: uploadAvatar,
        validate: validateFile,
        applyPreview: applyPreview,
        MSG: MSG,
        MAX_BYTES: MAX_BYTES,
    };
})(typeof window !== 'undefined' ? window : this);
