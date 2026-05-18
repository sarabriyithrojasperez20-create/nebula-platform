#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ejecuta la migración completa con mensajes detallados por colección."""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from dotenv import load_dotenv

load_dotenv(os.path.join(ROOT, ".env"))

from flask import Flask

from db import RENDER_DATABASE_DEFAULT, apply_sqlalchemy_config, describe_database_target
from migrate_json_to_postgres import ejecutar_importacion
from nebula_data import bootstrap_postgres

if __name__ == "__main__":
    app = Flask(__name__)
    uri = apply_sqlalchemy_config(app, default_url=RENDER_DATABASE_DEFAULT)
    print("Destino:", describe_database_target(uri))
    bootstrap_postgres(app)
    raise SystemExit(ejecutar_importacion(app, force=True))
