(function () {
    var data = window.LECCION_QUIZ;
    if (!data || !data.preguntas || !data.preguntas.length) return;

    var introWrap = document.getElementById('quiz-intro-wrap');
    var activeWrap = document.getElementById('quiz-active-wrap');
    var summaryEl = document.getElementById('quiz-summary');
    var startBtn = document.getElementById('quiz-start-btn');
    var tabJump = document.getElementById('quiz-tab-jump');

    var counterEl = document.getElementById('quiz-counter');
    var percentEl = document.getElementById('quiz-percent');
    var progressFill = document.getElementById('quiz-progress-fill');
    var timerEl = document.getElementById('quiz-timer');
    var typeBadge = document.getElementById('quiz-type-badge');
    var questionEl = document.getElementById('quiz-question');
    var optionsEl = document.getElementById('quiz-options');
    var feedbackEl = document.getElementById('quiz-feedback');
    var submitBtn = document.getElementById('quiz-submit-btn');
    var prevBtn = document.getElementById('quiz-prev-btn');
    var nextBtn = document.getElementById('quiz-next-btn');
    var hintBox = document.getElementById('quiz-hint-box');
    var showHintBtn = document.getElementById('quiz-show-hint');
    var stuckBtn = document.getElementById('quiz-stuck-btn');
    var retryBtn = document.getElementById('quiz-retry-btn');
    var summaryScore = document.getElementById('quiz-summary-score');
    var summaryText = document.getElementById('quiz-summary-text');
    var summaryDetail = document.getElementById('quiz-summary-detail');

    var preguntas = data.preguntas;
    var currentIndex = 0;
    var selectedOption = null;
    var answered = false;
    var correctCount = 0;
    var results = [];
    var timerSeconds = 600;
    var timerInterval = null;

    function pad(n) {
        return n < 10 ? '0' + n : String(n);
    }

    function formatTimer(sec) {
        var m = Math.floor(sec / 60);
        var s = sec % 60;
        return pad(m) + ':' + pad(s);
    }

    function startTimer() {
        if (timerInterval) clearInterval(timerInterval);
        timerSeconds = 600;
        timerEl.textContent = formatTimer(timerSeconds);
        timerInterval = setInterval(function () {
            if (timerSeconds > 0) {
                timerSeconds--;
                timerEl.textContent = formatTimer(timerSeconds);
            }
        }, 1000);
    }

    function stopTimer() {
        if (timerInterval) {
            clearInterval(timerInterval);
            timerInterval = null;
        }
    }

    function updateProgress() {
        var total = preguntas.length;
        var current = answered ? currentIndex + 1 : currentIndex;
        var pct = Math.round((current / total) * 100);
        if (answered && currentIndex === total - 1) pct = 100;
        counterEl.textContent = 'Pregunta ' + (currentIndex + 1) + ' de ' + total;
        percentEl.textContent = pct + '%';
        progressFill.style.width = pct + '%';
    }

    function renderQuestion() {
        var q = preguntas[currentIndex];
        selectedOption = null;
        answered = false;
        typeBadge.textContent = q.tipo || 'Opción múltiple';
        questionEl.textContent = q.enunciado;
        optionsEl.innerHTML = '';
        feedbackEl.classList.remove('is-visible', 'is-correct', 'is-incorrect');
        feedbackEl.innerHTML = '';
        hintBox.classList.remove('is-visible');
        hintBox.textContent = '';
        submitBtn.disabled = false;
        nextBtn.style.display = 'none';
        prevBtn.disabled = currentIndex === 0;
        submitBtn.style.display = 'inline-flex';

        ['A', 'B', 'C', 'D'].forEach(function (letter) {
            if (!q.opciones[letter]) return;
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'leccion-quiz-option';
            btn.setAttribute('data-letter', letter);
            btn.innerHTML =
                '<span class="letter">' + letter + '</span><span class="text">' + q.opciones[letter] + '</span>';
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

        updateProgress();
    }

    function showFeedback(isCorrect, q) {
        answered = true;
        feedbackEl.classList.add('is-visible');
        feedbackEl.classList.toggle('is-correct', isCorrect);
        feedbackEl.classList.toggle('is-incorrect', !isCorrect);
        var title = isCorrect ? '¡Correcto!' : 'Incorrecto';
        feedbackEl.innerHTML =
            '<strong>' + title + '</strong><p>' + q.explicacion + '</p>';

        optionsEl.querySelectorAll('.leccion-quiz-option').forEach(function (o) {
            o.disabled = true;
            var letter = o.getAttribute('data-letter');
            if (letter === q.correcta) o.classList.add('is-correct');
            if (letter === selectedOption && !isCorrect) o.classList.add('is-wrong');
        });

        submitBtn.style.display = 'none';
        nextBtn.style.display = 'inline-flex';
        nextBtn.textContent =
            currentIndex < preguntas.length - 1 ? 'Siguiente pregunta' : 'Ver resultados';
        updateProgress();
    }

    function showSummary() {
        activeWrap.classList.remove('is-visible');
        summaryEl.classList.add('is-visible');
        stopTimer();
        var total = preguntas.length;
        var pct = Math.round((correctCount / total) * 100);
        summaryScore.textContent = pct + '%';
        summaryText.textContent =
            correctCount + ' de ' + total + ' respuestas correctas';
        if (window.LeccionQuizGate) {
            window.LeccionQuizGate.onQuizComplete(correctCount, total);
        }
        if (pct >= 80) {
            summaryDetail.textContent = '¡Excelente trabajo! Dominas los conceptos de esta lección.';
        } else if (pct >= 60) {
            summaryDetail.textContent = 'Buen esfuerzo. Repasa las explicaciones y vuelve a intentarlo.';
        } else {
            summaryDetail.textContent = 'Te recomendamos repasar el contenido de la lección antes de continuar.';
        }
    }

    function startQuiz() {
        if (window.LeccionQuizGate) {
            window.LeccionQuizGate.onQuizStart();
        }
        introWrap.classList.add('is-hidden');
        summaryEl.classList.remove('is-visible');
        activeWrap.classList.add('is-visible');
        currentIndex = 0;
        correctCount = 0;
        results = [];
        startTimer();
        renderQuestion();
        document.getElementById('leccion-quiz-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    startBtn.addEventListener('click', startQuiz);
    if (tabJump) {
        tabJump.addEventListener('click', function () {
            document.getElementById('leccion-quiz-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    }

    submitBtn.addEventListener('click', function () {
        if (!selectedOption || answered) return;
        var q = preguntas[currentIndex];
        var isCorrect = selectedOption === q.correcta;
        if (isCorrect) correctCount++;
        results.push({ index: currentIndex, correct: isCorrect });
        showFeedback(isCorrect, q);
    });

    prevBtn.addEventListener('click', function () {
        if (currentIndex > 0 && !answered) {
            currentIndex--;
            renderQuestion();
        }
    });

    nextBtn.addEventListener('click', function () {
        if (currentIndex < preguntas.length - 1) {
            currentIndex++;
            renderQuestion();
        } else {
            showSummary();
        }
    });

    showHintBtn.addEventListener('click', function () {
        var q = preguntas[currentIndex];
        hintBox.textContent = q.pista || 'Piensa en el concepto principal antes de responder.';
        hintBox.classList.add('is-visible');
    });

    stuckBtn.addEventListener('click', function () {
        var q = preguntas[currentIndex];
        hintBox.textContent =
            'Pista: ' + (q.pista || 'Revisa las definiciones clave de la lección.') +
            ' La respuesta correcta está relacionada con el tema central.';
        hintBox.classList.add('is-visible');
    });

    retryBtn.addEventListener('click', function () {
        summaryEl.classList.remove('is-visible');
        introWrap.classList.remove('is-hidden');
        startQuiz();
    });
})();
