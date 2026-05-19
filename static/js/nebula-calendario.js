/**
 * Nébula — Calendario académico (modal dashboard + API + vínculo a cursos)
 */
(function (global) {
    'use strict';

    const API = '/api/calendario/eventos';
    const CATEGORIAS = {
        evaluacion: { label: 'Examen', cls: 'evaluacion' },
        examen: { label: 'Examen', cls: 'evaluacion' },
        quiz: { label: 'Quiz', cls: 'evaluacion' },
        tarea: { label: 'Tarea', cls: 'tarea' },
        estudio: { label: 'Clase', cls: 'estudio' },
        clase: { label: 'Clase', cls: 'estudio' },
        reunion: { label: 'Reunión', cls: 'reunion' },
    };

    let eventos = [];
    let cursos = [];
    let weekStart = getMonday(new Date());
    let viewMode = 'week';
    let editingId = null;
    let dragId = null;
    let detailEvent = null;

    function $(id) { return document.getElementById(id); }

    function parseBoot() {
        try {
            const el = document.getElementById('nebula-calendario-boot');
            return el ? JSON.parse(el.textContent) : {};
        } catch { return {}; }
    }

    function getMonday(d) {
        const date = new Date(d);
        const day = date.getDay();
        const diff = date.getDate() - day + (day === 0 ? -6 : 1);
        return new Date(date.setDate(diff));
    }

    function addDays(date, days) {
        const r = new Date(date);
        r.setDate(r.getDate() + days);
        return r;
    }

    function formatDate(d) { return d.toISOString().slice(0, 10); }

    function escapeHtml(s) {
        return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function tipoLabel(ev) {
        return ev.tipo_label || (CATEGORIAS[ev.categoria] || CATEGORIAS.estudio).label;
    }

    function countdownLabel(fecha) {
        if (!fecha) return '';
        const hoy = new Date();
        hoy.setHours(0, 0, 0, 0);
        const obj = new Date(fecha + 'T12:00:00');
        const delta = Math.round((obj - hoy) / 86400000);
        if (delta < 0) return 'Pasado';
        if (delta === 0) return 'Hoy';
        if (delta === 1) return 'Mañana';
        return 'Faltan ' + delta + ' días';
    }

    function cursoTitulo(ev) {
        if (ev.curso_titulo) return ev.curso_titulo;
        const slug = ev.curso_slug || ev.materia;
        const c = cursos.find((x) => x.slug === slug);
        return c ? c.titulo : (slug || 'General');
    }

    function showToast(msg) {
        const t = $('nb-cal-toast');
        if (!t) return;
        t.textContent = msg;
        t.classList.remove('hidden');
        clearTimeout(showToast._tm);
        showToast._tm = setTimeout(() => t.classList.add('hidden'), 2800);
    }

    async function fetchEventos() {
        const res = await fetch(API, { credentials: 'same-origin' });
        const data = await res.json().catch(() => ({}));
        if (data.ok && Array.isArray(data.eventos)) eventos = data.eventos;
        return eventos;
    }

    async function fetchDestinoCurso(idActividad) {
        const res = await fetch('/evento/' + idActividad + '/curso', { credentials: 'same-origin' });
        return res.json().catch(() => ({}));
    }

    async function saveEvento(payload) {
        const isEdit = !!payload.id_actividad;
        const url = isEdit ? API + '/' + payload.id_actividad : API;
        const res = await fetch(url, {
            method: isEdit ? 'PUT' : 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || !data.ok) throw new Error(data.mensaje || 'No se pudo guardar.');
        return data.evento;
    }

    async function deleteEvento(id) {
        const res = await fetch(API + '/' + id, { method: 'DELETE', credentials: 'same-origin' });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || !data.ok) throw new Error(data.mensaje || 'No se pudo eliminar.');
    }

    function eventosDelDia(dateStr) {
        return eventos.filter((e) => e.fecha === dateStr).sort((a, b) => (a.hora || '').localeCompare(b.hora || ''));
    }

    function renderEventChip(ev) {
        const cat = CATEGORIAS[ev.categoria] || CATEGORIAS.estudio;
        const cd = ev.countdown || countdownLabel(ev.fecha);
        const curso = cursoTitulo(ev);
        return '<div class="nb-cal-event nb-cal-event--' + cat.cls + '" draggable="true" data-id="' + ev.id_actividad + '" title="' + escapeHtml(curso) + '">' +
            '<span class="nb-cal-event__title">' + escapeHtml(ev.titulo) + '</span>' +
            '<span class="nb-cal-event__meta">' + escapeHtml(tipoLabel(ev)) + ' · ' + escapeHtml(curso) + '</span>' +
            (cd ? '<span class="nb-cal-event__countdown">' + escapeHtml(cd) + '</span>' : '') +
            (ev.hora ? '<span class="nb-cal-event__hora">' + escapeHtml(ev.hora) + '</span>' : '') +
            '</div>';
    }

    function renderWeek() {
        const grid = $('nb-cal-week-grid');
        const headers = $('nb-cal-week-headers');
        const range = $('nb-cal-range');
        if (!grid || !headers) return;
        const labels = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
        const today = formatDate(new Date());
        const end = addDays(weekStart, 6);
        if (range) {
            range.textContent = weekStart.toLocaleDateString('es', { day: 'numeric', month: 'short' }) + ' – ' + end.toLocaleDateString('es', { day: 'numeric', month: 'short', year: 'numeric' });
        }
        headers.innerHTML = labels.map((label, i) => {
            const dt = addDays(weekStart, i);
            const isToday = formatDate(dt) === today;
            const color = isToday ? '#6a4bd8' : '#1c1a24';
            return '<div><span>' + label + '</span><br><strong style="color:' + color + '">' + dt.getDate() + '</strong></div>';
        }).join('');
        grid.innerHTML = '';
        for (let i = 0; i < 7; i++) {
            const dt = addDays(weekStart, i);
            const ds = formatDate(dt);
            const col = document.createElement('div');
            col.className = 'nb-cal-day' + (ds === today ? ' is-today' : '');
            col.dataset.date = ds;
            const num = document.createElement('div');
            num.className = 'nb-cal-day__num';
            num.textContent = String(dt.getDate());
            col.appendChild(num);
            eventosDelDia(ds).forEach((ev) => {
                const wrap = document.createElement('div');
                wrap.innerHTML = renderEventChip(ev);
                col.appendChild(wrap.firstElementChild);
            });
            grid.appendChild(col);
        }
    }

    function renderMonth() {
        const grid = $('nb-cal-month-grid');
        if (!grid) return;
        const y = weekStart.getFullYear();
        const m = weekStart.getMonth();
        const first = new Date(y, m, 1);
        const startPad = (first.getDay() + 6) % 7;
        const daysInMonth = new Date(y, m + 1, 0).getDate();
        const today = formatDate(new Date());
        let html = '';
        for (let i = 0; i < startPad; i++) html += '<div class="nb-cal-month-cell" style="visibility:hidden"></div>';
        for (let d = 1; d <= daysInMonth; d++) {
            const ds = formatDate(new Date(y, m, d));
            const count = eventosDelDia(ds).length;
            const cls = ['nb-cal-month-cell', ds === today ? 'is-today' : '', count ? 'has-events' : ''].filter(Boolean).join(' ');
            html += '<button type="button" class="' + cls + '" data-date="' + ds + '">' + d + (count ? '<span style="display:block;font-size:8px">' + count + ' ev.</span>' : '') + '</button>';
        }
        grid.innerHTML = html;
        const range = $('nb-cal-range');
        if (range) range.textContent = first.toLocaleDateString('es', { month: 'long', year: 'numeric' });
    }

    function renderCalendar() {
        const weekEl = $('nb-cal-week-wrap');
        const monthEl = $('nb-cal-month-wrap');
        if (viewMode === 'week') {
            weekEl && weekEl.classList.remove('hidden');
            monthEl && monthEl.classList.add('hidden');
            renderWeek();
        } else {
            weekEl && weekEl.classList.add('hidden');
            monthEl && monthEl.classList.remove('hidden');
            renderMonth();
        }
    }

    function renderUpcoming() {
        const list = $('nb-cal-upcoming-list');
        if (!list) return;
        const hoy = formatDate(new Date());
        const prox = eventos.filter((e) => (e.fecha || '') >= hoy).slice(0, 8);
        if (!prox.length) {
            list.innerHTML = '<p style="font-size:0.8125rem;color:#9490a0">No hay actividades próximas.</p>';
            return;
        }
        list.innerHTML = prox.map((ev) => {
            const cd = ev.countdown || countdownLabel(ev.fecha);
            return '<article class="nb-cal-upcoming-item" data-id="' + ev.id_actividad + '" role="button" tabindex="0">' +
                '<div class="nb-cal-upcoming-date"><em>' + escapeHtml(ev.mes) + '</em><strong>' + escapeHtml(ev.dia) + '</strong></div>' +
                '<div style="min-width:0;flex:1"><p style="font-size:0.8125rem;font-weight:700;margin:0">' + escapeHtml(ev.titulo) + '</p>' +
                '<p style="font-size:0.6875rem;margin:4px 0 0;color:#6b6578">' + escapeHtml(tipoLabel(ev)) + ' · ' + escapeHtml(cursoTitulo(ev)) +
                (ev.hora ? ' · ' + escapeHtml(ev.hora) : '') + '</p>' +
                (cd ? '<span class="nb-cal-countdown-badge">' + escapeHtml(cd) + '</span>' : '') +
                '</div></article>';
        }).join('');
    }

    function hideDetail() {
        detailEvent = null;
        $('nb-cal-detail') && $('nb-cal-detail').classList.add('hidden');
        $('nb-cal-upcoming-section') && $('nb-cal-upcoming-section').classList.remove('hidden');
    }

    function showDetail(ev) {
        detailEvent = ev;
        $('nb-cal-upcoming-section') && $('nb-cal-upcoming-section').classList.add('hidden');
        const panel = $('nb-cal-detail');
        if (!panel) return;
        panel.classList.remove('hidden');
        $('nb-cal-detail-tipo').textContent = tipoLabel(ev);
        $('nb-cal-detail-titulo').textContent = ev.titulo || '—';
        $('nb-cal-detail-curso').textContent = cursoTitulo(ev);
        const fechaTxt = ev.fecha ? new Date(ev.fecha + 'T12:00:00').toLocaleDateString('es', { weekday: 'long', day: 'numeric', month: 'long' }) : '—';
        $('nb-cal-detail-fecha').textContent = fechaTxt + (ev.hora ? ' · ' + ev.hora : '');
        $('nb-cal-detail-countdown').textContent = ev.countdown || countdownLabel(ev.fecha);
        const desc = (ev.descripcion || '').trim();
        const descEl = $('nb-cal-detail-desc');
        if (descEl) {
            descEl.textContent = desc || 'Sin notas para este evento.';
            descEl.style.display = desc ? 'block' : 'block';
        }
        const goBtn = $('nb-cal-detail-go');
        const unavail = $('nb-cal-detail-unavailable');
        const slug = ev.curso_slug || ev.materia;
        const tieneCurso = slug && cursos.some((c) => c.slug === slug);
        if (goBtn) goBtn.classList.toggle('hidden', !tieneCurso);
        if (unavail) unavail.classList.toggle('hidden', !!tieneCurso);
    }

    async function navegarAlCurso(ev) {
        if (!ev || !ev.id_actividad) {
            showToast('Curso no disponible');
            return;
        }
        showToast('Abriendo curso…');
        const data = await fetchDestinoCurso(ev.id_actividad);
        if (data.disponible && data.url) {
            global.location.href = data.url;
            return;
        }
        showToast(data.mensaje || 'Curso no disponible');
    }

    function refreshDashboardEvaluaciones() {
        const ul = document.getElementById('dashboard-eval-list');
        if (!ul) return;
        const hoy = formatDate(new Date());
        const evs = eventos.filter((e) => (e.fecha || '') >= hoy).slice(0, 6);
        if (!evs.length) return;
        ul.innerHTML = evs.map((ev) => {
            const cd = ev.countdown || countdownLabel(ev.fecha);
            return '<li><button type="button" class="dashboard-eval-row w-full text-left flex items-center gap-3 p-3 rounded-xl transition-colors hover:bg-violet-50/80" data-event-id="' + ev.id_actividad + '">' +
                '<div class="bg-white px-2.5 py-2 rounded-lg text-center shadow-sm border border-slate-100 shrink-0 min-w-[3rem]">' +
                '<p class="text-[10px] font-bold text-primary uppercase">' + escapeHtml(ev.mes) + '</p>' +
                '<p class="text-lg font-black text-slate-900">' + escapeHtml(ev.dia) + '</p></div>' +
                '<div class="flex-1 min-w-0"><h5 class="text-sm font-bold truncate">' + escapeHtml(ev.titulo) + '</h5>' +
                '<p class="text-[11px] text-slate-500 truncate">' + escapeHtml(cursoTitulo(ev)) + ' · ' + escapeHtml(tipoLabel(ev)) +
                (cd ? ' · <span class="text-primary font-semibold">' + escapeHtml(cd) + '</span>' : '') + '</p></div>' +
                '<span class="material-symbols-outlined text-slate-400">chevron_right</span></button></li>';
        }).join('');
        ul.querySelectorAll('[data-event-id]').forEach((btn) => {
            btn.addEventListener('click', () => {
                const id = Number(btn.dataset.eventId);
                const ev = eventos.find((x) => x.id_actividad === id);
                if (ev) navegarAlCurso(ev);
            });
        });
    }

    function fillCursoSelect() {
        const sel = $('nb-cal-curso');
        if (!sel) return;
        if (!cursos.length) {
            sel.innerHTML = '<option value="">Sin cursos asignados</option>';
            return;
        }
        sel.innerHTML = cursos.map((m) => '<option value="' + escapeHtml(m.slug) + '">' + escapeHtml(m.titulo) + '</option>').join('');
    }

    function updateFechaCountdown() {
        const inp = $('nb-cal-fecha');
        const out = $('nb-cal-fecha-countdown');
        if (!inp || !out) return;
        out.textContent = inp.value ? countdownLabel(inp.value) : '';
    }

    function showForm(ev) {
        const wrap = $('nb-cal-form-wrap');
        if (!wrap) return;
        hideDetail();
        wrap.classList.remove('hidden');
        const form = $('nb-cal-form');
        form.reset();
        editingId = ev ? ev.id_actividad : null;
        $('nb-cal-form-title').textContent = ev ? 'Editar actividad' : 'Nueva actividad';
        $('nb-cal-delete-btn').classList.toggle('hidden', !ev);
        if (ev) {
            form.titulo.value = ev.titulo || '';
            form.curso_slug.value = ev.curso_slug || ev.materia || '';
            form.fecha.value = ev.fecha || '';
            form.hora.value = ev.hora || '';
            form.categoria.value = ev.categoria === 'evaluacion' ? 'examen' : (ev.categoria || 'clase');
            form.prioridad.value = ev.prioridad || 'media';
            form.estado.value = ev.estado || 'pendiente';
            form.recordatorio.value = ev.recordatorio || 'ninguno';
            form.descripcion.value = ev.descripcion || '';
        } else {
            form.fecha.value = formatDate(new Date());
            if (cursos.length) form.curso_slug.value = cursos[0].slug;
        }
        updateFechaCountdown();
    }

    function hideForm() { $('nb-cal-form-wrap') && $('nb-cal-form-wrap').classList.add('hidden'); editingId = null; }

    function openModal() {
        const modal = $('nb-cal-modal');
        if (!modal) return;
        modal.classList.remove('hidden');
        document.body.classList.add('nb-cal-open');
        fetchEventos().then(() => { renderCalendar(); renderUpcoming(); refreshDashboardEvaluaciones(); });
    }

    function closeModal() {
        const modal = $('nb-cal-modal');
        if (!modal) return;
        modal.classList.add('hidden');
        document.body.classList.remove('nb-cal-open');
        hideForm();
        hideDetail();
    }

    function bindEvents() {
        document.querySelectorAll('[data-nb-cal-open]').forEach((btn) => btn.addEventListener('click', openModal));
        document.querySelectorAll('[data-nb-cal-close]').forEach((btn) => btn.addEventListener('click', closeModal));
        $('nb-cal-prev') && $('nb-cal-prev').addEventListener('click', () => {
            weekStart = addDays(weekStart, viewMode === 'week' ? -7 : -30);
            if (viewMode === 'month') weekStart = new Date(weekStart.getFullYear(), weekStart.getMonth(), 1);
            renderCalendar();
        });
        $('nb-cal-next') && $('nb-cal-next').addEventListener('click', () => {
            weekStart = addDays(weekStart, viewMode === 'week' ? 7 : 30);
            if (viewMode === 'month') weekStart = new Date(weekStart.getFullYear(), weekStart.getMonth(), 1);
            renderCalendar();
        });
        $('nb-cal-today') && $('nb-cal-today').addEventListener('click', () => { weekStart = getMonday(new Date()); renderCalendar(); });
        document.querySelectorAll('[data-cal-view]').forEach((btn) => {
            btn.addEventListener('click', () => {
                viewMode = btn.dataset.calView;
                document.querySelectorAll('[data-cal-view]').forEach((b) => b.classList.toggle('is-active', b === btn));
                renderCalendar();
            });
        });
        $('nb-cal-new-btn') && $('nb-cal-new-btn').addEventListener('click', () => showForm(null));
        $('nb-cal-fecha') && $('nb-cal-fecha').addEventListener('change', updateFechaCountdown);
        $('nb-cal-fecha') && $('nb-cal-fecha').addEventListener('input', updateFechaCountdown);
        $('nb-cal-detail-back') && $('nb-cal-detail-back').addEventListener('click', hideDetail);
        $('nb-cal-detail-go') && $('nb-cal-detail-go').addEventListener('click', () => detailEvent && navegarAlCurso(detailEvent));
        $('nb-cal-detail-edit') && $('nb-cal-detail-edit').addEventListener('click', () => {
            if (detailEvent) showForm(detailEvent);
        });
        $('nb-cal-form') && $('nb-cal-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const fd = new FormData(e.target);
            const payload = {
                titulo: fd.get('titulo'),
                curso_slug: fd.get('curso_slug'),
                materia: fd.get('curso_slug'),
                fecha: fd.get('fecha'),
                hora: fd.get('hora'),
                categoria: fd.get('categoria'),
                prioridad: fd.get('prioridad'),
                estado: fd.get('estado'),
                recordatorio: fd.get('recordatorio'),
                descripcion: fd.get('descripcion'),
            };
            if (editingId) payload.id_actividad = editingId;
            try {
                const saved = await saveEvento(payload);
                const idx = eventos.findIndex((x) => x.id_actividad === saved.id_actividad);
                if (idx >= 0) eventos[idx] = saved; else eventos.push(saved);
                eventos.sort((a, b) => (a.fecha + (a.hora || '')).localeCompare(b.fecha + (b.hora || '')));
                hideForm(); renderCalendar(); renderUpcoming(); refreshDashboardEvaluaciones(); showToast('Actividad guardada');
            } catch (err) { showToast(err.message); }
        });
        $('nb-cal-delete-btn') && $('nb-cal-delete-btn').addEventListener('click', async () => {
            if (!editingId || !confirm('¿Eliminar esta actividad?')) return;
            try {
                await deleteEvento(editingId);
                eventos = eventos.filter((e) => e.id_actividad !== editingId);
                hideForm(); hideDetail(); renderCalendar(); renderUpcoming(); refreshDashboardEvaluaciones(); showToast('Eliminada');
            } catch (err) { showToast(err.message); }
        });
        $('nb-cal-cancel-form') && $('nb-cal-cancel-form').addEventListener('click', hideForm);
        const weekGrid = $('nb-cal-week-grid');
        weekGrid && weekGrid.addEventListener('click', (e) => {
            const chip = e.target.closest('.nb-cal-event');
            if (!chip) return;
            const ev = eventos.find((x) => String(x.id_actividad) === chip.dataset.id);
            if (!ev) return;
            const slug = ev.curso_slug || ev.materia;
            if (slug && cursos.some((c) => c.slug === slug)) {
                navegarAlCurso(ev);
            } else {
                showDetail(ev);
            }
        });
        weekGrid && weekGrid.addEventListener('dragstart', (e) => {
            const chip = e.target.closest('.nb-cal-event');
            if (!chip) return;
            dragId = chip.dataset.id;
            e.dataTransfer.setData('text/plain', dragId);
        });
        weekGrid && weekGrid.addEventListener('dragover', (e) => {
            const day = e.target.closest('.nb-cal-day');
            if (!day) return;
            e.preventDefault();
            day.classList.add('is-drop-target');
        });
        weekGrid && weekGrid.addEventListener('dragleave', (e) => {
            const day = e.target.closest('.nb-cal-day');
            if (day) day.classList.remove('is-drop-target');
        });
        weekGrid && weekGrid.addEventListener('drop', async (e) => {
            const day = e.target.closest('.nb-cal-day');
            if (!day || !dragId) return;
            e.preventDefault();
            day.classList.remove('is-drop-target');
            const ev = eventos.find((x) => String(x.id_actividad) === dragId);
            if (!ev || ev.fecha === day.dataset.date) return;
            try {
                const updated = await saveEvento(Object.assign({}, ev, { id_actividad: ev.id_actividad, fecha: day.dataset.date }));
                const idx = eventos.findIndex((x) => x.id_actividad === ev.id_actividad);
                if (idx >= 0) eventos[idx] = updated;
                renderCalendar(); renderUpcoming(); refreshDashboardEvaluaciones(); showToast('Fecha actualizada');
            } catch (err) { showToast(err.message); }
            dragId = null;
        });
        $('nb-cal-month-grid') && $('nb-cal-month-grid').addEventListener('click', (e) => {
            const cell = e.target.closest('[data-date]');
            if (!cell) return;
            weekStart = getMonday(new Date(cell.dataset.date + 'T12:00:00'));
            viewMode = 'week';
            document.querySelectorAll('[data-cal-view]').forEach((b) => b.classList.toggle('is-active', b.dataset.calView === 'week'));
            renderCalendar();
            showForm({ fecha: cell.dataset.date, titulo: '' });
        });
        $('nb-cal-upcoming-list') && $('nb-cal-upcoming-list').addEventListener('click', (e) => {
            const item = e.target.closest('[data-id]');
            if (!item) return;
            const ev = eventos.find((x) => String(x.id_actividad) === item.dataset.id);
            if (ev) showDetail(ev);
        });
        const evalList = document.getElementById('dashboard-eval-list');
        evalList && evalList.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-event-id]');
            if (!btn) return;
            const id = Number(btn.dataset.eventId);
            const ev = eventos.find((x) => x.id_actividad === id);
            if (ev) {
                e.preventDefault();
                navegarAlCurso(ev);
            }
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && $('nb-cal-modal') && !$('nb-cal-modal').classList.contains('hidden')) closeModal();
        });
    }

    function init() {
        const boot = parseBoot();
        eventos = boot.eventos || [];
        cursos = boot.cursos || boot.materias || [];
        fillCursoSelect();
        bindEvents();
        refreshDashboardEvaluaciones();
        setInterval(() => {
            renderCalendar();
            renderUpcoming();
            refreshDashboardEvaluaciones();
        }, 60000);
    }

    global.NebulaCalendario = { init: init, open: openModal, refresh: fetchEventos, navegarAlCurso: navegarAlCurso };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else init();
})(typeof window !== 'undefined' ? window : this);
