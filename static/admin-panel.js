(function () {
    var resumen = document.getElementById('admin-dashboard-resumen');
    var widgets = document.getElementById('admin-dashboard-widgets');
    var widgets2 = document.getElementById('admin-dashboard-widgets-2');
    var welcome = document.querySelector('.max-w-container-max > section.space-y-1');

    function seccionesResumen() {
        var list = [];
        if (welcome) list.push(welcome);
        if (resumen) list.push(resumen);
        if (widgets) list.push(widgets);
        if (widgets2) list.push(widgets2);
        return list;
    }

    function mostrarPanel(nombre) {
        document.querySelectorAll('.admin-detail-panel').forEach(function (panel) {
            panel.classList.add('hidden');
        });
        seccionesResumen().forEach(function (el) {
            el.classList.add('hidden');
        });

        var panel = document.getElementById('admin-panel-' + nombre);
        if (panel) {
            panel.classList.remove('hidden');
            panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }

    function volverResumen() {
        document.querySelectorAll('.admin-detail-panel').forEach(function (panel) {
            panel.classList.add('hidden');
        });
        seccionesResumen().forEach(function (el) {
            el.classList.remove('hidden');
        });
        var detalle = document.getElementById('admin-usuario-detalle');
        if (detalle) detalle.classList.add('hidden');
        if (resumen) {
            resumen.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }

    document.querySelectorAll('[data-admin-panel]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var panel = btn.getAttribute('data-admin-panel');
            if (panel) mostrarPanel(panel);
        });
    });

    document.querySelectorAll('[data-admin-back]').forEach(function (btn) {
        btn.addEventListener('click', volverResumen);
    });

    document.querySelectorAll('.admin-ver-curso').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var slug = btn.getAttribute('data-curso-slug');
            document.querySelectorAll('.admin-curso-estudiantes').forEach(function (row) {
                if (row.getAttribute('data-curso-estudiantes') === slug) {
                    row.classList.toggle('hidden');
                }
            });
        });
    });

    var usuariosJson = document.getElementById('admin-usuarios-json');
    var usuariosData = [];
    if (usuariosJson) {
        try {
            usuariosData = JSON.parse(usuariosJson.textContent);
        } catch (e) {
            usuariosData = [];
        }
    }

    function renderDetalleUsuario(id) {
        var u = usuariosData.find(function (item) {
            return String(item.id_usuario) === String(id);
        });
        if (!u) return;

        var box = document.getElementById('admin-usuario-detalle');
        var nombre = document.getElementById('admin-detalle-nombre');
        var contenido = document.getElementById('admin-detalle-contenido');
        if (!box || !nombre || !contenido) return;

        nombre.textContent = u.nombre_completo;
        var html = '';
        html += '<p><strong>Correo:</strong> ' + u.correo + '</p>';
        html += '<p><strong>Username:</strong> @' + u.username + '</p>';
        html += '<p><strong>Rol:</strong> ' + u.rol + '</p>';
        html += '<p><strong>Grado:</strong> ' + (u.grado || '—') + '</p>';
        html += '<p><strong>Estado:</strong> ' + (u.activo ? 'Activo' : 'Inactivo') + '</p>';
        html += '<p><strong>Fecha de registro:</strong> ' + u.fecha_registro + '</p>';

        html += '<div class="mt-4"><strong>Cursos asignados y progreso</strong><ul class="list-disc pl-5 mt-2">';
        if (u.cursos_asignados && u.cursos_asignados.length) {
            u.cursos_asignados.forEach(function (c) {
                var diag = c.diagnostico
                    ? ' — Diagnóstico: ' + (c.diagnostico.titulo_nivel || c.diagnostico.nivel) + ' (' + c.diagnostico.porcentaje + '%)'
                    : ' — Sin diagnóstico';
                html += '<li>' + c.titulo + ': ' + c.progreso + '%' + diag + '</li>';
            });
        } else {
            html += '<li>Sin cursos asignados</li>';
        }
        html += '</ul></div>';

        html += '<div class="mt-4"><strong>Lecciones completadas (' + u.total_lecciones_completadas + ')</strong><ul class="list-disc pl-5 mt-2">';
        if (u.lecciones_completadas && u.lecciones_completadas.length) {
            u.lecciones_completadas.forEach(function (l) {
                html += '<li>' + l.curso + ' — ' + l.leccion + '</li>';
            });
        } else {
            html += '<li>Ninguna lección completada</li>';
        }
        html += '</ul></div>';

        html += '<div class="mt-4"><strong>Evaluaciones</strong><ul class="list-disc pl-5 mt-2">';
        if (u.evaluaciones && u.evaluaciones.length) {
            u.evaluaciones.forEach(function (ev) {
                var estado =
                    ev.tipo === 'diagnostico'
                        ? ev.nivel || '—'
                        : ev.aprobado
                          ? 'Aprobado'
                          : 'No aprobado';
                html += '<li>' + ev.tipo + ' — ' + ev.curso + ' / ' + ev.tema + ': ' + ev.porcentaje + '% (' + estado + ')</li>';
            });
        } else {
            html += '<li>Sin evaluaciones registradas</li>';
        }
        html += '</ul></div>';

        html += '<p class="mt-4"><strong>Quizzes finales:</strong> ' + u.quizzes_aprobados + ' aprobados, ' + u.quizzes_no_aprobados + ' no aprobados</p>';

        contenido.innerHTML = html;
        box.classList.remove('hidden');
        box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    document.querySelectorAll('.admin-ver-usuario').forEach(function (btn) {
        btn.addEventListener('click', function () {
            renderDetalleUsuario(btn.getAttribute('data-usuario-id'));
        });
    });

    document.querySelectorAll('.admin-cerrar-detalle').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var box = document.getElementById('admin-usuario-detalle');
            if (box) box.classList.add('hidden');
        });
    });

    try {
        var pendingPanel = sessionStorage.getItem('nebula_admin_panel');
        if (pendingPanel) {
            sessionStorage.removeItem('nebula_admin_panel');
            mostrarPanel(pendingPanel);
        }
    } catch (e) {
        /* ignore */
    }
})();
