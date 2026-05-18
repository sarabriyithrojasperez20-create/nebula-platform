#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crea todas las tablas en PostgreSQL (Render u otro) e importa datos JSON.

Uso:
  python scripts/setup_database.py
  python scripts/setup_database.py --solo-esquema
"""

from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description="Crear esquema + datos en PostgreSQL")
    parser.add_argument(
        "--solo-esquema",
        action="store_true",
        help="Solo crear tablas, sin importar JSON",
    )
    args = parser.parse_args()

    from dotenv import load_dotenv

    load_dotenv(os.path.join(ROOT, ".env"))

    from flask import Flask

    from db import RENDER_DATABASE_DEFAULT, apply_sqlalchemy_config, describe_database_target
    from nebula_data import bootstrap_postgres

    app = Flask(__name__)
    app.secret_key = "setup-nebula"
    uri = apply_sqlalchemy_config(app, default_url=RENDER_DATABASE_DEFAULT)
    target = describe_database_target(uri)

    print(f"Conectando a {target['host']} / {target['database']} ...")
    tablas = bootstrap_postgres(app)
    print(f"OK — {len(tablas)} tablas creadas.")

    if args.solo_esquema:
        with app.app_context():
            from nebula_db import init_app as init_nebula_db

            init_nebula_db(app)
        print("OK — configuración por defecto (config_sistema).")
        print("\nListo. Ejecuta: python app.py")
        return 0

    print("\nImportando datos JSON (vacía tablas y reimporta todo) ...")
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    from migrate_json_to_postgres import ejecutar_importacion

    return ejecutar_importacion(app, force=True)


if __name__ == "__main__":
    raise SystemExit(main())
