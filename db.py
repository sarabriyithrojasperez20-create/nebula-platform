# -*- coding: utf-8 -*-
"""Configuración PostgreSQL, pooling y utilidades de sesión."""

from __future__ import annotations

import os

from extensions import db, migrate


def database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif url.startswith("postgresql://") and "+psycopg2" not in url:
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url
    user = os.getenv("POSTGRES_USER", "nebula")
    password = os.getenv("POSTGRES_PASSWORD", "nebula")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    name = os.getenv("POSTGRES_DB", "nebula")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"


def configure_app(app) -> None:
    try:
        from dotenv import load_dotenv
        from nebula_config import ENV_PATH

        load_dotenv(ENV_PATH)
    except ImportError:
        pass

    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url()
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)
    app.config.setdefault(
        "SQLALCHEMY_ENGINE_OPTIONS",
        {
            "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
            "pool_pre_ping": True,
            "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "300")),
        },
    )


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
