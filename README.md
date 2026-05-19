# Nébula

Plataforma educativa web con panel de estudiante y administrador: cursos, lecciones, diagnósticos, quizzes, plan de estudios, racha diaria, tutor con IA y gestión de catálogo académico.

## Tecnologías

- **Backend:** Python 3, Flask, SQLAlchemy, Flask-Migrate
- **Base de datos:** SQLite (desarrollo local) o PostgreSQL (producción)
- **Frontend:** Jinja2, HTML, CSS y JavaScript en `templates/` y `static/`
- **IA:** API de OpenAI (tutor, opcional)

## Requisitos previos

- Python 3.10 o superior
- `pip` actualizado
- (Opcional) PostgreSQL si no usas SQLite local

## Instalación

1. Clona el repositorio y entra en la carpeta del proyecto:

```bash
git clone URL_DEL_REPOSITORIO
cd Nebula-4.0
```

2. Crea y activa un entorno virtual (recomendado):

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
```

3. Instala las dependencias:

```bash
pip install -r requirements.txt
```

## Configuración (`.env`)

El archivo **`.env` no se sube a GitHub** por seguridad. Copia la plantilla:

```bash
copy .env.example .env
```

En Windows PowerShell también puedes usar: `Copy-Item .env.example .env`

Variables principales:

| Variable | Descripción |
|----------|-------------|
| `SECRET_KEY` o `FLASK_SECRET_KEY` | Clave secreta de sesión Flask (obligatoria en producción) |
| `DATABASE_URL` | Conexión a BD; por defecto `sqlite:///instance/nebula.db` |
| `OPENAI_API_KEY` | Clave para el tutor IA (opcional en desarrollo) |

Al arrancar por primera vez, si no existe `.env`, la aplicación puede crearlo desde `.env.example`.

## Ejecutar el proyecto

```bash
py app.py
```

(o `python app.py` en Linux/macOS)

Abre en el navegador: **http://127.0.0.1:5000**

## Estructura del proyecto

```
Nebula 4.0/
├── app.py                 # Aplicación Flask principal y rutas
├── db.py                  # Configuración de base de datos y sesión ORM
├── extensions.py          # SQLAlchemy y Flask-Migrate
├── nebula_config.py       # Carga de variables de entorno
├── nebula_data.py         # Capa de datos (usuarios, progreso, etc.)
├── models.py              # Modelos SQLAlchemy
├── *_service.py           # Lógica de negocio (auth, catálogo, racha, tutor…)
├── lecciones_contenido.py # Contenido estático de lecciones
├── quizzes_contenido.py   # Preguntas de evaluación por curso
├── diagnosticos_contenido.py
├── templates/             # Plantillas HTML (Jinja2)
├── static/                # CSS, JS, imágenes y recursos descargables
├── data/                  # JSON de catálogo, diagnósticos y datos auxiliares
├── instance/              # SQLite local (ignorado por git)
├── scripts/               # Utilidades de migración y mantenimiento
├── admin-ui/              # Recursos del panel administrativo (si aplica)
├── requirements.txt
├── .env.example           # Plantilla de variables (sí se versiona)
└── .gitignore
```

### Carpetas principales

- **`templates/`** — Vistas HTML y partials reutilizables (`partials/`).
- **`static/`** — Hojas de estilo, scripts del cliente y subida de avatares (`uploads/perfiles/`).
- **`data/`** — Archivos JSON de configuración y catálogos que complementan la BD.
- **`instance/`** — Base SQLite y datos locales del desarrollador (no se suben al repo).
- **`scripts/`** — Migración JSON→Postgres, reparación de FK, verificación de OpenAI, etc.

## Migraciones de base de datos (opcional)

Con Flask-Migrate:

```bash
flask db upgrade
```

(Define `FLASK_APP=app.py` si tu entorno lo requiere.)

## Subir a GitHub

Desde la raíz del proyecto (sin incluir `.env` ni `instance/*.db` gracias a `.gitignore`):

```bash
git init
git add .
git commit -m "Preparar proyecto Nébula para GitHub"
git branch -M main
git remote add origin URL_DEL_REPOSITORIO
git push -u origin main
```

## Licencia

Consulta con el autor del proyecto si deseas reutilizar o distribuir el código.
