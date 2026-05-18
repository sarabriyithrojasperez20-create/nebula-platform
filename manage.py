#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI Flask-Migrate: flask db init | migrate | upgrade"""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from app import app  # noqa: F401 — FLASK_APP=manage.py flask db migrate

if __name__ == "__main__":
    app.run()
