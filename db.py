# -*- coding: utf-8 -*-
"""Configuración PostgreSQL, pooling y utilidades de sesión."""

from __future__ import annotations

import os
import sys
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from extensions import db, migrate

# Opcional: URL externa solo por variable de entorno (nunca credenciales en el repo)
RENDER_DATABASE_DEFAULT = (os.getenv("RENDER_DATABASE_URL") or "").strip()


def normalize_database_url(url: str) -> str:
    """Normaliza URLs de Render/Heroku para psycopg2 + SQLAlchemy."""
    url = (url or "").strip()
    if not url:
        return url
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://") and "+psycopg2" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def _ensure_env_loaded() -> None:
    try:
        from dotenv import load_dotenv
        from nebula_config import ENV_PATH

        load_dotenv(ENV_PATH, override=False)
        load_dotenv(override=False)
    except ImportError:
        pass


def _default_sqlite_url() -> str:
    """SQLite local en instance/ — desarrollo sin PostgreSQL."""
    from pathlib import Path

    root = Path(__file__).resolve().parent
    instance = root / "instance"
    instance.mkdir(parents=True, exist_ok=True)
    db_path = instance / "nebula.db"
    # Forma absoluta compatible con Windows (sqlite:///C:/...)
    return f"sqlite:///{db_path.resolve().as_posix()}"


def is_sqlite_url(url: str) -> bool:
    return (url or "").strip().lower().startswith("sqlite:")


def resolve_database_url(default_url: str | None = None) -> str:
    """
    Orden de prioridad:
    1. Variable de entorno DATABASE_URL (si no está vacía)
    2. default_url (p. ej. Render en app.py)
    3. POSTGRES_* solo si POSTGRES_HOST está definido explícitamente
    4. SQLite en instance/nebula.db (desarrollo local, salvo NEBULA_DISABLE_SQLITE_FALLBACK=1)
    """
    _ensure_env_loaded()

    env_url = (os.getenv("DATABASE_URL") or "").strip()
    if env_url:
        if is_sqlite_url(env_url):
            return env_url
        return normalize_database_url(env_url)

    fallback = (default_url or RENDER_DATABASE_DEFAULT or "").strip()
    if fallback:
        return normalize_database_url(fallback)

    host = (os.getenv("POSTGRES_HOST") or "").strip()
    if host:
        user = os.getenv("POSTGRES_USER", "nebula")
        password = os.getenv("POSTGRES_PASSWORD", "nebula")
        port = os.getenv("POSTGRES_PORT", "5432")
        name = os.getenv("POSTGRES_DB", "nebula")
        built = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"
        return normalize_database_url(built)

    if os.getenv("NEBULA_DISABLE_SQLITE_FALLBACK", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        return ""

    return _default_sqlite_url()


def describe_database_target(url: str) -> dict[str, str]:
    """Resumen legible de la URI (sin contraseña)."""
    if not url:
        return {"host": "?", "port": "?", "database": "?", "user": "?"}
    parsed = urlparse(url.replace("postgresql+psycopg2", "postgresql"))
    return {
        "host": parsed.hostname or "?",
        "port": str(parsed.port or 5432),
        "database": (parsed.path or "/").lstrip("/") or "?",
        "user": parsed.username or "?",
    }


def apply_sqlalchemy_config(app, default_url: str | None = None) -> str:
    """Asigna SQLALCHEMY_* en Flask a partir de DATABASE_URL / fallback."""
    url = resolve_database_url(default_url=default_url)
    if not url:
        raise ValueError(
            "No hay URL de base de datos. Define DATABASE_URL en .env, usa Render "
            "(RENDER_DATABASE_URL) o deja el fallback SQLite en instance/nebula.db."
        )
    app.config["SQLALCHEMY_DATABASE_URI"] = url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    return url


def database_url() -> str:
    """Compatibilidad con código que llama database_url() directamente."""
    return resolve_database_url()


def configure_app(app) -> None:
    try:
        from dotenv import load_dotenv
        from nebula_config import ENV_PATH

        load_dotenv(ENV_PATH)
    except ImportError:
        pass

    current = (app.config.get("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not current:
        app.config["SQLALCHEMY_DATABASE_URI"] = resolve_database_url()
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)
    engine_opts: dict = {
        "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
        "pool_pre_ping": True,
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "300")),
    }
    uri = (app.config.get("SQLALCHEMY_DATABASE_URI") or "").lower()
    if is_sqlite_url(uri):
        engine_opts["connect_args"] = {"check_same_thread": False}
    elif "render.com" in uri or os.getenv("DB_SSLMODE", "").strip() == "require":
        engine_opts["connect_args"] = {"sslmode": "require"}
    app.config.setdefault("SQLALCHEMY_ENGINE_OPTIONS", engine_opts)


