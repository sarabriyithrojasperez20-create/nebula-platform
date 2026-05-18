/**
 * Nébula Tutor IA — chat con streaming, reintentos y estados UX.
 */
(function (global) {
    'use strict';

    const API = {
        chat: '/api/chat',
        stream: '/api/chat/stream',
        quick: '/api/tutor_ai/quick-action',
        session: '/api/tutor_ai/session',
        limites: '/api/tutor_ai/limites',
        health: '/api/tutor_ai/health',
    };

    const ETIQUETAS_MATERIA = {
        matematicas: 'Matemáticas',
        ciencia: 'Ciencias',
        historia: 'Historia',
        lenguaje: 'Lenguaje',
    };

    const USER_AVATAR =
        "url('https://lh3.googleusercontent.com/aida-public/AB6AXuDrTkVyxcrnRJfPROv8iv-pIr5qtw7LAygaTD_LwLOzTgcR8uuHkXntZk42deQiJRdweUFiTldbjFfoD8NyY7h5d5nwyo15gC6cwcuOQ2vatK6AJxHqfoFlrI2lkr7RO8SoCP50IXNc9b93UthpOaEZt-X26POZI-sAm-mnQM0zRiRjk5CqtQzKCFxBi0q0ys0RS6AaOIfiWYqKg3mE5rRVSb4O1uvyGn9hldyrnQjvCX1XJiaDBWGV61hDZ8fUYqMtAWQB7zpl3K0')";

    let config = {};
    let sessionId = null;
    let enviando = false;
    let usarStreaming = true;

    function parseConfig() {
        try {
            const el = document.getElementById('nebula-tutor-config');
            return el ? JSON.parse(el.textContent) : {};
        } catch {
            return {};
        }
    }

    function $(id) {
        return document.getElementById(id);
    }

    function escapeHtml(str) {
        return String(str || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function etiquetaMateria(slug) {
        if (!slug) return 'General';
        return ETIQUETAS_MATERIA[slug] || String(slug).replace(/_/g, ' ');
    }

    function mensajeDesdePayload(data, fallback) {
        if (!data) return fallback;
        if (data.mensaje) return data.mensaje;
        if (data.message) return data.message;
        return fallback;
    }

    function esErrorApi(data, err) {
        const codigo = data?.codigo || '';
        const msg = (data?.mensaje || err?.message || '').toLowerCase();
        if (codigo === 'quota' || codigo === 'auth' || codigo === 'config') return true;
        if (codigo === 'cooldown' || codigo === 'limite_diario' || codigo === 'limite_quiz') return true;
        if (msg.includes('cuota') && msg.includes('agotad')) return true;
        return false;
    }

    function renderContenido(texto) {
        let html = escapeHtml(texto || '');
        html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
        html = html.replace(/\n/g, '<br>');
        return html;
    }

    function formatearHora(iso) {
        try {
            const d = iso ? new Date(iso) : new Date();
            return d.toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' });
        } catch {
            return '';
        }
    }

    function renderizarMathEn(el) {
        if (!global.renderMathInElement) return;
        try {
            renderMathInElement(el, {
                delimiters: [
                    { left: '$$', right: '$$', display: true },
                    { left: '$', right: '$', display: false },
                ],
                throwOnError: false,
            });
        } catch {
            /* KaTeX opcional */
        }
    }

    function scrollAbajo() {
        const sc = $('tutor-chat-scroll');
        if (sc) sc.scrollTop = sc.scrollHeight;
    }

    function setEstadoUI(texto, tipo) {
        const bar = $('tutor-status-bar');
        const typingText = $('tutor-typing-text');
        if (bar) {
            bar.textContent = texto || '';
            bar.classList.toggle('hidden', !texto);
            bar.classList.remove('tutor-status-bar--processing', 'tutor-status-bar--retry', 'tutor-status-bar--info');
            if (texto) bar.classList.add(`tutor-status-bar--${tipo || 'info'}`);
        }
        if (typingText && texto) typingText.textContent = texto;
    }

    function mostrarToast(texto, tipo) {
        setEstadoUI(texto, tipo);
        const toast = $('tutor-toast');
        if (!toast) return;
        toast.textContent = texto;
        toast.classList.remove('hidden', 'tutor-toast--error', 'tutor-toast--info', 'tutor-toast--retry');
        toast.classList.add(tipo === 'error' ? 'tutor-toast--error' : tipo === 'retry' ? 'tutor-toast--retry' : 'tutor-toast--info');
        clearTimeout(mostrarToast._t);
        mostrarToast._t = setTimeout(() => toast.classList.add('hidden'), 4500);
    }

    function crearMensajeUsuario(texto, createdAt) {
        const wrap = document.createElement('div');
        wrap.className = 'flex gap-4 flex-row-reverse tutor-chat-msg';
        wrap.innerHTML = `
            <div class="size-10 rounded-full bg-slate-300 shrink-0 border-2 border-white shadow-sm"
                style="background-image: ${USER_AVATAR}; background-size: cover;"></div>
            <div class="max-w-2xl">
                <div class="tutor-ai-msg-user text-white p-6 rounded-xl rounded-tr-none">
                    <div class="tutor-msg-body">${renderContenido(texto)}</div>
                </div>
                <p class="text-[10px] text-slate-400 text-right mt-1">${formatearHora(createdAt)}</p>
            </div>`;
        return wrap;
    }

    function crearMensajeIA(texto, createdAt, esError) {
        const wrap = document.createElement('div');
        wrap.className = 'flex gap-4 tutor-chat-msg';
        const cardClass = esError
            ? 'tutor-ai-msg-ai tutor-ai-msg-error p-6 rounded-xl rounded-tl-none'
            : 'tutor-ai-msg-ai p-6 rounded-xl rounded-tl-none';
        wrap.innerHTML = `
            <div class="size-10 rounded-full bg-primary flex items-center justify-center text-white shrink-0 shadow-md shadow-primary/25">
                <span class="material-symbols-outlined">smart_toy</span>
            </div>
            <div class="max-w-2xl space-y-4">
                <div class="${cardClass}">
                    <div class="tutor-msg-body text-slate-700"></div>
                </div>
                <p class="text-[10px] text-slate-400 mt-1">${formatearHora(createdAt)}</p>
            </div>`;
        const bodyEl = wrap.querySelector('.tutor-msg-body');
        if (bodyEl) bodyEl.innerHTML = renderContenido(texto);
        if (!esError) renderizarMathEn(wrap);
        return wrap;
    }

    function mostrarTyping(mostrar, texto) {
        const el = $('tutor-typing-indicator');
        if (el) el.classList.toggle('hidden', !mostrar);
        if (mostrar) {
            setEstadoUI(texto || 'La IA está procesando tu solicitud…', 'processing');
            scrollAbajo();
        } else {
            setEstadoUI('', 'info');
        }
    }

    function pintarMensajes(mensajes) {
        const cont = $('tutor-chat-messages');
        if (!cont) return;
        cont.innerHTML = '';
        (mensajes || []).forEach((m) => {
            const node =
                m.role === 'user'
                    ? crearMensajeUsuario(m.content, m.created_at)
                    : crearMensajeIA(m.content, m.created_at);
            cont.appendChild(node);
        });
        scrollAbajo();
    }

    function actualizarHeader(ctx) {
        const h = $('tutor-topic-title');
        const sub = $('tutor-topic-subtitle');
        if (h && ctx?.titulo) h.textContent = ctx.titulo;
        if (sub) {
            sub.textContent = ctx?.materia
                ? `Materia: ${etiquetaMateria(ctx.materia)}`
                : 'Modo de refuerzo académico';
        }
    }

    function actualizarLimitesUI(lim) {
        const el = $('tutor-limites-badge');
        if (!el || !lim) return;
        el.textContent = `${lim.mensajes_usados}/${lim.mensajes_max} mensajes hoy`;
        el.title = lim.es_pro ? 'Plan Pro' : 'Plan gratuito';
        el.classList.remove('hidden');
    }

    async function fetchJson(url, options) {
        const res = await fetch(url, {
            credentials: 'same-origin',
            headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
            ...options,
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || data.ok === false) {
            const err = new Error(mensajeDesdePayload(data, `Error (${res.status})`));
            err.payload = data;
            err.status = res.status;
            throw err;
        }
        return data;
    }

    function mostrarErrorEnChat(err) {
        const data = err?.payload || {};
        const texto = mensajeDesdePayload(data, err?.message || 'No pude procesar tu mensaje.');
        const cont = $('tutor-chat-messages');
        if (cont) {
            cont.appendChild(crearMensajeIA(texto, new Date().toISOString(), true));
        }
        mostrarToast(texto, esErrorApi(data, err) ? 'error' : 'info');
        scrollAbajo();
    }

    async function esperarCooldown(segundos) {
        const s = Math.max(1, Math.ceil(segundos || 2));
        for (let i = s; i > 0; i--) {
            setEstadoUI(`Espera ${i}s antes del siguiente mensaje…`, 'processing');
            await new Promise((r) => setTimeout(r, 1000));
        }
    }

    async function enviarMensaje(texto) {
        if (enviando || !texto.trim()) return;

        if (!sessionId) {
            try {
                await nuevoChat();
            } catch (err) {
                mostrarErrorEnChat(err);
                return;
            }
        }

        enviando = true;
        const input = $('tutor-chat-input');
        const sendBtn = $('tutor-send-btn');
        if (input) input.disabled = true;
        if (sendBtn) sendBtn.disabled = true;

        const cont = $('tutor-chat-messages');
        cont.appendChild(crearMensajeUsuario(texto, new Date().toISOString()));
        scrollAbajo();
        mostrarTyping(true, 'La IA está procesando tu solicitud…');

        let streamNode = null;

        try {
            if (usarStreaming) {
                streamNode = await enviarStream(texto);
            } else {
                const data = await fetchJson(API.chat, {
                    method: 'POST',
                    body: JSON.stringify({ session_id: sessionId, mensaje: texto }),
                });
                cont.appendChild(crearMensajeIA(data.respuesta, new Date().toISOString()));
                if (data.limites) actualizarLimitesUI(data.limites);
            }
        } catch (err) {
            if (streamNode?.parentNode) streamNode.remove();
            const payload = err?.payload || {};
            if (payload.codigo === 'cooldown' && payload.retry_after) {
                const ultimo = cont?.querySelector('.tutor-chat-msg.flex-row-reverse:last-of-type');
                if (ultimo) ultimo.remove();
                await esperarCooldown(payload.retry_after);
                enviando = false;
                if (input) {
                    input.disabled = false;
                    input.value = texto;
                }
                if (sendBtn) sendBtn.disabled = false;
                return enviarMensaje(texto);
            }
            mostrarErrorEnChat(err);
        } finally {
            mostrarTyping(false);
            enviando = false;
            if (input) {
                input.disabled = false;
                input.value = '';
                input.focus();
            }
            if (sendBtn) sendBtn.disabled = false;
            scrollAbajo();
        }
    }

    async function enviarStream(texto, intentoCliente = 0) {
        const res = await fetch(API.stream, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
            body: JSON.stringify({ session_id: sessionId, mensaje: texto }),
        });

        const contentType = res.headers.get('content-type') || '';
        if (!res.ok || contentType.includes('application/json')) {
            const data = await res.json().catch(() => ({}));
            const err = new Error(mensajeDesdePayload(data, 'No se pudo conectar con el tutor.'));
            err.payload = data;
            if (data.retryable && intentoCliente < 2 && data.codigo !== 'quota') {
                mostrarToast('Reintentando conexión…', 'retry');
                await new Promise((r) => setTimeout(r, 1200 * (intentoCliente + 1)));
                return enviarStream(texto, intentoCliente + 1);
            }
            throw err;
        }

        const wrap = crearMensajeIA('', new Date().toISOString());
        $('tutor-chat-messages').appendChild(wrap);
        const body = wrap.querySelector('.tutor-msg-body');
        let acumulado = '';
        let recibioDelta = false;

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lineas = buffer.split('\n');
            buffer = lineas.pop() || '';

            for (const linea of lineas) {
                if (!linea.startsWith('data: ')) continue;
                let payload;
                try {
                    payload = JSON.parse(linea.slice(6));
                } catch {
                    continue;
                }

                if (payload.status && payload.mensaje) {
                    const tipo = payload.status === 'retry' ? 'retry' : 'processing';
                    setEstadoUI(payload.mensaje, tipo);
                    mostrarToast(payload.mensaje, tipo);
                    continue;
                }

                if (payload.error) {
                    const err = new Error(payload.mensaje || 'Error del tutor');
                    err.payload = payload;
                    if (payload.retryable && intentoCliente < 2 && payload.codigo !== 'quota') {
                        wrap.remove();
                        mostrarToast('Reintentando conexión…', 'retry');
                        await new Promise((r) => setTimeout(r, 1500));
                        return enviarStream(texto, intentoCliente + 1);
                    }
                    throw err;
                }

                if (payload.delta) {
                    if (!recibioDelta) {
                        recibioDelta = true;
                        mostrarTyping(false);
                        setEstadoUI('Estamos preparando tu respuesta…', 'processing');
                    }
                    acumulado += payload.delta;
                    body.innerHTML = renderContenido(acumulado);
                    renderizarMathEn(wrap);
                    scrollAbajo();
                }
            }
        }

        if (!acumulado.trim()) {
            const err = new Error('La IA no devolvió contenido. Intenta de nuevo.');
            err.payload = { codigo: 'empty', retryable: true };
            throw err;
        }

        setEstadoUI('', 'info');
        await refrescarLimites();
        return wrap;
    }

    async function refrescarLimites() {
        try {
            const data = await fetchJson(API.limites);
            if (data.ok !== false) actualizarLimitesUI(data);
        } catch {
            /* silencioso */
        }
    }

    async function accionRapida(accion) {
        if (enviando) return;
        if (!sessionId) {
            try {
                await nuevoChat();
            } catch (err) {
                mostrarErrorEnChat(err);
                return;
            }
        }
        enviando = true;
        mostrarTyping(true, 'Generando respuesta…');
        try {
            const data = await fetchJson(API.quick, {
                method: 'POST',
                body: JSON.stringify({ session_id: sessionId, accion }),
            });
            const cont = $('tutor-chat-messages');
            const labels = { explain: 'Explicar concepto', quiz: 'Cuestionario', summary: 'Resumen' };
            cont.appendChild(
                crearMensajeUsuario(`[${labels[accion] || accion}]`, new Date().toISOString())
            );
            cont.appendChild(crearMensajeIA(data.respuesta, new Date().toISOString()));
            if (data.limites) actualizarLimitesUI(data.limites);
        } catch (err) {
            mostrarErrorEnChat(err);
        } finally {
            mostrarTyping(false);
            enviando = false;
            scrollAbajo();
        }
    }

    async function nuevoChat() {
        const data = await fetchJson(API.session, { method: 'POST', body: '{}' });
        sessionId = data.session_id;
        config.contexto = data.contexto;
        actualizarHeader(data.contexto);
        pintarMensajes(data.mensajes || []);
        await refrescarLimites();
    }

    async function cargarSesion(id) {
        if (!id || enviando) return;
        try {
            const data = await fetchJson(`${API.session}/${encodeURIComponent(id)}`, { method: 'GET' });
            sessionId = data.sesion.session_id;
            config.contexto = data.sesion.contexto;
            actualizarHeader(data.sesion.contexto);
            pintarMensajes(data.sesion.mensajes || []);
            document.querySelectorAll('[data-tutor-session-id]').forEach((btn) => {
                const active = btn.dataset.tutorSessionId === sessionId;
                btn.classList.toggle('bg-primary/10', active);
                btn.classList.toggle('text-primary', active);
                btn.classList.toggle('font-medium', active);
            });
        } catch (err) {
            mostrarErrorEnChat(err);
        }
    }

    async function verificarSaludIA() {
        if (config.iaConfigurada === false) return;
        try {
            const data = await fetchJson(API.health);
            const diag = data.diagnostico || {};
            if (!diag.ok && diag.codigo_error === 'quota') {
                mostrarToast(diag.mensaje || 'Cuota de API agotada en el servidor.', 'error');
            }
        } catch {
            /* health opcional */
        }
    }

    function bindEvents() {
        $('tutor-send-btn')?.addEventListener('click', () => {
            const input = $('tutor-chat-input');
            if (input?.value.trim()) enviarMensaje(input.value.trim());
        });

        $('tutor-chat-input')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (e.target.value.trim() && !enviando) enviarMensaje(e.target.value.trim());
            }
        });

        $('tutor-btn-nuevo-chat')?.addEventListener('click', () => nuevoChat());

        $('tutor-attach-btn')?.addEventListener('click', () => {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = '.pdf,.png,.jpg,.jpeg,.webp,.txt';
            input.addEventListener('change', () => {
                if (input.files?.length) {
                    mostrarToast('La subida de archivos estará disponible pronto.', 'info');
                }
            });
            input.click();
        });

        document.querySelectorAll('[data-tutor-action]').forEach((btn) => {
            btn.addEventListener('click', () => accionRapida(btn.dataset.tutorAction));
        });

        document.querySelectorAll('[data-tutor-session-id]').forEach((btn) => {
            btn.addEventListener('click', () => cargarSesion(btn.dataset.tutorSessionId));
        });
    }

    async function init() {
        config = parseConfig();
        sessionId = config.sessionId || null;
        usarStreaming = config.streaming !== false;
        actualizarHeader(config.contexto);
        pintarMensajes(config.mensajes || []);
        actualizarLimitesUI(config.limites);
        bindEvents();

        if (config.iaConfigurada === false) {
            mostrarErrorEnChat({
                message:
                    'El tutor IA no está configurado. Define OPENAI_API_KEY en .env y reinicia Flask.',
                payload: { codigo: 'config' },
            });
        } else {
            await verificarSaludIA();
            if (!sessionId) {
                try {
                    await nuevoChat();
                } catch (err) {
                    mostrarErrorEnChat(err);
                }
            }
        }

        $('tutor-chat-input')?.focus();
    }

    global.NebulaTutorAI = { init, enviarMensaje, accionRapida, nuevoChat };
    document.addEventListener('DOMContentLoaded', () => init());
})(typeof window !== 'undefined' ? window : this);
