(function () {

    var grid = document.getElementById('mis-cursos-grid');

    var contador = document.getElementById('mis-cursos-contador');

    var emptyState = document.getElementById('mis-cursos-empty');

    var materiaBtns = document.querySelectorAll('.mis-cursos-filtro-materia');

    var nivelBtns = document.querySelectorAll('.mis-cursos-filtro-nivel');

    var dificultadBtn = document.getElementById('btn-filtro-dificultad');

    var dificultadMenu = document.getElementById('filtro-dificultad-menu');

    var dificultadLabel = document.getElementById('filtro-dificultad-label');

    var dificultadWrap = document.getElementById('filtro-dificultad-wrap');

    var modal = document.getElementById('mis-cursos-modal');

    var modalLista = document.getElementById('mis-cursos-modal-lista');

    var modalCargando = document.getElementById('mis-cursos-modal-cargando');

    var btnAbrirModal = document.getElementById('mis-cursos-abrir-modal');

    var addCard = document.querySelector('.mis-cursos-card-anadir');



    if (!grid || !contador) return;



    var meta = window.MIS_CURSOS_META || {};

    var userId = meta.userId || 0;

    var materiaActiva = 'todas';

    var nivelActivo = 'todas';

    var busquedaActiva = '';

    var catalogoCache = null;

    var slugsEnPagina = new Set();



    function getCards() {

        return grid.querySelectorAll('.mis-cursos-card[data-slug]');

    }



    function refrescarSlugsEnPagina() {

        slugsEnPagina = new Set();

        getCards().forEach(function (card) {

            var slug = card.getAttribute('data-slug');

            if (slug) slugsEnPagina.add(slug);

        });

    }



    function textoContador(n) {

        if (n === 1) return 'Mostrando 1 curso activo';

        return 'Mostrando ' + n + ' cursos activos';

    }



    function textoCoincideBusqueda(card) {
        if (!busquedaActiva) return true;
        var blob = card.getAttribute('data-search') || card.textContent || '';
        if (window.NebulaSearchUtils && window.NebulaSearchUtils.matches) {
            return window.NebulaSearchUtils.matches(busquedaActiva, blob);
        }
        return blob.toLowerCase().indexOf(busquedaActiva.toLowerCase()) !== -1;
    }

    function aplicarFiltros(query) {
        if (typeof query === 'string') {
            busquedaActiva = query.trim();
        }

        var cards = getCards();

        var visibles = 0;

        var emptySearch = document.getElementById('mis-cursos-empty-search');

        cards.forEach(function (card) {

            var materia = card.getAttribute('data-materia');

            var nivel = card.getAttribute('data-nivel');

            var coincideMateria = materiaActiva === 'todas' || materia === materiaActiva;

            var coincideNivel = nivelActivo === 'todas' || nivel === nivelActivo;

            var coincideBusqueda = textoCoincideBusqueda(card);

            var mostrar = coincideMateria && coincideNivel && coincideBusqueda;

            card.style.display = mostrar ? '' : 'none';

            if (mostrar) visibles++;

        });

        contador.textContent = textoContador(visibles);

        if (emptyState) {
            emptyState.classList.toggle('hidden', visibles > 0 || cards.length === 0 || !!busquedaActiva);
        }

        if (emptySearch) {
            emptySearch.classList.toggle('hidden', !busquedaActiva || visibles > 0 || cards.length === 0);
        }
    }

    window.aplicarFiltrosMisCursos = aplicarFiltros;



    function activarBotonMateria(btn) {

        materiaBtns.forEach(function (b) {

            b.classList.remove('mis-cursos-filtro--active');

        });

        btn.classList.add('mis-cursos-filtro--active');

        materiaActiva = btn.getAttribute('data-filtro-materia') || 'todas';

        aplicarFiltros();

    }



    materiaBtns.forEach(function (btn) {

        btn.addEventListener('click', function () {

            activarBotonMateria(btn);

        });

    });



    if (dificultadBtn && dificultadMenu) {

        dificultadBtn.addEventListener('click', function (e) {

            e.stopPropagation();

            dificultadMenu.classList.toggle('hidden');

        });

        document.addEventListener('click', function (e) {

            if (dificultadWrap && !dificultadWrap.contains(e.target)) {

                dificultadMenu.classList.add('hidden');

            }

        });

    }



    nivelBtns.forEach(function (btn) {

        btn.addEventListener('click', function () {

            nivelActivo = btn.getAttribute('data-filtro-nivel') || 'todas';

            if (dificultadLabel) {

                dificultadLabel.textContent =

                    nivelActivo === 'todas' ? 'Dificultad' : nivelActivo;

            }

            if (dificultadMenu) dificultadMenu.classList.add('hidden');

            aplicarFiltros();

        });

    });



    function actualizarAnillo(card, porcentaje) {

        var arc = card.querySelector('.mis-cursos-progress-arc');

        var label = card.querySelector('.mis-cursos-progress-text');

        var pct = Math.max(0, Math.min(100, Math.round(porcentaje)));

        if (arc) arc.setAttribute('stroke-dashoffset', String(100 - pct));

        if (label) label.textContent = pct + '%';

    }



    function sincronizarDesdeLocalStorage() {

        getCards().forEach(function (card) {

            var slug = card.getAttribute('data-slug');

            if (!slug) return;

            try {

                var key = 'nebula_curso_pct_' + userId + '_' + slug;

                var raw = localStorage.getItem(key);

                if (raw !== null) {

                    actualizarAnillo(card, parseInt(raw, 10));

                }

            } catch (e) {

                /* ignore */

            }

        });

    }



    function escaparHtml(texto) {

        var div = document.createElement('div');

        div.textContent = texto == null ? '' : String(texto);

        return div.innerHTML;

    }



    function abrirModal() {

        if (!modal) return;

        modal.classList.remove('hidden');

        modal.setAttribute('aria-hidden', 'false');

        document.body.style.overflow = 'hidden';

        cargarCatalogoModal();

    }



    function cerrarModal() {

        if (!modal) return;

        modal.classList.add('hidden');

        modal.setAttribute('aria-hidden', 'true');

        document.body.style.overflow = '';

    }



    function renderModalCatalogo(catalogo) {

        if (!modalLista) return;

        modalLista.innerHTML = '';

        refrescarSlugsEnPagina();



        if (!catalogo.length) {

            modalLista.innerHTML =

                '<p class="text-center text-sm text-slate-500 dark:text-slate-400 py-8">No hay cursos en el catálogo.</p>';

            return;

        }



        catalogo.forEach(function (item) {

            var asignado = item.asignado || slugsEnPagina.has(item.slug);

            var row = document.createElement('article');

            row.className = 'mis-cursos-modal__item';

            row.setAttribute('data-slug', item.slug);

            row.innerHTML =

                '<img class="mis-cursos-modal__item-img" src="' +

                escaparHtml(item.imagen) +

                '" alt="">' +

                '<div class="mis-cursos-modal__item-body">' +

                '<p class="mis-cursos-modal__item-titulo">' +

                escaparHtml(item.titulo) +

                '</p>' +

                '<p class="mis-cursos-modal__item-meta">' +

                escaparHtml(item.nivel) +

                '</p>' +

                '<p class="mis-cursos-modal__item-desc">' +

                escaparHtml(item.descripcion) +

                '</p>' +

                '</div>' +

                (asignado

                    ? '<span class="mis-cursos-modal__btn-anadir mis-cursos-modal__btn-asignado"><span class="material-symbols-outlined text-[18px]">check</span> Agregado</span>'

                    : '<button type="button" class="mis-cursos-modal__btn-anadir" data-slug="' +

                      escaparHtml(item.slug) +

                      '"><span class="material-symbols-outlined text-[18px]">add</span> Añadir</button>');



            if (!asignado) {

                var btn = row.querySelector('.mis-cursos-modal__btn-anadir');

                btn.addEventListener('click', function () {

                    anadirCurso(item.slug, btn);

                });

            }

            modalLista.appendChild(row);

        });

    }



    function cargarCatalogoModal() {

        if (!modalLista || !modalCargando) return;



        if (catalogoCache) {

            renderModalCatalogo(catalogoCache);

            return;

        }



        modalCargando.classList.remove('hidden');

        modalLista.innerHTML = '';



        fetch('/api/mis-cursos/catalogo', {

            credentials: 'same-origin',

            headers: { Accept: 'application/json' },

        })

            .then(function (res) {

                if (!res.ok) throw new Error('No se pudo cargar el catálogo');

                return res.json();

            })

            .then(function (data) {

                catalogoCache = data.catalogo || [];

                modalCargando.classList.add('hidden');

                renderModalCatalogo(catalogoCache);

            })

            .catch(function () {

                modalCargando.classList.add('hidden');

                modalLista.innerHTML =

                    '<p class="text-center text-sm text-red-500 py-8">Error al cargar el catálogo. Intenta de nuevo.</p>';

            });

    }



    function marcarAsignadoEnModal(slug) {

        if (!modalLista) return;

        var row = modalLista.querySelector('.mis-cursos-modal__item[data-slug="' + slug + '"]');

        if (!row) return;

        var btn = row.querySelector('.mis-cursos-modal__btn-anadir');

        if (!btn) return;

        var span = document.createElement('span');

        span.className = 'mis-cursos-modal__btn-anadir mis-cursos-modal__btn-asignado mis-cursos-modal__btn-anadir--success';

        span.innerHTML = '<span class="material-symbols-outlined text-[18px]">check</span> Agregado';

        btn.replaceWith(span);

        if (catalogoCache) {

            catalogoCache.forEach(function (c) {

                if (c.slug === slug) c.asignado = true;

            });

        }

    }



    function anadirCurso(slug, btn) {

        if (!slug || slugsEnPagina.has(slug)) return;

        if (btn) {

            btn.disabled = true;

            btn.textContent = 'Añadiendo...';

        }



        fetch('/api/asignar-curso/' + encodeURIComponent(slug), {

            method: 'POST',

            credentials: 'same-origin',

            headers: {

                Accept: 'application/json',

                'X-Requested-With': 'XMLHttpRequest',

            },

        })

            .then(function (res) {

                return res.json().then(function (data) {

                    if (!res.ok) throw new Error(data.error || 'Error al asignar');

                    return data;

                });

            })

            .then(function (data) {

                if (!data.html || !addCard) return;

                addCard.insertAdjacentHTML('beforebegin', data.html);

                slugsEnPagina.add(slug);

                try {

                    localStorage.setItem('nebula_curso_pct_' + userId + '_' + slug, '0');

                } catch (e) {

                    /* ignore */

                }

                if (window.NebulaCursosActivos && data.curso_activo) {

                    window.NebulaCursosActivos.add(data.curso_activo, { highlightSelect: true });

                }

                sincronizarDesdeLocalStorage();

                aplicarFiltros();

                marcarAsignadoEnModal(slug);

            })

            .catch(function () {

                if (btn) {

                    btn.disabled = false;

                    btn.innerHTML =

                        '<span class="material-symbols-outlined text-[18px]">add</span> Añadir';

                }

                alert('No se pudo añadir el curso. Intenta de nuevo.');

            });

    }



    if (btnAbrirModal) {

        btnAbrirModal.addEventListener('click', abrirModal);

    }



    if (modal) {

        modal.querySelectorAll('[data-cerrar-modal]').forEach(function (el) {

            el.addEventListener('click', cerrarModal);

        });

        document.addEventListener('keydown', function (e) {

            if (e.key === 'Escape' && !modal.classList.contains('hidden')) {

                cerrarModal();

            }

        });

    }



    refrescarSlugsEnPagina();

    aplicarFiltros();

    sincronizarDesdeLocalStorage();

    if (window.NebulaCursosActivos) {

        window.NebulaCursosActivos.init({

            userId: userId,

            initial: meta.cursosActivos || [],

            syncDom: true,

            root: grid,

            fetch: true,

        });

    }

})();


