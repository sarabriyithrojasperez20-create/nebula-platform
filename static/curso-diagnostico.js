(function () {
    var data = window.CURSO_DIAGNOSTICO;
    var meta = window.CURSO_DIAGNOSTICO_META || {};
    if (!data || !data.preguntas || !data.preguntas.length) return;

    var introWrap = document.getElementById('diag-intro-wrap');
    var activeWrap = document.getElementById('diag-active-wrap');
    var summaryEl = document.getElementById('diag-summary');
    var startBtn = document.getElementById('diag-start-btn');
    var sectionEl = document.getElementById('diagnostico');

    var counterEl = document.getElementById('diag-counter');
    var percentEl = document.getElementById('diag-percent');
    var progressFill = document.getElementById('diag-progress-fill');
    var typeBadge = document.getElementById('diag-type-badge');
    var questionEl = document.getElementById('diag-question');
    var optionsEl = document.getElementById('diag-options');
    var feedbackEl = document.getElementById('diag-feedback');
    var submitBtn = document.getElementById('diag-submit-btn');
    var prevBtn = document.getElementById('diag-prev-btn');
    var nextBtn = document.getElementById('diag-next-btn');
    var hintBox = document.getElementById('diag-hint-box');
    var showHintBtn = document.getElementById('diag-show-hint');
    var summaryScore = document.getElementById('diag-summary-score');
    var summaryNivel = document.getElementById('diag-summary-nivel');
    var summaryText = document.getElementById('diag-summary-text');
    var summaryDetail = document.getElementById('diag-summary-detail');
    var finishBtn = document.getElementById('diag-finish-btn');

    var preguntas = data.preguntas;
    var currentIndex = 0;
    var selectedOption = null;
    var answered = false;
    var correctCount = 0;
    var respuestasRegistro = [];
    var quizIniciado = false;

    function scrollToDiagnostico() {
        if (sectionEl) {
            sectionEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }

    function updateProgress() {
        var total = preguntas.length;
        var pct = Math.round(((currentIndex + (answered ? 1 : 0)) / total) * 100);
        if (pct > 100) pct = 100;
        if (counterEl) counterEl.textContent = 'Pregunta ' + (currentIndex + 1) + ' de ' + total;
        if (percentEl) percentEl.textContent = pct + '%';
        if (progressFill) progressFill.style.width = pct + '%';
    }

    function renderQuestion() {
        var q = preguntas[currentIndex];
        selectedOption = null;
        answered = false;
        if (typeBadge) typeBadge.textContent = q.tipo || 'Opción múltiple';
        if (questionEl) questionEl.textContent = q.enunciado;
        if (optionsEl) optionsEl.innerHTML = '';
        if (feedbackEl) {
            feedbackEl.classList.remove('is-visible', 'is-correct', 'is-incorrect');
            feedbackEl.innerHTML = '';
        }
        if (hintBox) {
            hintBox.classList.remove('is-visible');
            hintBox.textContent = '';
        }
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.style.display = 'inline-flex';
        }
        if (nextBtn) nextBtn.style.display = 'none';
        if (prevBtn) prevBtn.disabled = currentIndex === 0;

        if (optionsEl) {
            ['A', 'B', 'C', 'D'].forEach(function (letter) {
                if (!q.opciones[letter]) return;
                var btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'leccion-quiz-option';
                btn.setAttribute('data-letter', letter);
                btn.innerHTML =
                    '<span class="letter">' +
                    letter +
                    '</span><span class="text">' +
                    q.opciones[letter] +
                    '</span>';
                btn.addEventListener('click', function () {
                    if (answered) return;
                    optionsEl.querySelectorAll('.leccion-quiz-option').forEach(function (o) {
                        o.classList.remove('is-selected');
                    });
                    btn.classList.add('is-selected');
                    selectedOption = letter;
                });
                optionsEl.appendChild(btn);
            });
        }

        updateProgress();
    }

    function showFeedback(isCorrect, q) {
        answered = true;
        if (!feedbackEl) return;
        feedbackEl.classList.add('is-visible');
        feedbackEl.classList.toggle('is-correct', isCorrect);
        feedbackEl.classList.toggle('is-incorrect', !isCorrect);
        feedbackEl.innerHTML =
            '<p class="font-semibold">' +
            (isCorrect ? '¡Correcto!' : 'Incorrecto') +
            '</p><p class="text-sm mt-1">' +
            (q.explicacion || '') +
            '</p>';

        if (optionsEl) {
            optionsEl.querySelectorAll('.leccion-quiz-option').forEach(function (o) {
                var letter = o.getAttribute('data-letter');
                o.disabled = true;
                if (letter === q.correcta) o.classList.add('is-correct');
                if (letter === selectedOption && !isCorrect) o.classList.add('is-incorrect');
            });
        }

        if (submitBtn) submitBtn.style.display = 'none';
        if (nextBtn) {
            nextBtn.style.display = 'inline-flex';
            nextBtn.textContent =
                currentIndex === preguntas.length - 1 ? 'Ver resultado' : 'Siguiente pregunta';
        }
    }

    function submitAnswer() {
        if (answered || !selectedOption) return;
        var q = preguntas[currentIndex];
        var isCorrect = selectedOption === q.correcta;
        if (isCorrect) correctCount++;

        respuestasRegistro.push({
            indice: currentIndex,
            elegida: selectedOption,
        });

        showFeedback(isCorrect, q);
        updateProgress();
    }

    function goNext() {
        if (currentIndex < preguntas.length - 1) {
            currentIndex++;
            renderQuestion();
            return;
        }
        finishQuiz();
    }

    function nivelLabel(nivel) {
        if (nivel === 'basico') return 'Nivel básico';
        if (nivel === 'intermedio') return 'Nivel intermedio';
        if (nivel === 'avanzado') return 'Nivel avanzado';
        return nivel;
    }

    function finishQuiz() {
        if (activeWrap) activeWrap.classList.remove('is-visible');
        if (introWrap) introWrap.classList.add('is-hidden');
        if (summaryEl) summaryEl.classList.add('is-visible');

        var total = preguntas.length;
        var pct = total ? Math.round((correctCount / total) * 100) : 0;
        if (summaryScore) summaryScore.textContent = pct + '%';
        if (summaryText) summaryText.textContent = correctCount + ' de ' + total + ' respuestas correctas';
        if (summaryDetail) summaryDetail.textContent = 'Guardando tu resultado...';
        if (summaryNivel) summaryNivel.textContent = '';

        fetch(meta.guardarUrl, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                Accept: 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify({ respuestas: respuestasRegistro }),
        })
            .then(function (res) {
                return res.json().then(function (body) {
                    if (!res.ok) throw new Error(body.mensaje || 'Error al guardar');
                    return body;
                });
            })
            .then(function (body) {
                if (summaryNivel) {
                    summaryNivel.textContent = body.titulo_nivel || nivelLabel(body.nivel);
                }
                if (summaryDetail) summaryDetail.textContent = body.mensaje || '';
                try {
                    localStorage.setItem(
                        'nebula_diagnostico_' + meta.userId + '_' + meta.slug,
                        JSON.stringify({
                            nivel: body.nivel,
                            porcentaje: body.porcentaje,
                        })
                    );
                } catch (e) {
                    /* ignore */
                }
                if (window.NebulaProgreso && meta.slug && body.progreso) {
                    window.NebulaProgreso.onCursoUpdated(meta.slug, body.progreso);
                } else if (window.NebulaProgreso && meta.slug && body.progreso_curso !== undefined) {
                    window.NebulaProgreso.onCursoUpdated(meta.slug, {
                        porcentaje: body.progreso_curso,
                    });
                }
                if (finishBtn) {
                    finishBtn.disabled = false;
                    finishBtn.onclick = function () {
                        window.location.href =
                            window.location.pathname + window.location.search;
                    };
                }
            })
            .catch(function () {
                if (summaryDetail) {
                    summaryDetail.textContent =
                        'No se pudo guardar el diagnóstico. Intenta de nuevo.';
                }
            });
    }

    function startQuiz() {
        if (quizIniciado && activeWrap && activeWrap.classList.contains('is-visible')) {
            scrollToDiagnostico();
            return;
        }
        quizIniciado = true;
        if (introWrap) introWrap.classList.add('is-hidden');
        if (summaryEl) summaryEl.classList.remove('is-visible');
        if (activeWrap) activeWrap.classList.add('is-visible');
        currentIndex = 0;
        correctCount = 0;
        respuestasRegistro = [];
        renderQuestion();
        scrollToDiagnostico();
    }

    function irADiagnostico(autoStart) {
        scrollToDiagnostico();
        if (autoStart) {
            window.setTimeout(startQuiz, 350);
        }
    }

    if (startBtn) startBtn.addEventListener('click', startQuiz);
    if (submitBtn) submitBtn.addEventListener('click', submitAnswer);
    if (nextBtn) nextBtn.addEventListener('click', goNext);
    if (prevBtn) {
        prevBtn.addEventListener('click', function () {
            if (currentIndex > 0 && !answered) {
                currentIndex--;
                renderQuestion();
            }
        });
    }
    if (showHintBtn) {
        showHintBtn.addEventListener('click', function () {
            var q = preguntas[currentIndex];
            if (q.pista && hintBox) {
                hintBox.textContent = q.pista;
                hintBox.classList.add('is-visible');
            }
        });
    }

    document.querySelectorAll('[data-iniciar-diagnostico]').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            var autoStart = btn.getAttribute('data-iniciar-diagnostico') === 'true';
            irADiagnostico(autoStart);
        });
    });

    if (window.location.hash === '#diagnostico') {
        irADiagnostico(true);
    }
})();
