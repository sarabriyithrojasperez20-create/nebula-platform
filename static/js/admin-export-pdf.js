/**
 * Exportación PDF por estudiante y masiva (ZIP) — jsPDF + JSZip.
 */
(function (win) {
    'use strict';

    win = win || (typeof window !== 'undefined' ? window : this);

    var estudiantes = [];
    var periodoActual = { dias: 30, desde: '', hasta: '', etiqueta: 'Último mes' };

    function $(id) {
        return document.getElementById(id);
    }

    function toast(msg, err) {
        var t = $('admin-export-toast');
        if (!t) return;
        t.textContent = msg;
        t.className = 'nb-toast' + (err ? ' nb-toast--err' : '');
        t.classList.remove('hidden');
        clearTimeout(toast._tm);
        toast._tm = setTimeout(function () {
            t.classList.add('hidden');
        }, 4200);
    }

    function escapeHtml(s) {
        return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function getPeriodoFromPage() {
        if (win.NebulaAnalyticsAdmin && win.NebulaAnalyticsAdmin.getPeriodo) {
            return win.NebulaAnalyticsAdmin.getPeriodo();
        }
        var sel = $('analytics-periodo');
        if (sel) {
            return {
                dias: parseInt(sel.value, 10) || 30,
                etiqueta: sel.options[sel.selectedIndex].text,
                desde: '',
                hasta: '',
            };
        }
        return periodoActual;
    }

    function syncPeriodoToModal(periodo) {
        periodo = periodo || getPeriodoFromPage();
        periodoActual = periodo;
        var desde = $('export-desde');
        var hasta = $('export-hasta');
        if (periodo.desde && desde) desde.value = periodo.desde;
        if (periodo.hasta && hasta) hasta.value = periodo.hasta;
        if (!periodo.desde && periodo.dias) {
            var h = new Date();
            var d = new Date();
            d.setDate(h.getDate() - (parseInt(periodo.dias, 10) - 1));
            if (desde) desde.value = d.toISOString().slice(0, 10);
            if (hasta) hasta.value = h.toISOString().slice(0, 10);
        }
    }

    function setExportLoading(on, label) {
        var btn = $('analytics-exportar');
        var icon = $('analytics-exportar-icon');
        var lbl = $('analytics-exportar-label');
        if (btn) {
            btn.disabled = !!on;
            btn.classList.toggle('aa-btn-export--loading', !!on);
        }
        if (icon) icon.textContent = on ? 'hourglass_top' : 'picture_as_pdf';
        if (lbl && label) lbl.textContent = label;
        else if (lbl && !on) lbl.textContent = 'Exportar reporte';
    }

    function openModal(periodo) {
        var m = $('admin-export-modal');
        if (!m) return;
        syncPeriodoToModal(periodo || getPeriodoFromPage());
        m.classList.remove('hidden');
        document.body.classList.add('nb-modal-open');
        loadEstudiantes();
    }

    function closeModal() {
        var m = $('admin-export-modal');
        if (m) m.classList.add('hidden');
        document.body.classList.remove('nb-modal-open');
    }

    async function loadEstudiantes() {
        try {
            var res = await fetch('/api/admin/estudiantes', { credentials: 'same-origin' });
            var data = await res.json().catch(function () {
                return {};
            });
            if (data.ok && data.estudiantes) {
                estudiantes = data.estudiantes.filter(function (e) {
                    return e.activo !== false;
                });
                fillSelect(estudiantes);
            }
        } catch (e) {
            toast('No se pudo cargar la lista de estudiantes.', true);
        }
    }

    function fillSelect(list) {
        var sel = $('export-estudiante');
        if (!sel) return;
        var q = ($('export-buscar') && $('export-buscar').value) || '';
        q = q.toLowerCase();
        var filtered = list.filter(function (e) {
            if (!q) return true;
            return (
                (e.nombre_completo || '').toLowerCase().indexOf(q) >= 0 ||
                (e.correo || '').toLowerCase().indexOf(q) >= 0
            );
        });
        sel.innerHTML =
            '<option value="">Selecciona un estudiante</option>' +
            filtered
                .map(function (e) {
                    return (
                        '<option value="' +
                        e.id_usuario +
                        '">' +
                        escapeHtml(e.nombre_completo) +
                        ' — ' +
                        escapeHtml(e.grado || 'Sin grado') +
                        '</option>'
                    );
                })
                .join('');
    }

    function reporteUrl(id, tipo, desde, hasta) {
        var url = '/api/admin/estudiantes/' + id + '/reporte?tipo=' + encodeURIComponent(tipo || 'completo');
        if (desde) url += '&desde=' + encodeURIComponent(desde);
        if (hasta) url += '&hasta=' + encodeURIComponent(hasta);
        return url;
    }

    async function fetchReporte(id, tipo, desde, hasta) {
        var res = await fetch(reporteUrl(id, tipo, desde, hasta), { credentials: 'same-origin' });
        var data = await res.json().catch(function () {
            return {};
        });
        if (!res.ok || !data.ok) throw new Error(data.mensaje || 'Error al obtener reporte');
        return data.reporte;
    }

    async function updatePreview() {
        var id = $('export-estudiante') && $('export-estudiante').value;
        var body = $('export-preview-body');
        if (!body) return;
        if (!id) {
            body.innerHTML =
                '<p class="text-sm text-[var(--nb-text-muted)]">Selecciona un estudiante para ver el resumen.</p>';
            return;
        }
        var tipo = $('export-tipo') ? $('export-tipo').value : 'completo';
        var desde = $('export-desde') ? $('export-desde').value : '';
        var hasta = $('export-hasta') ? $('export-hasta').value : '';
        body.innerHTML = '<p class="text-sm">Cargando vista previa…</p>';
        try {
            var r = await fetchReporte(id, tipo, desde, hasta);
            var st = r.estudiante;
            var m = r.metricas;
            body.innerHTML =
                '<div class="admin-export-preview__student">' +
                '<strong>' +
                escapeHtml(st.nombre_completo) +
                '</strong>' +
                '<span>' +
                escapeHtml(st.correo) +
                ' · ' +
                escapeHtml(st.grado) +
                '</span></div>' +
                '<ul class="admin-export-preview__metrics">' +
                '<li>Periodo: <b>' +
                escapeHtml(r.rango.desde) +
                ' — ' +
                escapeHtml(r.rango.hasta) +
                '</b></li>' +
                '<li>Progreso promedio: <b>' +
                m.progreso_promedio +
                '%</b></li>' +
                '<li>Lecciones en periodo: <b>' +
                m.lecciones_completadas +
                '</b></li>' +
                '<li>Quizzes en periodo: <b>' +
                (m.quizzes_total != null ? m.quizzes_total : m.evaluaciones_total) +
                '</b></li>' +
                '</ul>';
        } catch (err) {
            body.innerHTML = '<p class="text-sm" style="color:#dc2626">' + escapeHtml(err.message) + '</p>';
        }
    }

    function pdfEnsureSpace(doc, y, need) {
        if (y + need > 275) {
            doc.addPage();
            return 20;
        }
        return y;
    }

    function generarPdfDocumento(reporte) {
        var jsPDF = win.jspdf && win.jspdf.jsPDF;
        if (!jsPDF) throw new Error('Biblioteca PDF no cargada.');
        var doc = new jsPDF({ unit: 'mm', format: 'a4' });
        var st = reporte.estudiante;
        var m = reporte.metricas;
        var y = 18;

        doc.setFillColor(109, 74, 255);
        doc.rect(0, 0, 210, 30, 'F');
        doc.setTextColor(255, 255, 255);
        doc.setFontSize(17);
        doc.text('Nébula — Reporte académico', 14, 15);
        doc.setFontSize(9);
        doc.text('Generado: ' + (reporte.generado_en || ''), 14, 22);
        doc.text(
            'Periodo: ' + (reporte.rango.desde || '—') + '  a  ' + (reporte.rango.hasta || '—'),
            14,
            27
        );

        doc.setTextColor(30, 30, 40);
        y = 40;
        doc.setFontSize(14);
        doc.text(st.nombre_completo || 'Estudiante', 14, y);
        y += 7;
        doc.setFontSize(10);
        doc.setTextColor(100, 100, 120);
        doc.text((st.correo || '') + '  |  ' + (st.grado || ''), 14, y);
        y += 5;
        doc.text('ID #' + (st.id_usuario || ''), 14, y);
        y += 12;

        doc.setTextColor(30, 30, 40);
        doc.setFontSize(12);
        doc.text('Resumen del periodo', 14, y);
        y += 8;
        doc.setFontSize(10);
        [
            'Progreso general (cursos): ' + (m.progreso_promedio || 0) + '%',
            'Cursos asignados: ' + (m.cursos_asignados || 0),
            'Lecciones completadas en periodo: ' + (m.lecciones_completadas || 0),
            'Quizzes / evaluaciones en periodo: ' +
                (m.quizzes_total != null ? m.quizzes_total : m.evaluaciones_total || 0),
            'Quizzes aprobados: ' + (m.quizzes_aprobados || 0),
            'Quizzes no aprobados: ' + (m.quizzes_no_aprobados || 0),
        ].forEach(function (line) {
            y = pdfEnsureSpace(doc, y, 8);
            doc.text(line, 18, y);
            y += 6;
        });
        y += 6;

        var lecciones = reporte.lecciones || [];
        if (lecciones.length) {
            y = pdfEnsureSpace(doc, y, 16);
            doc.setFontSize(12);
            doc.text('Lecciones', 14, y);
            y += 7;
            doc.setFontSize(9);
            lecciones.forEach(function (lec) {
                y = pdfEnsureSpace(doc, y, 10);
                var titulo = (lec.leccion || lec.leccion_id || 'Lección').substring(0, 55);
                doc.text('• ' + titulo, 16, y);
                y += 4;
                doc.setTextColor(120, 120, 130);
                doc.text(
                    '   Curso: ' +
                        (lec.curso || '—') +
                        '  |  Estado: ' +
                        (lec.estado || 'Completada') +
                        '  |  Fecha: ' +
                        (lec.fecha || '—'),
                    16,
                    y
                );
                doc.setTextColor(30, 30, 40);
                y += 6;
            });
            y += 4;
        }

        var quizzes = reporte.quizzes || [];
        if (quizzes.length) {
            y = pdfEnsureSpace(doc, y, 16);
            doc.setFontSize(12);
            doc.text('Quizzes y evaluaciones', 14, y);
            y += 7;
            doc.setFontSize(9);
            quizzes.forEach(function (qz) {
                y = pdfEnsureSpace(doc, y, 10);
                var nombre = (qz.tema || 'Quiz').substring(0, 50);
                var tipo = qz.tipo === 'diagnostico' ? 'Diagnóstico' : 'Quiz final';
                doc.text('• [' + tipo + '] ' + nombre, 16, y);
                y += 4;
                doc.setTextColor(120, 120, 130);
                var estado =
                    qz.aprobado === true
                        ? 'Aprobado'
                        : qz.aprobado === false
                          ? 'No aprobado'
                          : 'Completado';
                doc.text(
                    '   Curso: ' +
                        (qz.curso || '—') +
                        '  |  Calificación: ' +
                        (qz.porcentaje != null ? qz.porcentaje : '—') +
                        '%  |  ' +
                        estado +
                        '  |  Fecha: ' +
                        (qz.fecha || '—'),
                    16,
                    y
                );
                doc.setTextColor(30, 30, 40);
                y += 6;
            });
        }

        if (reporte.cursos && reporte.cursos.length) {
            y = pdfEnsureSpace(doc, y, 14);
            doc.setFontSize(12);
            doc.text('Progreso por curso', 14, y);
            y += 8;
            doc.setFontSize(10);
            reporte.cursos.forEach(function (c) {
                y = pdfEnsureSpace(doc, y, 6);
                doc.text('• ' + (c.titulo || c.slug) + ': ' + (c.progreso || 0) + '%', 18, y);
                y += 6;
            });
        }

        doc.setFontSize(8);
        doc.setTextColor(150, 150, 160);
        doc.text('Documento generado por Nébula Admin', 14, 287);

        return doc;
    }

    function safeFilename(nombre) {
        return (nombre || 'estudiante')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .replace(/[^\w\s-]/g, '')
            .trim()
            .replace(/\s+/g, '_')
            .substring(0, 48);
    }

    function generarPdf(reporte) {
        var doc = generarPdfDocumento(reporte);
        var st = reporte.estudiante;
        doc.save('nebula-reporte-' + safeFilename(st.nombre_completo) + '.pdf');
    }

    function generarPdfBlob(reporte) {
        var doc = generarPdfDocumento(reporte);
        return doc.output('blob');
    }

    async function onGenerarUno() {
        var id = $('export-estudiante') && $('export-estudiante').value;
        if (!id) {
            toast('Selecciona un estudiante.', true);
            return;
        }
        var btn = $('export-generar-pdf');
        if (btn) btn.disabled = true;
        try {
            var desde = $('export-desde').value;
            var hasta = $('export-hasta').value;
            var reporte = await fetchReporte(id, $('export-tipo').value, desde, hasta);
            generarPdf(reporte);
            toast('PDF generado correctamente.');
            closeModal();
        } catch (err) {
            toast(err.message, true);
        } finally {
            if (btn) btn.disabled = false;
        }
    }

    async function exportarTodosZip() {
        if (!win.JSZip) {
            toast('JSZip no está cargado.', true);
            return;
        }
        syncPeriodoToModal(getPeriodoFromPage());
        var desde = $('export-desde') && $('export-desde').value;
        var hasta = $('export-hasta') && $('export-hasta').value;
        var lista = estudiantes.length ? estudiantes : [];

        if (!lista.length) {
            await loadEstudiantes();
            lista = estudiantes;
        }
        if (!lista.length) {
            toast('No hay estudiantes para exportar.', true);
            return;
        }

        setExportLoading(true, 'Generando ZIP…');
        var btnModal = $('export-generar-zip');
        if (btnModal) btnModal.disabled = true;

        try {
            var zip = new win.JSZip();
            var ok = 0;
            var errores = 0;

            for (var i = 0; i < lista.length; i++) {
                var est = lista[i];
                setExportLoading(true, 'PDF ' + (i + 1) + '/' + lista.length + '…');
                try {
                    var reporte = await fetchReporte(est.id_usuario, 'completo', desde, hasta);
                    var blob = generarPdfBlob(reporte);
                    zip.file('nebula-reporte-' + safeFilename(est.nombre_completo) + '.pdf', blob);
                    ok++;
                } catch (e) {
                    errores++;
                    console.warn(est.id_usuario, e);
                }
            }

            if (ok === 0) {
                throw new Error('No se pudo generar ningún reporte.');
            }

            var zipBlob = await zip.generateAsync({ type: 'blob' });
            var a = document.createElement('a');
            a.href = URL.createObjectURL(zipBlob);
            a.download =
                'nebula-reportes-' +
                (desde || 'inicio') +
                '_' +
                (hasta || 'fin') +
                '.zip';
            document.body.appendChild(a);
            a.click();
            setTimeout(function () {
                URL.revokeObjectURL(a.href);
                a.remove();
            }, 400);

            toast(
                'ZIP descargado (' +
                    ok +
                    ' PDF' +
                    (errores ? ', ' + errores + ' omitidos' : '') +
                    ').'
            );
            closeModal();
        } catch (err) {
            toast(err.message, true);
        } finally {
            setExportLoading(false);
            if (btnModal) btnModal.disabled = false;
        }
    }

    function bind() {
        document.querySelectorAll('[data-export-close]').forEach(function (el) {
            el.addEventListener('click', closeModal);
        });
        var buscar = $('export-buscar');
        if (buscar) {
            buscar.addEventListener('input', function () {
                fillSelect(estudiantes);
            });
        }
        ['export-estudiante', 'export-tipo', 'export-desde', 'export-hasta'].forEach(function (id) {
            var el = $(id);
            if (el) el.addEventListener('change', updatePreview);
        });
        var gen = $('export-generar-pdf');
        if (gen) gen.addEventListener('click', onGenerarUno);
        var zipBtn = $('export-generar-zip');
        if (zipBtn) zipBtn.addEventListener('click', exportarTodosZip);

        var exportBtn = $('analytics-exportar');
        if (exportBtn) {
            exportBtn.addEventListener('click', function (e) {
                e.preventDefault();
                exportarTodosZip();
            });
        }

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && $('admin-export-modal') && !$('admin-export-modal').classList.contains('hidden')) {
                closeModal();
            }
        });
    }

    win.NebulaAdminExport = {
        open: openModal,
        openModal: openModal,
        close: closeModal,
        closeModal: closeModal,
        toast: toast,
        exportAll: exportarTodosZip,
        generarPdf: generarPdf,
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bind);
    } else {
        bind();
    }
})(typeof window !== 'undefined' ? window : this);
