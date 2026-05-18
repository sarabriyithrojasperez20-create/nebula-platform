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

# JSON legacy sin PK explícito (p. ej. progreso.json) → asignar IDs al guardar
COLLECTION_PK_FIELD: dict[str, str] = {
    "cursos": "id_curso",
    "lecciones": "id_leccion",
    "progreso": "id_progreso",
    "actividades": "id_actividad",
    "comentarios": "id_comentario",
    "actividad_sistema": "id_actividad",
    "diagnosticos_catalogo": "id_diagnostico",
    "recursos_descargas": "id",
    "tutor_logs": "id_log",
    "racha_logs": "id_log",
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


def _ensure_primary_keys(datos: list[dict], campo_id: str) -> list[dict]:
    """Asigna IDs únicos si faltan o hay duplicados (común en JSON legacy)."""
    if not datos:
        return datos
    max_id = 0
    for item in datos:
        raw = item.get(campo_id)
        if raw in (None, "", 0, "0"):
            continue
        try:
            max_id = max(max_id, int(raw))
        except (TypeError, ValueError):
            continue
    siguiente = max(max_id, 0) + 1
    resultado: list[dict] = []
    usados: set[int] = set()
    for item in datos:
        copia = dict(item)
        raw = copia.get(campo_id)
        try:
            pk = int(raw) if raw not in (None, "", 0, "0") else 0
        except (TypeError, ValueError):
            pk = 0
        if pk <= 0 or pk in usados:
            pk = siguiente
            siguiente += 1
        usados.add(pk)
        copia[campo_id] = pk
        resultado.append(copia)
    return resultado


def truncate_all_tables() -> None:
    """Vacía todas las tablas (PostgreSQL). Usar antes de reimportar con --force."""
    import models  # noqa: F401
    from sqlalchemy import text

    nombres = [t.name for t in db.metadata.sorted_tables]
    if not nombres:
        return
    lista = ", ".join(f'"{n}"' for n in nombres)
    session = get_db()
    session.execute(text(f"TRUNCATE {lista} RESTART IDENTITY CASCADE"))
    session.commit()
    logger.info("TRUNCATE CASCADE: %d tablas vaciadas", len(nombres))


def _replace_all(model: Type, datos: list[dict], coleccion: str | None = None) -> None:
    session = get_db()
    factory = _FROM_DICT[model]
    campo_pk = COLLECTION_PK_FIELD.get(coleccion or "")
    if campo_pk:
        datos = _ensure_primary_keys(datos, campo_pk)
    etiqueta = coleccion or getattr(model, "__tablename__", "colección")
    with _WRITE_LOCK:
        try:
            session.execute(delete(model))
            session.flush()
            total = len(datos)
            for indice, item in enumerate(datos):
                try:
                    session.add(factory(item))
                    session.flush()
                except SQLAlchemyError as exc:
                    session.rollback()
                    raise RuntimeError(
                        f"«{etiqueta}» registro {indice + 1}/{total} rechazado por PostgreSQL: {exc}\n"
                        f"  Claves del registro: {list(item.keys())}"
                    ) from exc
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise


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
        _replace_all(model, datos, coleccion=nombre)
    except SQLAlchemyError as exc:
        db.session.rollback()
        raise RuntimeError(
            f"Error al guardar la colección «{nombre}» ({len(datos)} registros): {exc}"
        ) from exc


def cargar_satellite(nombre: str) -> list:
    """Alias explícito para servicios satélite."""
    return cargar_datos(nombre)


def guardar_satellite(nombre: str, datos: list) -> None:
    guardar_datos(nombre, datos)


def generar_id(lista: list, campo_id: str) -> int:
    if len(lista) == 0:
        return 1
    return max(int(item.get(campo_id, 0) or 0) for item in lista) + 1


# Colecciones sin FK directa (datos en JSONB / payload)
_COLECCIONES_PAYLOAD_USUARIO: tuple[tuple[str, str], ...] = (
    ("tutor_logs", "id_usuario"),
    ("actividades", "id_usuario"),
    ("comentarios", "id_usuario"),
    ("progreso", "id_usuario"),
    ("recursos_descargas", "id_usuario"),
)


def _filtrar_coleccion_usuario(nombre: str, id_usuario: int, campo: str = "id_usuario") -> None:
    datos = cargar_datos(nombre)
    if not isinstance(datos, list):
        return
    uid = int(id_usuario)
    restantes = []
    for reg in datos:
        valor = reg.get(campo)
        if valor is None:
            restantes.append(reg)
            continue
        try:
            if int(valor) != uid:
                restantes.append(reg)
        except (TypeError, ValueError):
            restantes.append(reg)
    guardar_datos(nombre, restantes)


def eliminar_usuario_completo(id_usuario: int) -> None:
    """
    Elimina un usuario y sus datos relacionados.
    Primero registros hijos (FK), luego la fila en usuarios.
    """
    from sqlalchemy import delete

    import models  # noqa: F401
    from models import (
        AdminNotification,
        CatalogProgress,
        CourseAssignment,
        DiagnosticRecord,
        QuizResult,
        StreakLog,
        StreakRecord,
        SystemActivity,
        TutorDailyUsage,
        TutorSession,
        User,
    )

    uid = int(id_usuario)
    session = get_db()

    with _WRITE_LOCK:
        try:
            for model in (
                StreakLog,
                StreakRecord,
                TutorSession,
                TutorDailyUsage,
                CourseAssignment,
                CatalogProgress,
                DiagnosticRecord,
                QuizResult,
                SystemActivity,
            ):
                session.execute(delete(model).where(model.id_usuario == uid))

            session.execute(delete(AdminNotification).where(AdminNotification.user_id == uid))

            for nombre, campo in _COLECCIONES_PAYLOAD_USUARIO:
                _filtrar_coleccion_usuario(nombre, uid, campo)

            usuario = session.get(User, uid)
            if usuario is None:
                raise ValueError("Estudiante no encontrado.")
            session.delete(usuario)
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise


def ensure_schema(app) -> list[str]:
    """Crea tablas si no existen (requiere contexto de aplicación Flask)."""
    import models  # noqa: F401

    with app.app_context():
        db.create_all()
        from sqlalchemy import inspect

        tablas = inspect(db.engine).get_table_names()
        logger.info("Esquema PostgreSQL: %d tablas (%s)", len(tablas), ", ".join(tablas[:8]))
        if len(tablas) > 8:
            logger.info("... y %d más", len(tablas) - 8)
        return tablas


def bootstrap_postgres(app) -> list[str]:
    """Conexión + creación de tablas (sin semillas de config)."""
    from db import verify_database_connection

    init_database(app)
    verify_database_connection(app)
    tablas = ensure_schema(app)
    if "config_sistema" not in tablas:
        raise RuntimeError(
            "No se pudo crear la tabla config_sistema. "
            "Revisa permisos del usuario en Render o ejecuta: "
            "python scripts/setup_database.py"
        )
    return tablas


def init_data_layer(app) -> None:
    """Inicializa PostgreSQL y la capa de persistencia."""
    from db import (
        describe_database_target,
        report_database_startup_error,
    )
    from sqlalchemy.exc import OperationalError, ProgrammingError, SQLAlchemyError

    try:
        bootstrap_postgres(app)
        from nebula_db import init_app as init_nebula_db

        init_nebula_db(app)
        target = describe_database_target(app.config.get("SQLALCHEMY_DATABASE_URI", ""))
        logger.info(
            "PostgreSQL conectado (host=%s db=%s). "
            "Si faltan tablas: python scripts/migrate_json_to_postgres.py",
            target["host"],
            target["database"],
        )
    except OperationalError as exc:
        report_database_startup_error(app, exc)
        raise SystemExit(1) from None
    except ProgrammingError as exc:
        report_database_startup_error(app, exc)
        raise SystemExit(1) from None
    except SQLAlchemyError as exc:
        report_database_startup_error(app, exc)
        raise SystemExit(1) from None
    except Exception as exc:
        report_database_startup_error(app, exc)
        raise SystemExit(1) from None
