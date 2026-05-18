# -*- coding: utf-8 -*-
"""
Capa de datos Nébula — PostgreSQL vía SQLAlchemy.

Expone cargar_datos / guardar_datos con la misma API que los JSON,
para compatibilidad total con app.py y servicios existentes.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Type

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError

from db import get_db, init_database
from extensions import db
from models import (
    Activity,
    AdminNotification,
    CatalogProgress,
    Comment,
    CourseAssignment,
    DiagnosticRecord,
    LegacyCourse,
    LegacyLesson,
    LegacyProgress,
    QuizResult,
    ResourceDownload,
    Role,
    StreakLog,
    StreakRecord,
    SystemActivity,
    TutorDailyUsage,
    TutorLog,
    TutorSession,
    User,
)

logger = logging.getLogger("nebula.data")

_WRITE_LOCK = threading.RLock()

# Colecciones principales (ARCHIVOS en app.py)
COLLECTION_MODELS: dict[str, tuple[Type, Callable[[Any], dict]]] = {
    "roles": (Role, lambda m: m.to_dict()),
    "usuarios": (User, lambda m: m.to_dict()),
    "cursos": (LegacyCourse, lambda m: m.to_dict()),
    "lecciones": (LegacyLesson, lambda m: m.to_dict()),
    "progreso": (LegacyProgress, lambda m: m.to_dict()),
    "actividades": (Activity, lambda m: m.to_dict()),
    "comentarios": (Comment, lambda m: m.to_dict()),
    "progreso_catalogo": (CatalogProgress, lambda m: m.to_dict()),
    "cursos_asignados": (CourseAssignment, lambda m: m.to_dict()),
    "diagnosticos_catalogo": (DiagnosticRecord, lambda m: m.to_dict()),
    "resultados_quiz": (QuizResult, lambda m: m.to_dict()),
    "actividad_sistema": (SystemActivity, lambda m: m.to_dict()),
}

# Colecciones satélite (antes en JSON independientes)
SATELLITE_COLLECTIONS: dict[str, tuple[Type, Callable[[Any], dict]]] = {
    "racha_diaria": (StreakRecord, lambda m: m.to_dict()),
    "racha_logs": (StreakLog, lambda m: m.to_dict()),
    "tutor_sesiones": (TutorSession, lambda m: m.to_dict()),
    "tutor_uso_diario": (TutorDailyUsage, lambda m: m.to_dict()),
    "tutor_logs": (TutorLog, lambda m: m.to_dict()),
    "notificaciones_admin": (AdminNotification, lambda m: m.to_dict()),
    "recursos_descargas": (ResourceDownload, lambda m: m.to_dict()),
}

_FROM_DICT = {
    Role: Role.from_dict,
    User: User.from_dict,
    LegacyCourse: LegacyCourse.from_dict,
    LegacyLesson: LegacyLesson.from_dict,
    LegacyProgress: LegacyProgress.from_dict,
    Activity: Activity.from_dict,
    Comment: Comment.from_dict,
    CatalogProgress: CatalogProgress.from_dict,
    CourseAssignment: CourseAssignment.from_dict,
    DiagnosticRecord: DiagnosticRecord.from_dict,
    QuizResult: QuizResult.from_dict,
    SystemActivity: SystemActivity.from_dict,
    StreakRecord: StreakRecord.from_dict,
    StreakLog: StreakLog.from_dict,
    TutorSession: TutorSession.from_dict,
    TutorDailyUsage: TutorDailyUsage.from_dict,
    TutorLog: TutorLog.from_dict,
    AdminNotification: AdminNotification.from_dict,
    ResourceDownload: ResourceDownload.from_dict,
}


def _resolve_collection(nombre: str) -> tuple[Type, Callable]:
    if nombre in COLLECTION_MODELS:
        model, serializer = COLLECTION_MODELS[nombre]
        return model, serializer
    if nombre in SATELLITE_COLLECTIONS:
        model, serializer = SATELLITE_COLLECTIONS[nombre]
        return model, serializer
    raise KeyError(f"Colección desconocida: {nombre}")


def _load_all(model: Type) -> list[dict]:
    session = get_db()
    rows = session.scalars(select(model)).all()
    serializer = None
    for _name, (m, ser) in {**COLLECTION_MODELS, **SATELLITE_COLLECTIONS}.items():
        if m is model:
            serializer = ser
            break
    if serializer is None:
        return [row.to_dict() for row in rows]
    return [serializer(row) for row in rows]


def _replace_all(model: Type, datos: list[dict]) -> None:
    session = get_db()
    factory = _FROM_DICT[model]
    with _WRITE_LOCK:
        session.execute(delete(model))
        for item in datos:
            session.add(factory(item))
        session.commit()


def cargar_datos(nombre: str) -> list:
    """Carga una colección completa (misma firma que app.py legacy)."""
    try:
        model, _ = _resolve_collection(nombre)
        return _load_all(model)
    except SQLAlchemyError as exc:
        logger.exception("Error cargando %s: %s", nombre, exc)
        db.session.rollback()
        raise


def guardar_datos(nombre: str, datos: list) -> None:
    """Reemplaza una colección completa (misma semántica que JSON)."""
    if not isinstance(datos, list):
        raise TypeError("datos debe ser una lista")
    try:
        model, _ = _resolve_collection(nombre)
        _replace_all(model, datos)
    except SQLAlchemyError as exc:
        logger.exception("Error guardando %s: %s", nombre, exc)
        db.session.rollback()
        raise


def cargar_satellite(nombre: str) -> list:
    """Alias explícito para servicios satélite."""
    return cargar_datos(nombre)


def guardar_satellite(nombre: str, datos: list) -> None:
    guardar_datos(nombre, datos)


def generar_id(lista: list, campo_id: str) -> int:
    if len(lista) == 0:
        return 1
    return max(int(item.get(campo_id, 0) or 0) for item in lista) + 1


def init_data_layer(app) -> None:
    """Inicializa PostgreSQL y la capa de persistencia."""
    init_database(app)
    from nebula_db import init_app as init_nebula_db

    init_nebula_db(app)
    logger.info(
        "Capa de datos PostgreSQL configurada. Ejecuta scripts/migrate_json_to_postgres.py "
        "o `flask --app manage.py db upgrade` tras crear el esquema."
    )


def ensure_schema() -> None:
    """Crea tablas si no existen (desarrollo / post-migración)."""
    db.create_all()