def init_database(app) -> None:
    """Inicializa SQLAlchemy, Migrate y registra teardown de sesión."""
    configure_app(app)
    db.init_app(app)
    migrate.init_app(app, db)

    import models  # noqa: F401 — registra metadatos

    @app.teardown_appcontext
    def _remove_session(_exc=None):
        db.session.remove()


def get_db():
    """Sesión ORM del request actual (scoped por Flask-SQLAlchemy)."""
    return db.session


def verify_database_connection(app) -> None:
    """Prueba la conexión al arranque (falla rápido si el servidor no responde)."""
    with app.app_context():
        db.session.execute(text("SELECT 1"))
        db.session.commit()


def _is_missing_schema_error(exc: BaseException) -> bool:
    texto = str(exc).lower()
    return "does not exist" in texto or "undefinedtable" in texto or "no existe la relación" in texto


def report_database_startup_error(app, exc: BaseException) -> None:
    """Mensaje claro en terminal sin traceback completo."""
    uri = (app.config.get("SQLALCHEMY_DATABASE_URI") or "").strip()
    target = describe_database_target(uri)
    host = target["host"]
    falta_esquema = _is_missing_schema_error(exc)
    sqlite = is_sqlite_url(uri)

    if sqlite:
        titulo = (
            "ERROR — Faltan tablas en SQLite (Nébula)"
            if falta_esquema
            else "ERROR — No se pudo usar SQLite (Nébula)"
        )
    else:
        titulo = (
            "ERROR — Faltan tablas en PostgreSQL (Nébula)"
            if falta_esquema
            else "ERROR — No se pudo conectar a PostgreSQL (Nébula)"
        )

    lines = [
        "",
        "=" * 62,
        f"  {titulo}",
        "=" * 62,
        f"  Host:     {target['host']}",
        f"  Puerto:   {target['port']}",
        f"  Base:     {target['database']}",
        f"  Usuario:  {target['user']}",
        "-" * 62,
        f"  Detalle:  {exc}",
        "-" * 62,
    ]

    if falta_esquema:
        lines.extend(
            [
                "  La conexión a Render funciona, pero la base está vacía (sin tablas).",
                "",
                "  Ejecuta en esta carpeta del proyecto:",
                "    python scripts/migrate_json_to_postgres.py",
                "",
                "  Eso crea las tablas e importa usuarios/cursos desde data/*.json.",
                "  Luego vuelve a ejecutar: python app.py",
            ]
        )
    elif sqlite:
        lines.extend(
            [
                "  Base SQLite local (instance/nebula.db). Prueba:",
                "    python scripts/migrate_json_to_postgres.py",
                "  o borra instance/nebula.db y reinicia python app.py",
            ]
        )
    elif host in ("localhost", "127.0.0.1", "::1"):
        lines.extend(
            [
                "  Estás apuntando a PostgreSQL LOCAL y no hay servidor escuchando.",
                "",
                "  Opción A — Usar Render (recomendado si no tienes Postgres local):",
                "    1. En .env define DATABASE_URL con la URL externa de Render",
                "       (Dashboard → PostgreSQL → Connect → External Database URL).",
                "    2. Comenta o borra cualquier DATABASE_URL=@localhost:5432",
                "",
                "  Opción B — PostgreSQL en esta PC (Windows):",
                "    1. Servicios de Windows (Win+R → services.msc)",
                "    2. Busca «postgresql» y pon el servicio en Iniciado",
                "    3. O en PowerShell (admin):",
                "       Get-Service *postgres*",
                "       Start-Service postgresql-x64-16   # ajusta el nombre",
                "    4. Verifica puerto: netstat -an | findstr 5432",
                "    5. Prueba: psql -h localhost -U nebula -d nebula",
            ]
        )
    else:
        lines.extend(
            [
                "  Estás usando un host remoto (p. ej. Render). Comprueba:",
                "  · DATABASE_URL correcta en .env (sin espacios ni comillas extra)",
                "  · Internet activo y firewall que permita salida al puerto 5432",
                "  · En Render: base de datos en estado «Available»",
            ]
        )

    lines.append("=" * 62)
    print("\n".join(lines), file=sys.stderr)


def is_local_database_host(app) -> bool:
    uri = (app.config.get("SQLALCHEMY_DATABASE_URI") or "").strip()
    return describe_database_target(uri)["host"] in ("localhost", "127.0.0.1", "::1")
