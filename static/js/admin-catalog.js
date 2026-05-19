/**
 * Admin — gestión del catálogo académico (cursos, lecciones, evaluaciones, preguntas).
 */
(function () {
    'use strict';

    var cursosCache = [];
    var leccionesCache = [];
    var evaluacionesCache = [];

    function $(id) {
        return document.getElementById(id);
    }

    function toast(msg, isErr) {
        var t = $('admin-student-toast');
        if (!t) {
            if (isErr) console.error(msg);
            else console.log(msg);
            return;
        }
        t.textContent = msg;
        t.className = 'nb-toast' + (isErr ? ' nb-toast--err' : '');
        t.classList.remove('hidden');
        clearTimeout(toast._tm);
        toast._tm = setTimeout(function () {
            t.classList.add('hidden');
        }, 3500);
    }

    function api(method, url, body) {
        var opts = {
            method: method,
            headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
            credentials: 'same-origin',
        };
        if (body !== undefined) opts.body = JSON.stringify(body);
        return fetch(url, opts).then(function (r) {
            return r.json().then(function (data) {
                if (!r.ok || data.ok === false) {
                    var err = new Error(data.mensaje || 'Error en la solicitud.');
                    err.status = r.status;
                    throw err;
                }
                return data;
            });
        });
    }

    function confirmDelete(label) {
        return window.confirm(
            '¿Seguro que deseas eliminar "' + label + '"?\nEsta acción no se puede deshacer.'
        );
    }

    function reloadAdmin(panel) {
        try {
            if (panel) sessionStorage.setItem('nebula_admin_panel', panel);
        } catch (e) {
            /* ignore */
        }
        window.location.reload();
    }

    function openDialog(dlg) {
        if (!dlg) return;
        if (typeof dlg.showModal === 'function') dlg.showModal();
        else dlg.setAttribute('open', 'open');
    }

    function closeDialog(dlg) {
        if (!dlg) return;
        if (typeof dlg.close === 'function') dlg.close();
        else dlg.removeAttribute('open');
    }

    function formData(form) {
        return new FormData(form);
    }

    function fillCursoSelects() {
        var selects = [
            $('admin-leccion-curso-select'),
            $('admin-eval-curso-select'),
        ].filter(Boolean);
        selects.forEach(function (sel) {
            var val = sel.value;
            sel.innerHTML = '';
            cursosCache.forEach(function (c) {
                var opt = document.createElement('option');
                opt.value = c.slug;
                opt.textContent = c.titulo + (c.activo === false ? ' (inactivo)' : '');
                sel.appendChild(opt);
            });
            if (val) sel.value = val;
        });
    }

    function fillLeccionSelectForEval(cursoSlug, selected) {
        var sel = $('admin-eval-leccion-select');
        if (!sel) return;
        sel.innerHTML = '<option value="">— Sin lección específica —</option>';
        leccionesCache
            .filter(function (l) {
                return l.curso_slug === cursoSlug;
            })
            .forEach(function (l) {
                var opt = document.createElement('option');
                opt.value = l.leccion_id;
                opt.textContent = l.titulo;
                sel.appendChild(opt);
            });
        if (selected) sel.value = selected;
    }

    function toggleEvalLeccionWrap() {
        var form = $('admin-form-eval');
        var wrap = document.querySelector('.admin-eval-leccion-wrap');
        if (!form || !wrap) return;
        var tipo = (form.tipo && form.tipo.value) || 'diagnostico';
        var show = tipo === 'quiz';
        wrap.classList.toggle('hidden', !show);
        if (show && form.curso_slug) {
            fillLeccionSelectForEval(form.curso_slug.value, form.leccion_id ? form.leccion_id.value : '');
        }
    }

    function loadCursos() {
        return api('GET', '/api/admin/catalogo/cursos').then(function (data) {
            cursosCache = data.cursos || [];
            fillCursoSelects();
            return cursosCache;
        });
    }

    function loadLecciones() {
        return api('GET', '/api/admin/catalogo/lecciones').then(function (data) {
            leccionesCache = data.lecciones || [];
            renderLeccionesTable();
            return leccionesCache;
        });
    }

    function loadEvaluaciones() {
        return api('GET', '/api/admin/catalogo/evaluaciones').then(function (data) {
            evaluacionesCache = data.evaluaciones || [];
            renderEvaluacionesTable();
            return evaluacionesCache;
        });
    }

    function renderLeccionesTable() {
        var tbody = $('admin-lecciones-catalogo-body');
        if (!tbody) return;
        if (!leccionesCache.length) {
            tbody.innerHTML =
                '<tr><td colspan="4" class="px-6 py-8 text-center text-outline">No hay lecciones en el catálogo.</td></tr>';
            return;
        }
        tbody.innerHTML = leccionesCache
            .map(function (l) {
                var estado = l.activo === false ? ' <span class="text-outline text-xs">(inactiva)</span>' : '';
                return (
                    '<tr data-lesson-id="' +
                    l.id +
                    '">' +
                    '<td class="px-6 py-4 font-body-md font-semibold text-on-surface">' +
                    escapeHtml(l.titulo) +
                    estado +
                    '</td>' +
                    '<td class="px-6 py-4 text-body-md text-secondary">' +
                    escapeHtml(l.curso) +
                    '</td>' +
                    '<td class="px-6 py-4 text-body-md text-secondary">' +
                    escapeHtml(l.duracion || '—') +
                    '</td>' +
                    '<td class="px-6 py-4 text-right whitespace-nowrap">' +
                    '<button type="button" class="admin-edit-leccion text-primary text-xs font-bold hover:underline mr-2" data-lesson-id="' +
                    l.id +
                    '">Editar</button>' +
                    '<button type="button" class="admin-del-leccion text-error text-xs font-bold hover:underline" data-lesson-id="' +
                    l.id +
                    '" data-lesson-titulo="' +
                    escapeAttr(l.titulo) +
                    '">Eliminar</button>' +
                    '</td></tr>'
                );
            })
            .join('');
        bindLeccionRowActions();
    }

    function renderEvaluacionesTable() {
        var tbody = $('admin-eval-catalogo-body');
        if (!tbody) return;
        if (!evaluacionesCache.length) {
            tbody.innerHTML =
                '<tr><td colspan="6" class="px-6 py-8 text-center text-outline">No hay evaluaciones en el catálogo.</td></tr>';
            return;
        }
        tbody.innerHTML = evaluacionesCache
            .map(function (ev) {
                var tipoLabel = ev.tipo === 'diagnostico' ? 'Diagnóstico' : 'Quiz final';
                var estado = ev.activo === false ? ' <span class="text-outline text-xs">(inactiva)</span>' : '';
                return (
                    '<tr data-ev-id="' +
                    ev.id +
                    '">' +
                    '<td class="px-6 py-4 font-body-md font-semibold text-on-surface">' +
                    escapeHtml(ev.titulo || tipoLabel) +
                    estado +
                    '</td>' +
                    '<td class="px-6 py-4 text-body-md text-secondary">' +
                    escapeHtml(ev.curso_titulo) +
                    '</td>' +
                    '<td class="px-6 py-4 text-body-md text-secondary">' +
                    tipoLabel +
                    '</td>' +
                    '<td class="px-6 py-4 text-center">' +
                    (ev.num_preguntas || 0) +
                    '</td>' +
                    '<td class="px-6 py-4 text-center">' +
                    (ev.porcentaje_aprobacion != null ? ev.porcentaje_aprobacion : 70) +
                    '%</td>' +
                    '<td class="px-6 py-4 text-right whitespace-nowrap">' +
                    '<button type="button" class="admin-ev-preguntas text-primary text-xs font-bold hover:underline mr-2" data-ev-id="' +
                    ev.id +
                    '">Preguntas</button>' +
                    '<button type="button" class="admin-edit-eval text-primary text-xs font-bold hover:underline mr-2" data-ev-id="' +
                    ev.id +
                    '">Editar</button>' +
                    '<button type="button" class="admin-del-eval text-error text-xs font-bold hover:underline" data-ev-id="' +
                    ev.id +
                    '" data-ev-titulo="' +
                    escapeAttr(ev.titulo || tipoLabel) +
                    '">Eliminar</button>' +
                    '</td></tr>'
                );
            })
            .join('');
        bindEvalRowActions();
    }

    function escapeHtml(s) {
        return String(s || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function escapeAttr(s) {
        return escapeHtml(s).replace(/'/g, '&#39;');
    }

    function bindLeccionRowActions() {
        document.querySelectorAll('.admin-edit-leccion').forEach(function (btn) {
            btn.onclick = function () {
                openLeccionEdit(parseInt(btn.getAttribute('data-lesson-id'), 10));
            };
        });
        document.querySelectorAll('.admin-del-leccion').forEach(function (btn) {
            btn.onclick = function () {
                var id = parseInt(btn.getAttribute('data-lesson-id'), 10);
                var titulo = btn.getAttribute('data-lesson-titulo') || 'lección';
                if (!confirmDelete(titulo)) return;
                api('DELETE', '/api/admin/catalogo/lecciones/' + id)
                    .then(function () {
                        toast('Lección eliminada.');
                        reloadAdmin('lecciones');
                    })
                    .catch(function (e) {
                        toast(e.message, true);
                    });
            };
        });
    }

    function bindEvalRowActions() {
        document.querySelectorAll('.admin-ev-preguntas').forEach(function (btn) {
            btn.onclick = function () {
                openPreguntasManager(parseInt(btn.getAttribute('data-ev-id'), 10));
            };
        });
        document.querySelectorAll('.admin-edit-eval').forEach(function (btn) {
            btn.onclick = function () {
                openEvalEdit(parseInt(btn.getAttribute('data-ev-id'), 10));
            };
        });
        document.querySelectorAll('.admin-del-eval').forEach(function (btn) {
            btn.onclick = function () {
                var id = parseInt(btn.getAttribute('data-ev-id'), 10);
                var titulo = btn.getAttribute('data-ev-titulo') || 'evaluación';
                if (!confirmDelete(titulo)) return;
                api('DELETE', '/api/admin/catalogo/evaluaciones/' + id)
                    .then(function () {
                        toast('Evaluación eliminada.');
                        reloadAdmin('evaluaciones');
                    })
                    .catch(function (e) {
                        toast(e.message, true);
                    });
            };
        });
    }

    function openCursoModal(editSlug) {
        var dlg = $('admin-modal-curso');
        var form = $('admin-form-curso');
        if (!dlg || !form) return;
        form.reset();
        var slugInput = form.querySelector('[name="slug"]');
        var editField = $('admin-curso-edit-slug');
        var tituloHdr = $('admin-modal-curso-titulo');
        if (editSlug) {
            if (tituloHdr) tituloHdr.textContent = 'Editar curso';
            if (slugInput) slugInput.disabled = true;
            if (editField) editField.value = editSlug;
            api('GET', '/api/admin/catalogo/cursos/' + encodeURIComponent(editSlug))
                .then(function (data) {
                    var c = data.curso;
                    form.titulo.value = c.titulo || '';
                    if (slugInput) slugInput.value = c.slug || '';
                    form.nivel.value = c.nivel || 'Intermedio';
                    form.categoria.value = c.categoria || 'matematicas';
                    form.descripcion.value = c.descripcion || '';
                    form.duracion_total.value = c.duracion_total || '';
                    form.activo.checked = c.activo !== false;
                    openDialog(dlg);
                })
                .catch(function (e) {
                    toast(e.message, true);
                });
        } else {
            if (tituloHdr) tituloHdr.textContent = 'Nuevo curso';
            if (slugInput) slugInput.disabled = false;
            if (editField) editField.value = '';
            form.activo.checked = true;
            openDialog(dlg);
        }
    }

    function submitCurso(e) {
        e.preventDefault();
        var form = e.target;
        var fd = formData(form);
        var editSlug = ($('admin-curso-edit-slug') && $('admin-curso-edit-slug').value) || '';
        var payload = {
            titulo: (fd.get('titulo') || '').trim(),
            slug: (fd.get('slug') || '').trim(),
            nivel: fd.get('nivel'),
            categoria: fd.get('categoria'),
            descripcion: fd.get('descripcion'),
            duracion_total: fd.get('duracion_total'),
            activo: form.activo.checked,
        };
        var p = editSlug
            ? api('PUT', '/api/admin/catalogo/cursos/' + encodeURIComponent(editSlug), payload)
            : api('POST', '/api/admin/catalogo/cursos', payload);
        p.then(function () {
            toast(editSlug ? 'Curso actualizado.' : 'Curso creado.');
            closeDialog($('admin-modal-curso'));
            reloadAdmin('cursos');
        }).catch(function (err) {
            toast(err.message, true);
        });
    }

    function buildContenidoLeccion(fd, titulo) {
        var conceptosRaw = (fd.get('conceptos') || '').split('\n');
        var definiciones = [];
        conceptosRaw.forEach(function (line) {
            line = line.trim();
            if (!line) return;
            var idx = line.indexOf(':');
            if (idx > -1) {
                definiciones.push({
                    termino: line.slice(0, idx).trim(),
                    definicion: line.slice(idx + 1).trim(),
                });
            } else {
                definiciones.push({ termino: line, definicion: '' });
            }
        });
        return {
            titulo_tema: titulo,
            explicacion: (fd.get('explicacion') || '').trim(),
            definiciones: definiciones,
            formulas: [],
            ejemplo: { enunciado: '', solucion: '' },
            practica: { pregunta: '', pista: '' },
        };
    }

    function openLeccionModal() {
        var dlg = $('admin-modal-leccion');
        var form = $('admin-form-leccion');
        if (!dlg || !form) return;
        form.reset();
        if (form.lesson_db_id) form.lesson_db_id.value = '';
        form.activo.checked = true;
        $('admin-modal-leccion-titulo').textContent = 'Nueva lección';
        fillCursoSelects();
        openDialog(dlg);
    }

    function openLeccionEdit(id) {
        var dlg = $('admin-modal-leccion');
        var form = $('admin-form-leccion');
        if (!dlg || !form) return;
        api('GET', '/api/admin/catalogo/lecciones/' + id)
            .then(function (data) {
                var l = data.leccion;
                form.reset();
                form.lesson_db_id.value = l.id;
                fillCursoSelects();
                form.curso_slug.value = l.curso_slug;
                form.titulo.value = l.titulo || '';
                form.duracion.value = l.duracion || '30 min';
                form.activo.checked = l.activo !== false;
                var c = l.contenido || {};
                form.explicacion.value = c.explicacion || '';
                var defs = c.definiciones || [];
                form.conceptos.value = defs
                    .map(function (d) {
                        return (d.termino || '') + ': ' + (d.definicion || '');
                    })
                    .join('\n');
                $('admin-modal-leccion-titulo').textContent = 'Editar lección';
                openDialog(dlg);
            })
            .catch(function (e) {
                toast(e.message, true);
            });
    }

    function submitLeccion(e) {
        e.preventDefault();
        var form = e.target;
        var fd = formData(form);
        var titulo = (fd.get('titulo') || '').trim();
        var payload = {
            curso_slug: fd.get('curso_slug'),
            titulo: titulo,
            duracion: fd.get('duracion'),
            activo: form.activo.checked,
            contenido: buildContenidoLeccion(fd, titulo),
        };
        var id = (fd.get('lesson_db_id') || '').trim();
        var p = id
            ? api('PUT', '/api/admin/catalogo/lecciones/' + id, payload)
            : api('POST', '/api/admin/catalogo/lecciones', payload);
        p.then(function () {
            toast(id ? 'Lección actualizada.' : 'Lección creada.');
            closeDialog($('admin-modal-leccion'));
            reloadAdmin('lecciones');
        }).catch(function (err) {
            toast(err.message, true);
        });
    }

    function openEvalModal() {
        var dlg = $('admin-modal-eval');
        var form = $('admin-form-eval');
        if (!dlg || !form) return;
        form.reset();
        form.eval_id.value = '';
        form.activo.checked = false;
        $('admin-modal-eval-titulo').textContent = 'Nueva evaluación';
        fillCursoSelects();
        toggleEvalLeccionWrap();
        openDialog(dlg);
    }

    function openEvalEdit(id) {
        var dlg = $('admin-modal-eval');
        var form = $('admin-form-eval');
        if (!dlg || !form) return;
        api('GET', '/api/admin/catalogo/evaluaciones/' + id)
            .then(function (data) {
                var ev = data.evaluacion;
                form.reset();
                form.eval_id.value = ev.id;
                fillCursoSelects();
                form.curso_slug.value = ev.curso_slug;
                form.tipo.value = ev.tipo || 'diagnostico';
                form.titulo.value = ev.titulo || '';
                form.porcentaje_aprobacion.value = ev.porcentaje_aprobacion != null ? ev.porcentaje_aprobacion : 70;
                form.activo.checked = ev.activo !== false;
                toggleEvalLeccionWrap();
                fillLeccionSelectForEval(ev.curso_slug, ev.leccion_id || '');
                $('admin-modal-eval-titulo').textContent = 'Editar evaluación';
                openDialog(dlg);
            })
            .catch(function (e) {
                toast(e.message, true);
            });
    }

    function submitEval(e) {
        e.preventDefault();
        var form = e.target;
        var fd = formData(form);
        var id = (fd.get('eval_id') || '').trim();
        var payload = {
            curso_slug: fd.get('curso_slug'),
            tipo: fd.get('tipo'),
            titulo: (fd.get('titulo') || '').trim(),
            porcentaje_aprobacion: parseInt(fd.get('porcentaje_aprobacion'), 10) || 70,
            activo: form.activo.checked,
            leccion_id: fd.get('leccion_id') || null,
        };
        if (payload.tipo !== 'quiz') payload.leccion_id = null;
        var p = id
            ? api('PUT', '/api/admin/catalogo/evaluaciones/' + id, payload)
            : api('POST', '/api/admin/catalogo/evaluaciones', payload);
        p.then(function (res) {
            toast(id ? 'Evaluación actualizada.' : 'Evaluación creada.');
            closeDialog($('admin-modal-eval'));
            var evId = id || (res.id != null ? res.id : null);
            if (evId) {
                openPreguntasManager(parseInt(evId, 10));
            } else {
                reloadAdmin('evaluaciones');
            }
        }).catch(function (err) {
            toast(err.message, true);
        });
    }

    function openPreguntasManager(evId) {
        var dlg = $('admin-modal-eval-preguntas');
        if (!dlg) return;
        $('admin-eval-preguntas-ev-id').value = evId;
        api('GET', '/api/admin/catalogo/evaluaciones/' + evId)
            .then(function (data) {
                var ev = data.evaluacion;
                var sub = $('admin-eval-preguntas-subtitulo');
                if (sub) {
                    sub.textContent =
                        (ev.titulo || ev.tipo) +
                        ' — ' +
                        ev.curso_slug +
                        ' (' +
                        (ev.preguntas ? ev.preguntas.length : 0) +
                        ' preguntas)';
                }
                renderPreguntasList(ev.preguntas || [], evId);
                openDialog(dlg);
            })
            .catch(function (e) {
                toast(e.message, true);
            });
    }

    function renderPreguntasList(preguntas, evId) {
        var tbody = $('admin-eval-preguntas-list');
        if (!tbody) return;
        if (!preguntas.length) {
            tbody.innerHTML =
                '<tr><td colspan="3" class="px-4 py-6 text-center text-outline">Sin preguntas. Agregue la primera.</td></tr>';
            return;
        }
        tbody.innerHTML = preguntas
            .map(function (p, i) {
                var pid = p.id;
                var texto = (p.enunciado || '').slice(0, 120);
                if ((p.enunciado || '').length > 120) texto += '…';
                return (
                    '<tr>' +
                    '<td class="px-4 py-3 text-center text-outline">' +
                    (i + 1) +
                    '</td>' +
                    '<td class="px-4 py-3 text-on-surface">' +
                    escapeHtml(texto) +
                    '</td>' +
                    '<td class="px-4 py-3 text-right whitespace-nowrap">' +
                    '<button type="button" class="admin-edit-pregunta text-primary text-xs font-bold hover:underline mr-2" data-pregunta-id="' +
                    pid +
                    '" data-ev-id="' +
                    evId +
                    '">Editar</button>' +
                    '<button type="button" class="admin-del-pregunta text-error text-xs font-bold hover:underline" data-pregunta-id="' +
                    pid +
                    '">Eliminar</button>' +
                    '</td></tr>'
                );
            })
            .join('');
        document.querySelectorAll('.admin-edit-pregunta').forEach(function (btn) {
            btn.onclick = function () {
                openPreguntaEdit(
                    parseInt(btn.getAttribute('data-ev-id'), 10),
                    parseInt(btn.getAttribute('data-pregunta-id'), 10)
                );
            };
        });
        document.querySelectorAll('.admin-del-pregunta').forEach(function (btn) {
            btn.onclick = function () {
                var pid = parseInt(btn.getAttribute('data-pregunta-id'), 10);
                if (!confirmDelete('esta pregunta')) return;
                api('DELETE', '/api/admin/catalogo/preguntas/' + pid)
                    .then(function () {
                        toast('Pregunta eliminada.');
                        openPreguntasManager(parseInt($('admin-eval-preguntas-ev-id').value, 10));
                        loadEvaluaciones();
                    })
                    .catch(function (e) {
                        toast(e.message, true);
                    });
            };
        });
    }

    function openPreguntaModal(evId, pregunta) {
        var dlg = $('admin-modal-pregunta');
        var form = $('admin-form-pregunta');
        if (!dlg || !form) return;
        form.reset();
        form.eval_id.value = evId;
        var label = $('admin-pregunta-eval-label');
        if (label) label.textContent = 'Evaluación #' + evId;
        if (pregunta) {
            form.pregunta_id.value = pregunta.id;
            form.enunciado.value = pregunta.enunciado || '';
            var op = pregunta.opciones || {};
            form.opcion_a.value = op.A || '';
            form.opcion_b.value = op.B || '';
            form.opcion_c.value = op.C || '';
            form.opcion_d.value = op.D || '';
            form.respuesta_correcta.value = (pregunta.correcta || 'A').toUpperCase();
            form.explicacion.value = pregunta.explicacion || '';
            form.tema.value = pregunta.tema || '';
            form.dificultad.value = pregunta.dificultad || 'media';
        } else {
            form.pregunta_id.value = '';
        }
        openDialog(dlg);
    }

    function openPreguntaEdit(evId, preguntaId) {
        api('GET', '/api/admin/catalogo/evaluaciones/' + evId)
            .then(function (data) {
                var p = (data.evaluacion.preguntas || []).find(function (x) {
                    return x.id === preguntaId;
                });
                if (!p) throw new Error('Pregunta no encontrada.');
                openPreguntaModal(evId, p);
            })
            .catch(function (e) {
                toast(e.message, true);
            });
    }

    function submitPregunta(e) {
        e.preventDefault();
        var form = e.target;
        var fd = formData(form);
        var evId = parseInt(fd.get('eval_id'), 10);
        var preguntaId = (fd.get('pregunta_id') || '').trim();
        var payload = {
            enunciado: (fd.get('enunciado') || '').trim(),
            opciones: {
                A: fd.get('opcion_a') || '',
                B: fd.get('opcion_b') || '',
                C: fd.get('opcion_c') || '',
                D: fd.get('opcion_d') || '',
            },
            respuesta_correcta: fd.get('respuesta_correcta'),
            explicacion: fd.get('explicacion'),
            tema: fd.get('tema'),
            dificultad: fd.get('dificultad'),
        };
        var p = preguntaId
            ? api('PUT', '/api/admin/catalogo/preguntas/' + preguntaId, payload)
            : api('POST', '/api/admin/catalogo/evaluaciones/' + evId + '/preguntas', payload);
        p.then(function () {
            toast(preguntaId ? 'Pregunta actualizada.' : 'Pregunta agregada.');
            closeDialog($('admin-modal-pregunta'));
            openPreguntasManager(evId);
            loadEvaluaciones();
        }).catch(function (err) {
            toast(err.message, true);
        });
    }

    function bindCatalogForms() {
        var formCurso = $('admin-form-curso');
        var formLeccion = $('admin-form-leccion');
        var formEval = $('admin-form-eval');
        var formPregunta = $('admin-form-pregunta');
        if (formCurso) formCurso.addEventListener('submit', submitCurso);
        if (formLeccion) formLeccion.addEventListener('submit', submitLeccion);
        if (formEval) formEval.addEventListener('submit', submitEval);
        if (formPregunta) formPregunta.addEventListener('submit', submitPregunta);

        document.querySelectorAll('.admin-catalog-cancel').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var dlg = btn.closest('dialog');
                closeDialog(dlg);
            });
        });

        var btnCurso = $('admin-btn-nuevo-curso');
        if (btnCurso) btnCurso.addEventListener('click', function () {
            openCursoModal(null);
        });

        var btnLeccion = $('admin-btn-nueva-leccion');
        if (btnLeccion) btnLeccion.addEventListener('click', openLeccionModal);

        var btnEval = $('admin-btn-nueva-eval');
        if (btnEval) btnEval.addEventListener('click', openEvalModal);

        var btnAddPreg = $('admin-btn-agregar-pregunta-eval');
        if (btnAddPreg) {
            btnAddPreg.addEventListener('click', function () {
                var evId = parseInt($('admin-eval-preguntas-ev-id').value, 10);
                if (evId) openPreguntaModal(evId, null);
            });
        }

        var formEvalEl = $('admin-form-eval');
        if (formEvalEl && formEvalEl.tipo) {
            formEvalEl.tipo.addEventListener('change', toggleEvalLeccionWrap);
        }
        if (formEvalEl && formEvalEl.curso_slug) {
            formEvalEl.curso_slug.addEventListener('change', function () {
                fillLeccionSelectForEval(formEvalEl.curso_slug.value, '');
            });
        }
    }

    function bindCursoTableActions() {
        document.querySelectorAll('.admin-edit-curso').forEach(function (btn) {
            btn.addEventListener('click', function () {
                openCursoModal(btn.getAttribute('data-curso-slug'));
            });
        });
        document.querySelectorAll('.admin-del-curso').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var slug = btn.getAttribute('data-curso-slug');
                var titulo = btn.getAttribute('data-curso-titulo') || slug;
                if (!confirmDelete(titulo)) return;
                api('DELETE', '/api/admin/catalogo/cursos/' + encodeURIComponent(slug))
                    .then(function () {
                        toast('Curso eliminado.');
                        reloadAdmin('cursos');
                    })
                    .catch(function (e) {
                        toast(e.message, true);
                    });
            });
        });
    }

    function init() {
        bindCatalogForms();
        bindCursoTableActions();
        loadCursos()
            .then(function () {
                return Promise.all([loadLecciones(), loadEvaluaciones()]);
            })
            .catch(function (e) {
                toast(e.message || 'No se pudo cargar el catálogo.', true);
            });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
