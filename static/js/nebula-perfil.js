/**

 * Nébula — edición de perfil (modal premium, foto, API Flask + estado global)

 */

(function (global) {

    'use strict';



    const API_PERFIL = '/api/perfil';

    const API_FOTO = '/api/perfil/foto';



    let config = {};

    let fotoSeleccionada = null;

    let previewUrl = null;

    let fotoSubidaEnSesion = false;



    function $(id) {

        return document.getElementById(id);

    }



    function profileStore() {

        return global.NebulaUserProfile || null;

    }



    function parseConfig() {

        try {

            const el = document.getElementById('nebula-perfil-config');

            return el ? JSON.parse(el.textContent) : {};

        } catch {

            return {};

        }

    }



    function mostrarToast(mensaje, esError) {

        const toast = $('perfil-toast');

        if (!toast) return;

        toast.textContent = mensaje;

        toast.classList.remove('hidden', 'perfil-toast--ok', 'perfil-toast--error');

        toast.classList.add(esError ? 'perfil-toast--error' : 'perfil-toast--ok');

    }



    function syncGlobalProfile(u) {

        const store = profileStore();

        if (!store || !u) return;

        const ts = u.foto_actualizada_en || String(Date.now());

        store.setProfile({

            id_usuario: u.id_usuario,

            nombre_completo: u.nombre_completo,

            username: u.username,

            correo: u.correo,

            sobre_mi: u.sobre_mi,

            nivel_academico: u.nivel_academico,

            preferencia_dominante:

                u.preferencia_dominante ||

                (u.preferencias_aprendizaje && u.preferencias_aprendizaje.dominante),

            avatar_url: u.avatar_url,

            avatarUrl: u.avatar_url,

            foto_perfil: u.foto_perfil || u.profile_image,

            foto_actualizada_en: ts,

            foto_version: ts,

        });

    }



    function aplicarAvatarGlobal(uOrUrl) {

        if (uOrUrl && typeof uOrUrl === 'object') {

            syncGlobalProfile(uOrUrl);

            return;

        }

        const store = profileStore();

        const url = uOrUrl;

        if (store && url) {

            store.setProfile({

                avatar_url: url,

                avatarUrl: url,

                foto_version: String(Date.now()),

            });

            return;

        }

        const ts = String(Date.now());

        const busted = url ? url.split('?')[0] + '?v=' + ts : '';

        document.querySelectorAll('[data-nebula-avatar]').forEach((el) => {

            if (el.tagName === 'IMG' && busted) {

                el.removeAttribute('src');

                void el.offsetHeight;

                el.src = busted;

            } else if (busted) el.style.backgroundImage = `url("${busted}")`;

        });

    }



    function abrirModal() {

        const modal = $('perfil-modal');

        if (!modal) return;

        sincronizarAsideDesdeFormulario();

        modal.classList.remove('hidden');

        modal.setAttribute('aria-hidden', 'false');

        document.body.classList.add('perfil-modal-open');

        $('perfil-form-editar')?.querySelector('input[name="nombre_completo"]')?.focus();

    }



    function cerrarModal() {

        const modal = $('perfil-modal');

        if (!modal) return;

        modal.classList.add('hidden');

        modal.setAttribute('aria-hidden', 'true');

        document.body.classList.remove('perfil-modal-open');

        if (!fotoSubidaEnSesion) {

            revocarPreview();

            fotoSeleccionada = null;

        }

        const inputFoto = $('perfil-form-foto');

        if (inputFoto && !fotoSubidaEnSesion) inputFoto.value = '';

        fotoSubidaEnSesion = false;

    }



    function revocarPreview() {

        if (previewUrl) {

            URL.revokeObjectURL(previewUrl);

            previewUrl = null;

        }

    }



    function aplicarPreviewLocal(file) {

        const Upload = global.NebulaAvatarUpload;

        if (Upload) {

            const v = Upload.validate(file);

            if (!v.ok) {

                mostrarToast(v.message, true);

                return false;

            }

        } else if (!file || !file.type.startsWith('image/')) {

            mostrarToast('Formato no permitido', true);

            return false;

        } else if (file.size > 5 * 1024 * 1024) {

            mostrarToast('La imagen supera el tamaño permitido', true);

            return false;

        }

        revocarPreview();

        fotoSeleccionada = file;

        previewUrl = URL.createObjectURL(file);

        document.querySelectorAll(

            '#perfil-modal-avatar, #perfil-avatar-main, [data-nebula-avatar]'

        ).forEach((el) => {

            if (el.tagName === 'IMG') el.src = previewUrl;

            else el.style.backgroundImage = `url("${previewUrl}")`;

        });

        return true;

    }



    async function subirFotoAlServidor(file) {

        const Upload = global.NebulaAvatarUpload;

        if (Upload) {

            const result = await Upload.upload(file, {

                preview: true,

                previewSelectors: ['#perfil-modal-avatar', '#perfil-avatar-main', '[data-nebula-avatar]'],

                onLoading: () => mostrarToast(Upload.MSG.loading, false),

                onError: (msg) => mostrarToast(msg, true),

            });

            if (!result.ok) throw new Error(result.message);

            return (result.data && result.data.usuario) || result.data;

        }

        if (!file) return null;

        const fd = new FormData();

        fd.append('foto', file, file.name || 'avatar.jpg');

        const res = await fetch(API_FOTO, {

            method: 'POST',

            credentials: 'same-origin',

            body: fd,

        });

        const text = await res.text();

        let data = {};

        try { data = JSON.parse(text); } catch (e) {

            throw new Error('Error al subir la imagen.');

        }

        if (!res.ok || !data.ok) {

            throw new Error(data.mensaje || 'Error al subir la imagen.');

        }

        return data.usuario || data;

    }



    async function onFotoSeleccionada(file) {

        const Upload = global.NebulaAvatarUpload;

        const v = Upload ? Upload.validate(file) : null;

        if (v && !v.ok) {

            mostrarToast(v.message, true);

            return;

        }

        if (!Upload) {

            mostrarToast('Módulo de subida no disponible. Recarga la página.', true);

            return;

        }

        try {

            const u = await subirFotoAlServidor(file);

            fotoSubidaEnSesion = true;

            fotoSeleccionada = null;

            revocarPreview();

            if (u) {

                syncGlobalProfile(u);

                if (config.usuario) config.usuario = { ...config.usuario, ...u };

            }

            mostrarToast(Upload.MSG.ok, false);

        } catch (err) {

            mostrarToast(err.message || 'Error al subir la imagen.', true);

            if (global.NebulaUserProfile) global.NebulaUserProfile.refreshFromServer();

        }

    }



    function actualizarPreferenciasUI(dominante) {

        document.querySelectorAll('.perfil-pref-card').forEach((card) => {

            const esActivo = card.dataset.pref === dominante;

            card.classList.toggle('perfil-pref-item--active', esActivo);

            card.classList.toggle('bg-slate-50', !esActivo);

            card.classList.toggle('border-slate-200', !esActivo);

            card.classList.toggle('opacity-80', !esActivo);

            const icon = card.querySelector('.material-symbols-outlined');

            const title = card.querySelector('p.font-bold');

            const label = card.querySelector('.perfil-pref-label');

            if (icon) {

                icon.classList.toggle('text-primary', esActivo);

                icon.classList.toggle('text-slate-500', !esActivo);

            }

            if (title) {

                title.classList.toggle('text-slate-900', esActivo);

                title.classList.toggle('text-slate-700', !esActivo);

            }

            if (label) label.textContent = esActivo ? 'Dominante' : 'Secundario';

        });

    }



    function sincronizarAsideDesdeFormulario() {

        const form = $('perfil-form-editar');

        if (!form) return;

        const nombre = form.nombre_completo?.value?.trim() || '';

        const username = form.username?.value?.trim() || '';

        const correo = form.correo?.value?.trim() || '';

        const nivel = form.nivel_academico?.value?.trim() || '';

        const setText = (id, text) => {

            const el = $(id);

            if (el) el.textContent = text;

        };

        setText('perfil-aside-nombre', nombre);

        setText('perfil-aside-username', username ? `@${username}` : '');

        setText('perfil-aside-correo', correo || '—');

        setText('perfil-aside-nivel', nivel || '—');

    }



    function actualizarVistaPerfil(u) {

        if (!u) return;

        const nombre = u.nombre_completo || '';

        const setText = (id, text) => {

            const el = $(id);

            if (el) el.textContent = text;

        };

        setText('perfil-nombre-display', nombre);

        const userEl = $('perfil-username-display');

        if (userEl) {

            userEl.textContent = u.username ? `@${u.username}` : '';

            userEl.classList.toggle('hidden', !u.username);

        }

        const correoEl = $('perfil-correo-display');

        if (correoEl) {

            correoEl.textContent = u.correo || '';

            correoEl.classList.toggle('hidden', !u.correo);

        }

        setText('perfil-sobre-mi-display', u.sobre_mi || config.usuario?.sobre_mi || '');

        setText('perfil-nivel-display', u.nivel_academico || '');

        const dom =

            u.preferencias_aprendizaje?.dominante || u.preferencia_dominante || 'visual';

        actualizarPreferenciasUI(dom);

        syncGlobalProfile(u);

        sincronizarAsideDesdeFormulario();

    }



    function validarFormulario(form) {

        if (!form.checkValidity()) {

            form.reportValidity();

            return false;

        }

        const username = form.username.value.trim();

        if (!/^[a-zA-Z0-9._-]{3,32}$/.test(username)) {

            mostrarToast('Usuario inválido (3-32 caracteres, letras, números, . _ -)', true);

            return false;

        }

        return true;

    }



    async function guardarPerfil(ev) {

        ev.preventDefault();

        const form = $('perfil-form-editar');

        if (!form || !validarFormulario(form)) return;



        const btn = $('perfil-btn-guardar');

        if (btn) btn.disabled = true;



        const fd = new FormData(form);

        if (fotoSeleccionada && !fotoSubidaEnSesion) {

            fd.set('foto', fotoSeleccionada);

        } else {

            fd.delete('foto');

        }



        try {

            const res = await fetch(API_PERFIL, {

                method: 'POST',

                credentials: 'same-origin',

                body: fd,

            });

            const data = await res.json().catch(() => ({}));

            if (!res.ok || !data.ok) {

                throw new Error(data.mensaje || 'No se pudo guardar el perfil.');

            }

            mostrarToast(data.mensaje || 'Perfil actualizado.', false);

            config.usuario = { ...config.usuario, ...data.usuario };

            actualizarVistaPerfil(data.usuario);

            fotoSeleccionada = null;

            fotoSubidaEnSesion = false;

            revocarPreview();

            setTimeout(cerrarModal, 900);

        } catch (err) {

            mostrarToast(err.message || 'Error al guardar.', true);

        } finally {

            if (btn) btn.disabled = false;

        }

    }



    function onFotoInputChange(ev) {

        const file = ev.target.files?.[0];

        if (file) onFotoSeleccionada(file);

    }



    function bindEvents() {

        $('btn-editar-perfil')?.addEventListener('click', abrirModal);

        $('perfil-btn-cambiar-foto')?.addEventListener('click', () => $('perfil-input-foto')?.click());

        $('perfil-btn-subir-foto')?.addEventListener('click', () => $('perfil-form-foto')?.click());

        $('perfil-input-foto')?.addEventListener('change', onFotoInputChange);

        $('perfil-form-foto')?.addEventListener('change', onFotoInputChange);



        $('perfil-form-editar')?.addEventListener('input', sincronizarAsideDesdeFormulario);



        document.querySelectorAll('[data-perfil-cerrar]').forEach((el) => {

            el.addEventListener('click', cerrarModal);

        });



        $('perfil-form-editar')?.addEventListener('submit', guardarPerfil);



        document.addEventListener('keydown', (e) => {

            if (e.key === 'Escape' && !$('perfil-modal')?.classList.contains('hidden')) {

                cerrarModal();

            }

        });



        document.addEventListener('nebula:profile-updated', (e) => {

            const u = e.detail;

            if (!u || !$('perfil-nombre-display')) return;

            if (u.nombre_completo) $('perfil-nombre-display').textContent = u.nombre_completo;

        });

    }



    function init() {

        config = parseConfig();

        bindEvents();

        if (config.usuario) syncGlobalProfile(config.usuario);

        const params = new URLSearchParams(global.location.search);

        if (params.get('editar') === '1') {

            abrirModal();

            try {

                const url = new URL(global.location.href);

                url.searchParams.delete('editar');

                global.history.replaceState({}, '', url.pathname + url.search + url.hash);

            } catch (e) {

                /* ignore */

            }

        }

    }



    global.NebulaPerfil = { init, abrirModal, cerrarModal };

    document.addEventListener('DOMContentLoaded', init);

})(typeof window !== 'undefined' ? window : this);


