/**
 * Perfil administrador — upload con vista previa y estado global.
 */
(function (global) {
    'use strict';

    var API_PERFIL = '/api/perfil';
    var Upload = global.NebulaAvatarUpload;

    function $(id) { return document.getElementById(id); }

    function toast(msg, type) {
        var t = $('admin-perfil-toast');
        if (!t) return;
        t.textContent = msg;
        t.className = 'admin-perfil-toast';
        if (type === 'err') t.classList.add('admin-perfil-toast--err');
        if (type === 'loading') t.classList.add('admin-perfil-toast--loading');
        t.classList.remove('hidden');
        clearTimeout(toast._tm);
        if (type !== 'loading') {
            toast._tm = setTimeout(function () { t.classList.add('hidden'); }, 3500);
        }
    }

    function setLoading(on) {
        var zone = $('admin-avatar-dropzone');
        if (zone) zone.classList.toggle('is-loading', on);
        var btn = $('admin-perfil-change-photo');
        if (btn) btn.disabled = on;
    }

    async function handleFile(file) {
        if (!Upload) {
            toast('Módulo de subida no cargado. Recarga la página.', 'err');
            return;
        }
        setLoading(true);
        await Upload.upload(file, {
            previewSelectors: ['#admin-perfil-avatar', '[data-nebula-avatar]', '.nb-avatar'],
            onLoading: function (m) { toast(m, 'loading'); },
            onSuccess: function (m) {
                toast(m, 'ok');
                var input = $('admin-perfil-foto-input');
                if (input) input.value = '';
            },
            onError: function (m) { toast(m, 'err'); },
        });
        setLoading(false);
    }

    async function saveProfile(form) {
        var fd = new FormData(form);
        try {
            var res = await fetch(API_PERFIL, { method: 'POST', body: fd, credentials: 'same-origin' });
            var data = await res.json().catch(function () { return {}; });
            if (!res.ok || !data.ok) throw new Error(data.mensaje || 'No se pudo guardar.');
            if (global.NebulaUserProfile && data.usuario) global.NebulaUserProfile.setProfile(data.usuario);
            toast('Perfil guardado correctamente.', 'ok');
        } catch (err) {
            toast(err.message, 'err');
        }
    }

    function bind() {
        var input = $('admin-perfil-foto-input');
        var zone = $('admin-avatar-dropzone');
        var btn = $('admin-perfil-change-photo');

        if (btn && input) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                input.click();
            });
        }
        if (input) {
            input.addEventListener('change', function () {
                if (input.files && input.files[0]) handleFile(input.files[0]);
            });
        }
        if (zone) {
            ['dragenter', 'dragover'].forEach(function (ev) {
                zone.addEventListener(ev, function (e) {
                    e.preventDefault();
                    zone.classList.add('is-dragover');
                });
            });
            zone.addEventListener('dragleave', function (e) {
                if (!zone.contains(e.relatedTarget)) zone.classList.remove('is-dragover');
            });
            zone.addEventListener('drop', function (e) {
                e.preventDefault();
                zone.classList.remove('is-dragover');
                var f = e.dataTransfer.files && e.dataTransfer.files[0];
                if (f) handleFile(f);
            });
        }

        var overlayLabel = zone && zone.querySelector('label[for="admin-perfil-foto-input"]');
        if (overlayLabel && input) {
            overlayLabel.addEventListener('click', function (e) {
                e.stopPropagation();
            });
        }

        var form = document.querySelector('.admin-perfil-form');
        if (form) {
            form.addEventListener('submit', function (e) {
                e.preventDefault();
                saveProfile(form);
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bind);
    } else {
        bind();
    }
})(typeof window !== 'undefined' ? window : this);
