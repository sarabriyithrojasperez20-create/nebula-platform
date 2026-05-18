#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migra datos JSON legacy → PostgreSQL.

Uso (desde la raíz del proyecto):
  set DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/nebula
  python scripts/migrate_json_to_postgres.py

Opciones:
  --dry-run   Solo muestra conteos, no escribe
  --force     Borra tablas y reimporta (¡destructivo!)
"""

from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

DATA_DIR = os.path.join(ROOT, "data")

ARCHIVOS_PRINCIPALES = {
    "roles": "roles.json",
    "usuarios": "usuarios.json",
    "cursos": "cursos.json",
    "lecciones": "lecciones.json",
    "progreso": "progreso.json",
    "actividades": "actividades.json",
    "comentarios": "comentarios.json",
    "progreso_catalogo": "progreso_catalogo.json",
    "cursos_asignados": "cursos_asignados.json",
    "diagnosticos_catalogo": "diagnosticos_catalogo.json",
    "resultados_quiz": "resultados_quiz.json",
    "actividad_sistema": "actividad_sistema.json",
}

SATELITE = {
    "racha_diaria": "racha_diaria.json",
    "racha_logs": "racha_logs.json",
    "tutor_sesiones": "tutor_sesiones.json",
    "tutor_uso_diario": "tutor_uso_diario.json",
    "tutor_logs": "tutor_logs.json",
    "notificaciones_admin": "notificaciones_admin.json",
    "recursos_descargas": "recursos_descargas.json",
}


def _leer_json(nombre_archivo: str) -> list:
    ruta = os.path.join(DATA_DIR, nombre_archivo)
    if not os.path.isfile(ruta):
        return []
    with open(ruta, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def _asignar_ids_diagnosticos(registros: list) -> list:
    siguiente = 1
    existentes = {
        int(r["id_diagnostico"])
        for r in registros
        if r.get("id_diagnostico") is not None
    }
    if existentes:
        siguiente = max(existentes) + 1
    out = []
    for reg in registros:
        copia = dict(reg)
        if copia.get("id_diagnostico") is None:
            copia["id_diagnostico"] = siguiente
            siguiente += 1
        out.append(copia)
    return out


def _migrar_sqlite_config(app) -> None:
    import sqlite3

    from nebula_db import DEFAULT_CONFIG, guardar_config

    db_path = os.path.join(DATA_DIR, "nebula.db")
    if not os.path.isfile(db_path):
        guardar_config({})
        return
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    filas = conn.execute("SELECT clave, valor FROM config_sistema").fetchall()
    conn.close()
    cfg = dict(DEFAULT_CONFIG)
    for fila in filas:
        cfg[fila["clave"]] = fila["valor"]
    with app.app_context():
        guardar_config(cfg)


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrar JSON → PostgreSQL (Nébula)")
    parser.add_argument("--dry-run", action="store_true", help="No escribir en BD")
    parser.add_argument("--force", action="store_true", help="Reemplazar todas las colecciones")
    args = parser.parse_args()

    from dotenv import load_dotenv

    load_dotenv(os.path.join(ROOT, ".env"))

    from flask import Flask

    from nebula_data import cargar_datos, guardar_datos, ensure_schema, init_data_layer

    app = Flask(__name__)
    app.secret_key = "migrate-nebula"
    init_data_layer(app)

    orden = [
        "roles",
        "usuarios",
        "cursos",
        "lecciones",
        "progreso",
        "cursos_asignados",
        "progreso_catalogo",
        "diagnosticos_catalogo",
        "resultados_quiz",
        "actividades",
        "comentarios",
        "actividad_sistema",
        "racha_diaria",
        "racha_logs",
        "tutor_sesiones",
        "tutor_uso_diario",
        "tutor_logs",
        "notificaciones_admin",
        "recursos_descargas",
    ]

    fuentes = {**ARCHIVOS_PRINCIPALES, **SATELITE}

    with app.app_context():
        ensure_schema()
        if args.dry_run:
            print("=== DRY RUN ===")
            for nombre in orden:
                archivo = fuentes.get(nombre)
                datos = _leer_json(archivo) if archivo else []
                if nombre == "diagnosticos_catalogo":
                    datos = _asignar_ids_diagnosticos(datos)
                print(f"  {nombre}: {len(datos)} registros desde {archivo}")
            print("Sin cambios en la base de datos.")
            return 0

        for nombre in orden:
            archivo = fuentes[nombre]
            datos = _leer_json(archivo)
            if nombre == "diagnosticos_catalogo":
                datos = _asignar_ids_diagnosticos(datos)
            if args.force or len(cargar_datos(nombre)) == 0:
                guardar_datos(nombre, datos)
                print(f"✓ {nombre}: {len(datos)} registros importados")
            else:
                print(f"⊘ {nombre}: omitido (ya tiene datos; usa --force)")

        _migrar_sqlite_config(app)
        print("✓ config_sistema migrada desde SQLite (si existía)")

    print("\nMigración completada. Reinicia Flask con DATABASE_URL configurado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
