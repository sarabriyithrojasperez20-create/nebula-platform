/**
 * Utilidades de búsqueda Nébula — normalización, coincidencias y filtrado DOM.
 */
(function (global) {
    'use strict';

    var ACCENT_MAP = {
        á: 'a', à: 'a', ä: 'a', â: 'a', ã: 'a',
        é: 'e', è: 'e', ë: 'e', ê: 'e',
        í: 'i', ì: 'i', ï: 'i', î: 'i',
        ó: 'o', ò: 'o', ö: 'o', ô: 'o', õ: 'o',
        ú: 'u', ù: 'u', ü: 'u', û: 'u',
        ñ: 'n', ç: 'c',
    };

    function normalize(text) {
        var s = String(text == null ? '' : text).toLowerCase().trim();
        s = s.replace(/[áàäâãéèëêíìïîóòöôõúùüûñç]/g, function (ch) {
            return ACCENT_MAP[ch] || ch;
        });
        return s.normalize ? s.normalize('NFD').replace(/[\u0300-\u036f]/g, '') : s;
    }

    function matches(query, haystack) {
        var q = normalize(query);
        if (!q) return true;
        return normalize(haystack).indexOf(q) !== -1;
    }

    function debounce(fn, wait) {
        var timer;
        return function () {
            var ctx = this;
            var args = arguments;
            clearTimeout(timer);
            timer = setTimeout(function () {
                fn.apply(ctx, args);
            }, wait == null ? 180 : wait);
        };
    }

    function textFromElement(el) {
        if (!el) return '';
        var parts = [];
        if (el.getAttribute('data-search')) {
            parts.push(el.getAttribute('data-search'));
        }
        if (el.dataset) {
            Object.keys(el.dataset).forEach(function (key) {
                if (key.indexOf('search') === 0 && key !== 'search') {
                    parts.push(el.dataset[key]);
                }
            });
        }
        parts.push(el.textContent || '');
        return parts.join(' ');
    }

    function filterElements(items, query, options) {
        var opts = options || {};
        var q = (query || '').trim();
        var visible = 0;
        items.forEach(function (el) {
            if (!el || el.classList.contains('nb-search-skip')) return;
            var ok = matches(q, textFromElement(el));
            el.style.display = ok ? '' : 'none';
            el.classList.toggle('nb-search-hidden', !ok);
            if (ok) visible += 1;
        });
        return visible;
    }

    function bindInput(input, onSearch) {
        if (!input || input._nebulaSearchBound) return;
        input._nebulaSearchBound = true;
        var handler = debounce(function () {
            onSearch((input.value || '').trim());
        }, 160);
        input.addEventListener('input', handler);
        input.addEventListener('search', handler);
    }

    function showEmptyMessage(container, show, message) {
        if (!container) return;
        var el = container.querySelector('.nb-search-empty');
        if (show) {
            if (!el) {
                el = document.createElement('p');
                el.className = 'nb-search-empty text-sm text-slate-500 dark:text-slate-400 text-center py-6';
                container.appendChild(el);
            }
            el.textContent = message || 'No se encontraron resultados para tu búsqueda.';
            el.classList.remove('hidden');
        } else if (el) {
            el.classList.add('hidden');
        }
    }

    global.NebulaSearchUtils = {
        normalize: normalize,
        matches: matches,
        debounce: debounce,
        textFromElement: textFromElement,
        filterElements: filterElements,
        bindInput: bindInput,
        showEmptyMessage: showEmptyMessage,
    };
})(typeof window !== 'undefined' ? window : this);
