# -*- coding: utf-8 -*-
"""Extensiones Flask compartidas (SQLAlchemy, Migrate)."""

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()
