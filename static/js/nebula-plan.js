/**
 * Plan Pro — modal de confirmación y activación (dashboard estudiante).
 */
(function () {
    'use strict';

    var modal = null;
    var payBtn = null;
    var upgradeBtn = null;

    function toast(msg, isError) {
        var el = document.getElementById('nb-plan-toast');
        if (!el) {
            if (isError) alert(msg);
            return;
        }
        el.textContent = msg;
        el.className =
            'fixed bottom-5 right-5 z-[300] max-w-sm px-4 py-3 rounded-xl text-sm font-semibold shadow-lg ' +
            (isError ? 'bg-red-600 text-white' : 'bg-primary text-white');
        el.classList.remove('hidden');
        clearTimeout(toast._tm);
        toast._tm = setTimeout(function () {
            el.classList.add('hidden');
        }, 3500);
    }

    function renderActivo(widget) {
        widget.setAttribute('data-plan', 'pro');
        widget.innerHTML =
            '<p class="text-xs font-semibold text-primary uppercase tracking-wider mb-2">Plan Pro</p>' +
            '<p class="text-xs text-slate-600 mb-3">Tienes acceso ampliado al tutor con IA.</p>' +
            '<div class="w-full py-2 text-center bg-white/80 text-primary text-xs font-bold rounded-lg border border-primary/25">' +
            'Plan activo</div>';
    }

    function openModal() {
        if (!modal) return;
        modal.classList.remove('hidden');
        modal.setAttribute('aria-hidden', 'false');
        document.body.classList.add('nb-plan-modal-open');
        if (payBtn) {
            payBtn.disabled = false;
            payBtn.innerHTML =
                '<span class="material-symbols-outlined text-[18px]" aria-hidden="true">payments</span>' +
                ' Confirmar y activar';
        }
        setTimeout(function () {
            if (payBtn) payBtn.focus();
        }, 80);
    }

    function closeModal() {
        if (!modal) return;
        modal.classList.add('hidden');
        modal.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('nb-plan-modal-open');
        if (upgradeBtn) upgradeBtn.focus();
    }

    async function confirmarPago() {
        if (!payBtn) return;
        payBtn.disabled = true;
        var label = payBtn.innerHTML;
        payBtn.innerHTML =
            '<span class="material-symbols-outlined text-[18px] animate-spin" aria-hidden="true">progress_activity</span> Activando…';
        try {
            var res = await fetch('/api/usuario/plan/mejorar', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
            });
            var data = await res.json().catch(function () {
                return {};
            });
            if (!res.ok || data.ok === false) {
                throw new Error(data.mensaje || 'No se pudo activar el plan.');
            }
            closeModal();
            toast(data.mensaje || 'Plan Pro activado correctamente.');
            var widget = document.getElementById('nb-plan-pro-widget');
            if (widget) renderActivo(widget);
        } catch (err) {
            toast(err.message || 'Error al activar el plan.', true);
            payBtn.disabled = false;
            payBtn.innerHTML = label;
        }
    }

    function bindModal() {
        modal = document.getElementById('nb-plan-modal');
        payBtn = document.getElementById('nb-plan-pay-btn');
        upgradeBtn = document.getElementById('nb-plan-upgrade-btn');
        if (!modal || !upgradeBtn) return;

        upgradeBtn.addEventListener('click', openModal);

        if (payBtn) {
            payBtn.addEventListener('click', confirmarPago);
        }

        modal.querySelectorAll('[data-plan-modal-close]').forEach(function (el) {
            el.addEventListener('click', closeModal);
        });

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && modal && !modal.classList.contains('hidden')) {
                closeModal();
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bindModal);
    } else {
        bindModal();
    }
})();
