/**
 * Cursos activos del estudiante — selector CURSO / MATERIA y sincronización con el catálogo.
 */
(function (global) {
    'use strict';

    var EVENT_NAME = 'nebula:cursos-actualizados';
    var STORAGE_PREFIX = 'nebula_cursos_activos_';

    var state = {
        userId: 0,
        cursos: [],
        loaded: false,
        navigateOnSelect: true,
        selects: [],
    };

    function storageKey() {
        return STORAGE_PREFIX + (state.userId || '0');
    }

    function readCache() {
        try {
            var raw = localStorage.getItem(storageKey());
            if (!raw) return null;
            var data = JSON.parse(raw);
            return Array.isArray(data) ? data : null;
        } catch (e) {
            return null;
        }
    }

    function writeCache(cursos) {
        try {
            localStorage.setItem(storageKey(), JSON.stringify(cursos));
        } catch (e) {
            /* ignore */
        }
    }

    function slugSet() {
        var set = {};
        state.cursos.forEach(function (c) {
            if (c && c.slug) set[c.slug] = true;
        });
        return set;
    }

    function hasSlug(slug) {
        return Boolean(slug && slugSet()[slug]);
    }

    function normalizeCurso(item) {
        if (!item || !item.slug) return null;
        return {
            slug: item.slug,
            titulo: item.titulo || item.slug,
            materia: item.materia || 'todas',
            nivel: item.nivel || '',
            imagen: item.imagen || '',
            url: item.url || '/curso/' + encodeURIComponent(item.slug),
        };
    }

    function mergeCursos(list) {
        var map = {};
        state.cursos.forEach(function (c) {
            map[c.slug] = c;
        });
        (list || []).forEach(function (item) {
            var c = normalizeCurso(item);
            if (c) map[c.slug] = c;
        });
        state.cursos = Object.keys(map).map(function (k) {
            return map[k];
        });
        state.cursos.sort(function (a, b) {
            return (a.titulo || '').localeCompare(b.titulo || '', 'es');
        });
    }

    function dispatchUpdate() {
        writeCache(state.cursos);
        var detail = { cursos: state.cursos.slice(), total: state.cursos.length };
        try {
            global.dispatchEvent(new CustomEvent(EVENT_NAME, { detail: detail }));
        } catch (e) {
            /* IE fallback omitido */
        }
        renderAllSelects();
    }

    function buildPlaceholderOption(select) {
        var opt = document.createElement('option');
        opt.value = '';
        opt.textContent =
            select.getAttribute('data-placeholder') ||
            'Selecciona un curso añadido';
        opt.disabled = true;
        opt.selected = true;
        return opt;
    }

    function renderSelect(select) {
        if (!select) return;
        var prev = select.value;
        var animate = select.classList.contains('nb-curso-select__field');
        if (animate) select.classList.add('nb-curso-select__field--refresh');

        select.innerHTML = '';
        select.appendChild(buildPlaceholderOption(select));

        state.cursos.forEach(function (c) {
            var opt = document.createElement('option');
            opt.value = c.slug;
            opt.textContent = c.titulo;
            opt.dataset.url = c.url;
            select.appendChild(opt);
        });

        if (prev && hasSlug(prev)) {
            select.value = prev;
        }

        select.disabled = state.cursos.length === 0;
        select.classList.toggle('nb-curso-select__field--empty', state.cursos.length === 0);

        if (animate) {
            global.setTimeout(function () {
                select.classList.remove('nb-curso-select__field--refresh');
            }, 320);
        }
    }

    function renderAllSelects() {
        state.selects.forEach(renderSelect);
        document.querySelectorAll('[data-nebula-curso-select]').forEach(function (el) {
            if (state.selects.indexOf(el) === -1) {
                registerSelect(el);
                renderSelect(el);
            }
        });
    }

    function onSelectChange(ev) {
        var select = ev.target;
        var slug = select.value;
        if (!slug) return;
        var curso = state.cursos.find(function (c) {
            return c.slug === slug;
        });
        var url = (curso && curso.url) || select.selectedOptions[0]?.dataset?.url;
        if (!url) return;

        var navigate =
            select.getAttribute('data-navigate') !== 'false' && state.navigateOnSelect;
        if (navigate && url) {
            global.location.assign(url);
        }
    }

    function registerSelect(select) {
        if (!select || state.selects.indexOf(select) >= 0) return;
        state.selects.push(select);
        select.addEventListener('change', onSelectChange);
    }

    function addCurso(item, options) {
        var c = normalizeCurso(item);
        if (!c || hasSlug(c.slug)) {
            if (c && hasSlug(c.slug)) dispatchUpdate();
            return false;
        }
        state.cursos.push(c);
        dispatchUpdate();
        if (options && options.highlightSelect) {
            state.selects.forEach(function (sel) {
                sel.classList.add('nb-curso-select--pulse');
                global.setTimeout(function () {
                    sel.classList.remove('nb-curso-select--pulse');
                }, 600);
            });
        }
        return true;
    }

    function syncFromDom(root) {
        var container = root || document;
        var nodes = container.querySelectorAll('[data-slug]');
        var list = [];
        nodes.forEach(function (node) {
            var slug = node.getAttribute('data-slug');
            if (!slug) return;
            if (node.classList.contains('mis-cursos-card-anadir')) return;
            var titulo =
                node.querySelector('.mis-cursos-card__title, h3')?.textContent?.trim() ||
                slug;
            list.push({
                slug: slug,
                titulo: titulo,
                url: '/curso/' + encodeURIComponent(slug),
            });
        });
        if (list.length) mergeCursos(list);
    }

    function fetchActivos() {
        return fetch('/api/mis-cursos/activos', {
            credentials: 'same-origin',
            headers: { Accept: 'application/json' },
        })
            .then(function (res) {
                if (!res.ok) throw new Error('No autorizado');
                return res.json();
            })
            .then(function (data) {
                mergeCursos(data.cursos || []);
                state.loaded = true;
                dispatchUpdate();
                return state.cursos;
            });
    }

    function init(options) {
        options = options || {};
        state.userId = options.userId || 0;
        state.navigateOnSelect = options.navigateOnSelect !== false;

        if (Array.isArray(options.initial)) {
            mergeCursos(options.initial);
        } else {
            var cached = readCache();
            if (cached && cached.length) mergeCursos(cached);
        }

        if (options.syncDom !== false) syncFromDom(options.root || document);

        var selector =
            options.select ||
            document.getElementById('nb-curso-materia-select');
        if (selector) registerSelect(selector);

        document.querySelectorAll('[data-nebula-curso-select]').forEach(registerSelect);
        renderAllSelects();

        if (options.fetch !== false) {
            return fetchActivos().catch(function () {
                dispatchUpdate();
                return state.cursos;
            });
        }
        dispatchUpdate();
        return Promise.resolve(state.cursos);
    }

    global.NebulaCursosActivos = {
        EVENT: EVENT_NAME,
        init: init,
        load: fetchActivos,
        add: addCurso,
        has: hasSlug,
        getCursos: function () {
            return state.cursos.slice();
        },
        registerSelect: registerSelect,
        renderSelect: renderSelect,
    };
})(window);
