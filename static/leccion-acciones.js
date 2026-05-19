(function () {
    var MIN_PASS = 60;
    var meta = window.LECCION_META || {};
    var msgEl = document.getElementById('leccion-quiz-gate-msg');
    var btnMarcar = document.getElementById('btn-marcar-completada');
    var btnContinuar = document.getElementById('btn-continuar-leccion');
    var estadoLabel = document.getElementById('leccion-estado-label');

    if (!msgEl || !btnMarcar || !btnContinuar) return;

    function quizStorageKey() {
        return 'nebula_quiz_' + (meta.userId || 0) + '_' + (meta.slug || '') + '_' + (meta.leccionId || '');
    }

    function leccionStorageKey() {
        return 'nebula_leccion_completada_' + (meta.userId || 0) + '_' + (meta.slug || '') + '_' + (meta.leccionId || '');
    }

    function loadQuizResult() {
        try {
            var raw = sessionStorage.getItem(quizStorageKey());
            if (!raw) return null;
            return JSON.parse(raw);
        } catch (e) {
            return null;
        }
    }

    function isQuizPassed() {
        var saved = loadQuizResult();
        return !!(saved && saved.completed && saved.passed && saved.pct >= MIN_PASS);
    }

    function isLeccionCompletada() {
        if (meta.leccionCompletada) return true;
        try {
            return sessionStorage.getItem(leccionStorageKey()) === 'true';
        } catch (e) {
            return false;
        }
    }

    function saveLeccionCompletadaLocal() {
        try {
            sessionStorage.setItem(leccionStorageKey(), 'true');
        } catch (e) {
            /* ignore */
        }
        meta.leccionCompletada = true;
    }

    function saveQuizResult(pct, passed, correctCount, total) {
        sessionStorage.setItem(
            quizStorageKey(),
            JSON.stringify({
                pct: pct,
                passed: passed,
                completed: true,
            })
        );
        if (meta.guardarQuizUrl) {
            return fetch(meta.guardarQuizUrl, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    Accept: 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: JSON.stringify({
                    porcentaje: pct,
                    correctas: correctCount || 0,
                    total: total || 0,
                    aprobado: passed,
                }),
            })
                .then(function (r) {
                    return r.json();
                })
                .then(function (data) {
                    if (data && data.ok && passed && window.NebulaProgreso && meta.slug) {
                        window.NebulaProgreso.onCursoUpdated(meta.slug, data.progreso || {
                            porcentaje: data.porcentaje_curso,
                        });
                    }
                    return data;
                })
                .catch(function () {
                    /* ignore */
                });
        }
    }

    function clearPassWhileRetrying() {
        sessionStorage.setItem(
            quizStorageKey(),
            JSON.stringify({
                pct: 0,
                passed: false,
                completed: false,
                started: true,
            })
        );
    }

    function setButtonsEnabled(enabled) {
        if (isLeccionCompletada()) {
            btnMarcar.disabled = true;
            btnMarcar.dataset.completada = 'true';
            btnContinuar.classList.remove('is-locked');
            btnContinuar.setAttribute('aria-disabled', 'false');
            return;
        }

        btnMarcar.disabled = !enabled;
        btnMarcar.dataset.completada = 'false';

        if (enabled) {
            btnContinuar.classList.remove('is-locked');
            btnContinuar.setAttribute('aria-disabled', 'false');
        } else {
            btnContinuar.classList.add('is-locked');
            btnContinuar.setAttribute('aria-disabled', 'true');
        }
    }

    function updateEstadoVisual() {
        if (!estadoLabel) return;
        if (isLeccionCompletada()) {
            estadoLabel.innerHTML = '<span class="text-green-400">Estado: Completado</span>';
        }
    }

    function applyGate(state, pct) {
        msgEl.classList.remove('is-warning', 'is-success');

        if (isLeccionCompletada()) {
            setButtonsEnabled(true);
            msgEl.classList.add('is-success');
            msgEl.textContent = 'Lección marcada como completada.';
            updateEstadoVisual();
            return;
        }

        if (state === 'passed') {
            setButtonsEnabled(true);
            msgEl.classList.add('is-success');
            msgEl.textContent =
                '¡Quiz aprobado con ' + pct + '%! Ya puedes marcar la lección como completada o continuar.';
            return;
        }

        setButtonsEnabled(false);

        if (state === 'failed') {
            msgEl.classList.add('is-warning');
            msgEl.textContent =
                'Obtuviste ' + pct + '%. Necesitas aprobar el quiz final con mínimo 60% para continuar. Puedes reintentar el quiz más abajo.';
            return;
        }

        msgEl.textContent =
            'Debes realizar y aprobar el quiz final (mínimo 60%) antes de marcar la lección como completada o continuar.';
    }

    function initFromStorage() {
        if (isLeccionCompletada()) {
            applyGate('passed', loadQuizResult() ? loadQuizResult().pct : 100);
            return;
        }

        var saved = loadQuizResult();
        if (saved && saved.completed && saved.passed) {
            applyGate('passed', saved.pct);
        } else if (saved && saved.completed && !saved.passed) {
            applyGate('failed', saved.pct);
        } else {
            applyGate('not_started');
        }
    }

    if (meta.continuarUrl) {
        btnContinuar.href = meta.continuarUrl;
    }

    btnContinuar.addEventListener('click', function (e) {
        if (btnContinuar.classList.contains('is-locked')) {
            e.preventDefault();
            return;
        }
        if (!isLeccionCompletada() && !isQuizPassed()) {
            e.preventDefault();
        }
    });

    btnMarcar.addEventListener('click', function () {
        if (btnMarcar.disabled || btnMarcar.dataset.completada === 'true') return;
        if (!isQuizPassed()) return;

        btnMarcar.disabled = true;

        fetch(meta.marcarUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
            },
        })
            .then(function (res) {
                return res.json().then(function (data) {
                    return { ok: res.ok, data: data };
                });
            })
            .then(function (result) {
                if (!result.ok || !result.data.ok) {
                    btnMarcar.disabled = false;
                    msgEl.classList.add('is-warning');
                    msgEl.textContent =
                        (result.data && result.data.mensaje) ||
                        'No se pudo guardar el progreso. Intenta de nuevo.';
                    return;
                }

                saveLeccionCompletadaLocal();
                btnMarcar.dataset.completada = 'true';
                btnMarcar.disabled = true;

                msgEl.classList.remove('is-warning');
                msgEl.classList.add('is-success');
                msgEl.textContent = result.data.mensaje || 'Lección marcada como completada';

                if (result.data.continuar_url) {
                    btnContinuar.href = result.data.continuar_url;
                    meta.continuarUrl = result.data.continuar_url;
                }

                if (result.data.porcentaje_curso !== undefined && meta.slug) {
                    try {
                        localStorage.setItem(
                            'nebula_curso_pct_' + (meta.userId || 0) + '_' + meta.slug,
                            String(result.data.porcentaje_curso)
                        );
                    } catch (e) {
                        /* ignore */
                    }
                }

                if (window.NebulaProgreso && meta.slug) {
                    window.NebulaProgreso.onCursoUpdated(
                        meta.slug,
                        result.data.progreso || {
                            porcentaje: result.data.porcentaje_curso,
                            completado: result.data.curso_completado,
                        }
                    );
                }

                btnContinuar.classList.remove('is-locked');
                btnContinuar.setAttribute('aria-disabled', 'false');
                updateEstadoVisual();
            })
            .catch(function () {
                btnMarcar.disabled = false;
                msgEl.classList.add('is-warning');
                msgEl.textContent = 'Error de conexión. Intenta de nuevo.';
            });
    });

    window.LeccionQuizGate = {
        MIN_PASS: MIN_PASS,
        onQuizStart: function () {
            if (!isLeccionCompletada()) {
                clearPassWhileRetrying();
                applyGate('not_started');
            }
        },
        onQuizComplete: function (correctCount, total) {
            var pct = total > 0 ? Math.round((correctCount / total) * 100) : 0;
            var passed = pct >= MIN_PASS;
            saveQuizResult(pct, passed, correctCount, total);
            if (!isLeccionCompletada()) {
                applyGate(passed ? 'passed' : 'failed', pct);
            }
            return { pct: pct, passed: passed };
        },
    };

    initFromStorage();
})();
