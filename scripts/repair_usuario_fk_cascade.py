#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aplica ON DELETE CASCADE en FKs hacia usuarios (Render / PostgreSQL)."""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main() -> int:
    from dotenv import load_dotenv
    from flask import Flask

    from db import RENDER_DATABASE_DEFAULT, apply_sqlalchemy_config, describe_database_target
    from nebula_data import ensure_postgres_usuario_on_delete_cascade

    load_dotenv(os.path.join(ROOT, ".env"))
    app = Flask(__name__)
    apply_sqlalchemy_config(app, default_url=RENDER_DATABASE_DEFAULT)
    from db import init_database

    init_database(app)
    target = describe_database_target(app.config["SQLALCHEMY_DATABASE_URI"])
    print(f"Conectando a {target['host']} / {target['database']} …")
    n = ensure_postgres_usuario_on_delete_cascade(app)
    print(f"Listo: {n} restricción(es) actualizada(s) con ON DELETE CASCADE.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
