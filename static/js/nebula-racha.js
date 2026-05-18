/**

 * Nébula — racha diaria automática (sin botón manual)

 * Sincroniza con API Flask según actividad real en la plataforma.

 */

(function (global) {

    'use strict';



    const API = {

        estado: '/api/plan_estudios/racha',

        sincronizar: '/api/plan_estudios/racha/sincronizar',

        actividad: '/api/plan_estudios/racha/actividad',

        resumen: '/api/plan_estudios/racha/resumen',

    };



    const POLL_MS = 60000;

    const EVENT_SYNC = 'nebula:racha:actualizada';



    let estadoCache = null;

    let pollTimer = null;

    let renderCallback = null;

    let showToastFn = null;

    let lastRachaRendered = null;



    function parseRoutes() {

        try {

            const el = document.getElementById('nebula-routes');

            return el ? JSON.parse(el.textContent) : {};

        } catch {

            return {};

        }

    }



    function urls() {

        const r = parseRoutes();

        return {

            estado: r.rachaEstado || API.estado,

            sincronizar: r.rachaSincronizar || API.sincronizar,

            actividad: r.rachaActividad || API.actividad,

            resumen: r.rachaResumen || API.resumen,

        };

    }



    function parseInicial() {

        try {

            const el = document.getElementById('nebula-racha-inicial');

            return el ? JSON.parse(el.textContent) : null;

        } catch {

            return null;

        }

    }



    async function fetchJson(url, options) {

        const res = await fetch(url, {

            credentials: 'same-origin',

            headers: { Accept: 'application/json', 'Content-Type': 'application/json' },

            ...options,

        });

        const data = await res.json().catch(() => ({}));

        if (!res.ok && data.ok === false) {

            throw new Error(data.mensaje || 'Error de red');

        }

        return data;

    }



    async function cargarEstado(force) {

        if (!force && estadoCache) return estadoCache;

        const u = urls();

        const data = await fetchJson(`${u.estado}?sincronizar=1`);

        if (data.ok !== false) {

            estadoCache = data;

            global.dispatchEvent(new CustomEvent(EVENT_SYNC, { detail: data }));

        }

        return estadoCache;

    }



    /** Sincroniza quizzes, lecciones, evaluaciones y actualiza la UI */

    async function sincronizarAutomatico() {

        const u = urls();

        const antes = estadoCache?.racha_actual ?? 0;

        const data = await fetchJson(u.sincronizar, { method: 'POST', body: '{}' });

        estadoCache = data;

        global.dispatchEvent(new CustomEvent(EVENT_SYNC, { detail: data }));

        aplicarEstadoAlDom(data, {

            animate: (data.racha_actual ?? 0) > antes,

        });

        return data;

    }



    async function registrarActividad(tipo, metadata, minutosEstudio) {

        const u = urls();

        const body = { tipo, metadata: metadata || {}, minutos_estudio: minutosEstudio || 0 };

        const data = await fetchJson(u.actividad, {

            method: 'POST',

            body: JSON.stringify(body),

        });

        estadoCache = data;

        global.dispatchEvent(new CustomEvent(EVENT_SYNC, { detail: data }));

        return data;

    }



    function calcularRachaLocal(dias) {

        if (!dias || !dias.length) return 0;

        const hoy = formatDateLocal(new Date());

        const set = new Set(dias);

        let start = new Date();

        const hoyStr = formatDateLocal(start);

        if (!set.has(hoyStr)) {

            const ayer = new Date(start);

            ayer.setDate(ayer.getDate() - 1);

            if (!set.has(formatDateLocal(ayer))) return 0;

            start = ayer;

        }

        let streak = 0;

        let d = new Date(start);

        while (set.has(formatDateLocal(d))) {

            streak++;

            d.setDate(d.getDate() - 1);

        }

        return streak;

    }



    function formatDateLocal(d) {

        const y = d.getFullYear();

        const m = String(d.getMonth() + 1).padStart(2, '0');

        const day = String(d.getDate()).padStart(2, '0');

        return `${y}-${m}-${day}`;

    }



    function mensajeMotivacional(racha, actividadHoy) {

        if (!actividadHoy && racha === 0) {

            return 'Completa una lección, evaluación o quiz para iniciar tu racha hoy.';

        }

        if (!actividadHoy) {

            return 'Estudia hoy para mantener tu racha activa.';

        }

        if (racha >= 16) return '¡Maestro del hábito! Tu constancia es ejemplar.';

        if (racha >= 8) return '¡Vas muy bien! Sigue construyendo el hábito de estudio.';

        if (racha >= 4) return '¡Buen ritmo! Cada día de estudio suma.';

        return '¡Buen comienzo! La racha se actualiza sola con tu actividad.';

    }



    function aplicarEstadoAlDom(estado, opts) {

        if (!estado) return;

        opts = opts || {};



        const racha = estado.racha_actual ?? calcularRachaLocal(estado.dias_activos);

        const record = estado.mejor_racha ?? estado.record ?? estado.record_personal ?? 0;

        const dias = estado.dias_activos || [];

        const activosMes = estado.dias_activos_mes ?? estado.active_days_month ?? 0;

        const nivel = estado.nivel || 'Explorador';

        const actividadHoy = !!estado.actividad_hoy;



        const setText = (id, val) => {

            const el = document.getElementById(id);

            if (el) el.textContent = val;

        };



        setText('racha-dias-grande', racha);

        setText('widget-racha-dias', racha);

        setText('racha-record', record);

        setText('racha-mes', activosMes);

        setText('racha-nivel', nivel);

        setText('racha-mensaje-motivacional', mensajeMotivacional(racha, actividadHoy));

        setText(

            'widget-racha-msg',

            racha > 0 ? `Tu récord personal es de ${record} días` : 'Tu actividad en la plataforma alimenta la racha'

        );

        setText('widget-racha-badge', racha >= 16 ? 'Increíble' : racha >= 7 ? 'En racha' : racha >= 1 ? 'Activo' : 'Comienza');



        const autoEl = document.getElementById('racha-estado-auto');

        if (autoEl) {

            autoEl.innerHTML = actividadHoy

                ? '<span class="material-symbols-outlined text-base">check_circle</span> Actividad detectada hoy'

                : '<span class="material-symbols-outlined text-base">sync</span> Sincronización automática activa';

        }



        if (estado.horas_semanales) {

            const hs = estado.horas_semanales;

            const pct = hs.meta

                ? Math.min(100, Math.round((hs.completadas / hs.meta) * 100))

                : 0;

            setText('widget-progreso-pct', pct + '%');

            const bar = document.getElementById('widget-progreso-bar');

            if (bar) bar.style.width = pct + '%';

        }



        renderHeatmap(dias);



        if (opts.animate && lastRachaRendered !== null && racha > lastRachaRendered) {

            animateIncrement(lastRachaRendered, racha);

        }

        lastRachaRendered = racha;



        if (typeof renderCallback === 'function') renderCallback(estado);

    }



    function renderHeatmap(dias) {

        const heat = document.getElementById('racha-heatmap');

        if (!heat) return;

        const set = new Set(dias || []);

        const today = new Date();

        heat.innerHTML = '';

        for (let i = 29; i >= 0; i--) {

            const d = new Date(today);

            d.setDate(d.getDate() - i);

            const ds = formatDateLocal(d);

            const active = set.has(ds);

            const isToday = ds === formatDateLocal(today);

            const cell = document.createElement('div');

            cell.className =

                'aspect-square rounded-lg transition-all ' +

                (active ? 'streak-day-active' : 'bg-slate-100') +

                (isToday ? ' ring-2 ring-primary ring-offset-1' : '');

            cell.title = ds + (active ? ' — Activo' : '');

            heat.appendChild(cell);

        }

    }



    function animateIncrement(before, after) {

        ['racha-dias-grande', 'widget-racha-dias'].forEach((id) => {

            const el = document.getElementById(id);

            if (el && after > before) {

                el.classList.remove('racha-dias-bounce');

                void el.offsetWidth;

                el.classList.add('racha-dias-bounce');

            }

        });

        const card = document.querySelector('#panel-racha .plan-estudios-streak');

        if (card) {

            card.classList.remove('racha-glow-pulse');

            void card.offsetWidth;

            card.classList.add('racha-glow-pulse');

        }

    }



    function startPolling() {

        stopPolling();

        pollTimer = setInterval(() => {

            sincronizarAutomatico().catch(() => {});

        }, POLL_MS);

    }



    function stopPolling() {

        if (pollTimer) clearInterval(pollTimer);

        pollTimer = null;

    }



    function configure(options) {

        if (options.showToast) showToastFn = options.showToast;

        if (options.onRender) renderCallback = options.onRender;

    }



    async function init(options) {

        configure(options || {});

        const inicial = parseInicial();

        if (inicial && inicial.ok !== false) {

            estadoCache = inicial;

            aplicarEstadoAlDom(inicial, {});

        }

        try {

            await sincronizarAutomatico();

        } catch {

            try {

                const estado = await cargarEstado(true);

                aplicarEstadoAlDom(estado, {});

            } catch {

                /* NebulaPlan puede usar localStorage */

            }

        }

        startPolling();

        document.addEventListener('visibilitychange', () => {

            if (document.visibilityState === 'visible') {

                sincronizarAutomatico().catch(() => {});

            }

        });

    }



    function toast(msg, type) {

        if (showToastFn) showToastFn(msg, type);

        else if (global.NebulaPlan?.showToast) global.NebulaPlan.showToast(msg, type);

    }



    function hookMetaCompletada(meta) {

        if (!meta || meta.estado !== 'completada') return;

        registrarActividad('meta', { meta_id: meta.id, titulo: meta.titulo })

            .then((data) => {

                if (data.ok && data.racha_incrementada) {

                    aplicarEstadoAlDom(data, { animate: true });

                    toast('Meta completada — racha actualizada', 'success');

                }

            })

            .catch(() => {});

    }



    function hookEstudioMinutos(minutos) {

        if (minutos < 15) return;

        return registrarActividad('estudio_tiempo', {}, minutos);

    }



    global.NebulaRacha = {

        init,

        configure,

        cargarEstado,

        sincronizarAutomatico,

        registrarActividad,

        aplicarEstadoAlDom,

        hookMetaCompletada,

        hookEstudioMinutos,

        getEstado: () => estadoCache,

        EVENT_SYNC,

        stopPolling,

    };

})(typeof window !== 'undefined' ? window : this);


