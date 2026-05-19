#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convierte contraseñas en texto plano a hash en PostgreSQL.

Uso (desde la raíz del proyecto):
  python scripts/hash_existing_passwords.py

Requiere DATABASE_URL en .env o entorno Render.
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main() -> int:
    from dotenv import load_dotenv
    from flask import Flask
    from sqlalchemy import select

    from db import RENDER_DATABASE_DEFAULT, apply_sqlalchemy_config, get_db, init_database
    from models import User
    from password_security import hash_password, is_password_hashed

    load_dotenv(os.path.join(ROOT, ".env"))
    app = Flask(__name__)
    apply_sqlalchemy_config(app, default_url=RENDER_DATABASE_DEFAULT or None)
    init_database(app)

    actualizados = 0
    omitidos = 0

    with app.app_context():
        from sqlalchemy import text

        session = get_db()
        try:
            session.execute(
                text("ALTER TABLE usuarios ALTER COLUMN password TYPE VARCHAR(512)")
            )
            session.commit()
        except Exception:
            session.rollback()

        usuarios = session.scalars(select(User)).all()
        for u in usuarios:
            if is_password_hashed(u.password):
                omitidos += 1
                continue
            if not u.password:
                print(f"  · id={u.id_usuario} sin contraseña — omitido")
                omitidos += 1
                continue
            u.password = hash_password(u.password)
            actualizados += 1
            print(f"  ✓ id={u.id_usuario} ({u.correo}) → hash aplicado")
        session.commit()

    print(f"\nListo: {actualizados} actualizado(s), {omitidos} ya con hash o vacío(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
