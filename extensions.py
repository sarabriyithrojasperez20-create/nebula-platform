# -*- coding: utf-8 -*-
"""
Extensiones Flask compartidas entre app.py, modelos y servicios.

Se inicializan aquí para evitar importaciones circulares; db.py y manage.py
las enlazan con la aplicación mediante init_app.
"""

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# ORM y migraciones Alembic (flask db migrate / upgrade).
db = SQLAlchemy()
migrate = Migrate()
