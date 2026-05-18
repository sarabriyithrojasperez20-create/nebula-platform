/**
 * Nébula — apertura/descarga de recursos académicos (URLs externas reales)
 * Reutiliza .recurso-abrir sin cambiar UI. PDF descargable vía proxy Flask (evita CORS).
 */
(function (global) {
    'use strict';

    const API_PROXY = '/api/recursos/proxy';
    const API_ESTADISTICA = '/api/recursos/estadistica';
    const DEBUG = /[?&]debug_recursos=1/.test(global.location?.search || '');

    /** Tipos que abren en nueva pestaña (no descarga directa) */
    const TIPOS_ABRIR_PESTANA = new Set([
        'web',
        'video',
        'podcast',
        'simulator',
        'flashcards',
        'article',
        'simulador',
    ]);

    let catalogo = new Map();
    let showToastFn = null;
    const enProceso = new Set();

    function logDebug(...args) {
        if (DEBUG) console.info('[NebulaRecursos]', ...args);
    }

    function configurar(opciones) {
        if (opciones?.showToast) showToastFn = opciones.showToast;
        if (Array.isArray(opciones?.recursos)) registrarCatalogo(opciones.recursos);
    }

    /** Índice por id (string) para los botones data-recurso-id */
    function registrarCatalogo(recursos) {
        catalogo = new Map();
        (recursos || []).forEach((r) => {
            const key = r?.id != null ? String(r.id) : null;
            if (key) catalogo.set(key, r);
        });
    }

    function obtenerRecurso(recursoId) {
        return catalogo.get(String(recursoId)) || null;
    }

    function toast(msg, tipo) {
        if (showToastFn) showToastFn(msg, tipo);
        else if (global.NebulaPlan?.showToast) global.NebulaPlan.showToast(msg, tipo);
    }

    /** Valida URL https antes de abrir o descargar */
    function validarUrl(url) {
        if (!url || typeof url !== 'string') return false;
        try {
            const u = new URL(url.trim());
            return u.protocol === 'https:' && u.hostname.length > 0;
        } catch {
            return false;
        }
    }

    /**
     * PDF con downloadable:true → descarga; resto → nueva pestaña.
     * type pdf sin downloadable (ej. recurso 8) → pestaña.
     */
    function esDescargaPdf(recurso) {
        const tipo = (recurso.type || '').toLowerCase();
        return tipo === 'pdf' && recurso.downloadable === true;
    }

    function debeAbrirEnPestana(recurso) {
        if (esDescargaPdf(recurso)) return false;
        const tipo = (recurso.type || '').toLowerCase();
        if (TIPOS_ABRIR_PESTANA.has(tipo)) return true;
        if (tipo === 'pdf') return true;
        return true;
    }

    function nombreArchivoDescarga(recurso) {
        const slug = (recurso.titulo || 'recurso')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .replace(/[^a-zA-Z0-9]+/g, '-')
            .replace(/^-|-$/g, '')
            .toLowerCase();
        return `${slug || 'recurso'}.pdf`;
    }

    function marcarCargando(btn, cargando) {
        if (!btn) return;
        btn.disabled = cargando;
        btn.setAttribute('aria-busy', cargando ? 'true' : 'false');
    }

    /** Abre URL externa (web, video, simulador, etc.) */
    function abrirEnNuevaPestana(url) {
        const ventana = window.open(url, '_blank', 'noopener,noreferrer');
        if (!ventana) {
            throw new Error('El navegador bloqueó la ventana emergente. Permite ventanas para este sitio.');
        }
        return ventana;
    }

    /**
     * Descarga PDF vía proxy del servidor (sin CORS en el cliente).
     * Fallback: abrir en nueva pestaña si el proxy falla.
     */
    async function descargarPdf(recurso) {
        const url = recurso.url.trim();
        const nombre = nombreArchivoDescarga(recurso);
        const proxyUrl = `${API_PROXY}?url=${encodeURIComponent(url)}&nombre=${encodeURIComponent(nombre)}`;

        logDebug('descarga proxy', proxyUrl);

        const res = await fetch(proxyUrl, { method: 'GET', credentials: 'same-origin' });
        if (!res.ok) {
            let mensaje = 'No se pudo descargar el PDF';
            try {
                const data = await res.json();
                if (data.mensaje) mensaje = data.mensaje;
            } catch {
                /* no JSON */
            }
            logDebug('proxy falló, fallback pestaña', res.status);
            abrirEnNuevaPestana(url);
            toast('No se pudo descargar; se abrió en una nueva pestaña', 'info');
            return;
        }

        const blob = await res.blob();
        if (!blob.size) {
            abrirEnNuevaPestana(url);
            toast('Archivo vacío; se abrió en una nueva pestaña', 'info');
            return;
        }

        const objectUrl = URL.createObjectURL(blob);
        const enlace = document.createElement('a');
        enlace.href = objectUrl;
        enlace.download = nombre;
        enlace.rel = 'noopener';
        enlace.style.display = 'none';
        document.body.appendChild(enlace);
        enlace.click();
        enlace.remove();
        setTimeout(() => URL.revokeObjectURL(objectUrl), 5000);
    }

    /** Estadísticas de uso (futuro: analytics / Storage) */
    async function registrarUso(recurso, accion) {
        try {
            await fetch(API_ESTADISTICA, {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
                body: JSON.stringify({
                    recurso_id: recurso.id,
                    titulo: recurso.titulo,
                    materia: recurso.materia,
                    category: recurso.category,
                    type: recurso.type,
                    url: recurso.url,
                    accion,
                }),
            });
        } catch (e) {
            logDebug('estadística no registrada', e);
        }
    }

    /**
     * Orquesta apertura según type y downloadable.
     * @param {object} recurso
     */
    async function ejecutarRecurso(recurso) {
        if (!validarUrl(recurso.url)) {
            throw new Error('La URL de este recurso no es válida o no está disponible.');
        }

        const url = recurso.url.trim();

        if (esDescargaPdf(recurso)) {
            await descargarPdf(recurso);
            await registrarUso(recurso, 'descarga');
            return;
        }

        if (debeAbrirEnPestana(recurso)) {
            abrirEnNuevaPestana(url);
            await registrarUso(recurso, 'abrir_pestana');
            return;
        }

        abrirEnNuevaPestana(url);
        await registrarUso(recurso, 'abrir_pestana');
    }

    /** Handler del botón existente .recurso-abrir */
    async function alClicAbrirRecurso(btn) {
        const recursoId = btn.dataset.recursoId;
        if (!recursoId) {
            toast('Recurso no identificado', 'error');
            return;
        }
        if (enProceso.has(recursoId)) return;

        const recurso = obtenerRecurso(recursoId);
        if (!recurso) {
            toast('Recurso no encontrado', 'error');
            return;
        }

        enProceso.add(recursoId);
        marcarCargando(btn, true);

        try {
            await ejecutarRecurso(recurso);
            const accion = esDescargaPdf(recurso) ? 'Descarga iniciada' : 'Recurso abierto';
            toast(`${accion}: ${recurso.titulo}`, 'success');
        } catch (err) {
            logDebug('error', err);
            toast(err.message || 'No se pudo abrir el recurso', 'error');
        } finally {
            enProceso.delete(recursoId);
            marcarCargando(btn, false);
        }
    }

    global.NebulaRecursos = {
        configurar,
        registrarCatalogo,
        alClicAbrirRecurso,
        ejecutarRecurso,
        validarUrl,
        esDescargaPdf,
    };
})(typeof window !== 'undefined' ? window : this);
