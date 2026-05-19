const NebulApi = {
  async login(email, password) {
    try {
      const response = await fetch('/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          usuario: email,
          password: password
        })
      });

      const data = await response.json();

      return {
        ok: response.ok,
        data: data
      };

    } catch (error) {
      return {
        ok: false,
        data: { error: 'Error de conexión' }
      };
    }
  },

  getToken() {
    return localStorage.getItem('token');
  }
};
// ── Barra de fortaleza de contraseña ──────────────────────
function calcularFortaleza(val) {
  const bar = document.getElementById('strength-bar');
  let score = 0;

  if (val.length >= 6) score++;
  if (val.length >= 10) score++;
  if (/[A-Z]/.test(val)) score++;
  if (/[0-9]/.test(val)) score++;
  if (/[^A-Za-z0-9]/.test(val)) score++;

  const niveles = [
    { w: '0%', bg: 'transparent' },
    { w: '25%', bg: '#ef4444' },
    { w: '50%', bg: '#f97316' },
    { w: '75%', bg: '#eab308' },
    { w: '90%', bg: '#22c55e' },
    { w: '100%', bg: '#16a34a' },
  ];

  const n = niveles[Math.min(score, 5)];
  bar.style.width = n.w;
  bar.style.background = n.bg;
}

// ── Toast ─────────────────────────────────────────────────
function toast(msg, tipo = 'error') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = `show ${tipo}`;

  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.className = '', 3500);
}

// ── Mostrar errores ───────────────────────────────────────
function setFieldError(id, show) {
  const msg = document.getElementById('msg-' + id);
  const input = document.getElementById(id);

  if (msg) msg.classList.toggle('visible', show);
  if (input) input.classList.toggle('border-red-400', show);
}

// ── Validación ────────────────────────────────────────────
function validar() {
  const nombre    = document.getElementById('nombre').value.trim();
  const grado     = document.getElementById('grado').value;
  const email     = document.getElementById('email').value.trim();
  const password  = document.getElementById('password').value;
  const confirmar = document.getElementById('confirmar').value;
  const terms     = document.getElementById('terms').checked;

  let ok = true;

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  setFieldError('nombre', !nombre);
  setFieldError('grado', !grado);
  setFieldError('email', !emailRegex.test(email));
  setFieldError('password', password.length < 6);
  setFieldError('confirmar', password !== confirmar);
  setFieldError('terms', !terms);

  if (!nombre || !grado || !emailRegex.test(email) ||
      password.length < 6 || password !== confirmar || !terms) {
    ok = false;
  }

  return ok;
}

// ── Estado botón ──────────────────────────────────────────
function setLoading(loading) {
  const btn = document.getElementById('btn-registro');
  const spinner = document.getElementById('spinner');
  const texto = document.getElementById('btn-texto');
  const icon = document.getElementById('btn-icon');

  btn.disabled = loading;
  spinner.style.display = loading ? 'block' : 'none';
  texto.textContent = loading ? 'Creando cuenta...' : 'Crear Mi Cuenta';
  icon.style.display = loading ? 'none' : 'inline';
}

// ── Submit ────────────────────────────────────────────────

const formRegistro = document.getElementById('form-registro');
if (formRegistro) {
  formRegistro.addEventListener('submit', (e) => {
    if (!validar()) {
      e.preventDefault();
      alert("Revisa los campos");
    }
  });
}
// ── Limpiar errores en tiempo real ────────────────────────
['nombre','email','password','confirmar'].forEach(id => {
  document.getElementById(id)?.addEventListener('input', () => setFieldError(id, false));
});

document.getElementById('grado')?.addEventListener('change', () => setFieldError('grado', false));
document.getElementById('terms')?.addEventListener('change', () => setFieldError('terms', false));