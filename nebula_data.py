# -*- coding: utf-8 -*-
"""
Capa de datos Nébula — PostgreSQL vía SQLAlchemy.

Expone cargar_datos / guardar_datos con la misma API que los JSON,
para compatibilidad total con app.py y servicios existentes.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any, Callable, Type

from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

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
        if nombre == "usuarios":
            try:
                _sync_usuarios(datos)
            except ValueError:
                raise
            return
        model, _ = _resolve_collection(nombre)
        datos = _filtrar_registros_usuario_valido(nombre, datos)
        _replace_all(model, datos, coleccion=nombre)
    except IntegrityError as exc:
        db.session.rollback()
        detalle = getattr(getattr(exc, "orig", None), "diagmessage", None) or str(exc)
        raise ValueError(
            f"No se pudo guardar «{nombre}»: referencia inválida en PostgreSQL. {detalle}"
        ) from exc
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


# Colecciones cuyos registros llevan id_usuario (FK → usuarios)
_COLECCIONES_ID_USUARIO: frozenset[str] = frozenset(
    {
        "cursos_asignados",
        "progreso_catalogo",
        "diagnosticos_catalogo",
        "resultados_quiz",
        "actividad_sistema",
        "racha_diaria",
        "racha_logs",
        "tutor_sesiones",
        "tutor_uso_diario",
    }
)

_ROLES_BASE: tuple[tuple[int, str, str], ...] = (
    (1, "Administrador", "Panel de gestión"),
    (2, "Estudiante", "Aprendizaje y tutor IA"),
)

# Tablas con FK a usuarios — orden de borrado (SQL directo, sin guardar_datos)
_TABLAS_FK_USUARIO_SQL: tuple[tuple[str, str], ...] = (
    ("racha_logs", "id_usuario"),
    ("racha_diaria", "id_usuario"),
    ("tutor_sesiones", "id_usuario"),
    ("tutor_uso_diario", "id_usuario"),
    ("cursos_asignados", "id_usuario"),
    ("progreso_catalogo", "id_usuario"),
    ("diagnosticos_catalogo", "id_usuario"),
    ("resultados_quiz", "id_usuario"),
    ("actividad_sistema", "id_usuario"),
    ("notificaciones_admin", "user_id"),
)

# Tablas legacy con id_usuario dentro de JSONB payload
_TABLAS_PAYLOAD_USUARIO: tuple[str, ...] = (
    "tutor_logs",
    "actividades",
    "comentarios",
    "progreso_legacy",
    "recursos_descargas",
)


def _ids_usuarios_existentes(session=None) -> set[int]:
    session = session or get_db()
    return {int(x) for x in session.scalars(select(User.id_usuario)).all()}


def _filtrar_registros_usuario_valido(coleccion: str, datos: list) -> list:
    """Omite filas con id_usuario inexistente (evita ForeignKeyViolation al importar/guardar)."""
    if coleccion not in _COLECCIONES_ID_USUARIO or not datos:
        return datos
    validos = _ids_usuarios_existentes()
    filtrados: list = []
    omitidos = 0
    for item in datos:
        raw = item.get("id_usuario")
        if raw is None:
            filtrados.append(item)
            continue
        try:
            uid = int(raw)
        except (TypeError, ValueError):
            omitidos += 1
            continue
        if uid in validos:
            filtrados.append(item)
        else:
            omitidos += 1
    if omitidos:
        logger.warning(
            "«%s»: omitidos %d registro(s) con id_usuario inexistente en PostgreSQL",
            coleccion,
            omitidos,
        )
    return filtrados


def _purge_user_fk_references_sqlite(session, uid: int) -> None:
    """Borra filas hijas con FK a usuarios en SQLite (PRAGMA foreign_key_list)."""
    if _db_dialect_name(session) != "sqlite":
        return
    tablas = session.execute(
        text(
            "SELECT DISTINCT m.name AS tabla, p.\"from\" AS columna "
            "FROM sqlite_master m "
            "JOIN pragma_foreign_key_list(m.name) p "
            "WHERE m.type = 'table' AND p.\"table\" = 'usuarios'"
        )
    ).all()
    for tabla, columna in tablas:
        session.execute(
            text(f"DELETE FROM {tabla} WHERE {columna} = :uid"),
            {"uid": uid},
        )
    session.flush()


def _purge_user_fk_references(session, uid: int) -> None:
    """
    Borra filas hijas con FK a usuarios descubriendo restricciones en pg_catalog.
    Funciona aunque ON DELETE CASCADE no esté aplicado en Render.
    """
    dialect = _db_dialect_name(session)
    if dialect == "sqlite":
        _purge_user_fk_references_sqlite(session, uid)
        return
    if dialect != "postgresql":
        return

    filas = session.execute(
        text(
            """
            SELECT quote_ident(t.relname) AS tabla,
                   quote_ident(a.attname) AS columna
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN pg_class ref ON ref.oid = c.confrelid
            JOIN pg_attribute a
              ON a.attrelid = c.conrelid
             AND a.attnum = ANY(c.conkey)
            WHERE c.contype = 'f'
              AND ref.relname = 'usuarios'
              AND array_length(c.conkey, 1) = 1
            """
        )
    ).all()

    for tabla, columna in filas:
        session.execute(
            text(f"DELETE FROM {tabla} WHERE {columna} = :uid"),
            {"uid": uid},
        )
    session.flush()


def _db_dialect_name(session=None) -> str:
    session = session or get_db()
    return (session.get_bind().dialect.name or "").lower()


def _delete_payload_rows_for_user(uid: int, session=None) -> None:
    """Borra filas cuyo payload.id_usuario coincide (sin reemplazar tablas enteras)."""
    session = session or get_db()
    dialect = _db_dialect_name(session)

    if dialect == "postgresql":
        for tabla in _TABLAS_PAYLOAD_USUARIO:
            session.execute(
                text(
                    f'DELETE FROM "{tabla}" '
                    "WHERE (payload->>'id_usuario') ~ '^[0-9]+$' "
                    "AND (payload->>'id_usuario')::int = :uid"
                ),
                {"uid": uid},
            )
        return

    # SQLite y otros: json_extract (evita operadores solo-PostgreSQL ->> y ~)
    for tabla in _TABLAS_PAYLOAD_USUARIO:
        session.execute(
            text(
                f"DELETE FROM {tabla} "
                "WHERE CAST(json_extract(payload, '$.id_usuario') AS INTEGER) = :uid"
            ),
            {"uid": uid},
        )

    # Respaldo ORM por si json_extract no coincide (payload anidado o tipos raros)
    from models import Activity, Comment, LegacyProgress, ResourceDownload, TutorLog

    def _payload_uid(row) -> int | None:
        p = row.payload if isinstance(getattr(row, "payload", None), dict) else {}
        raw = p.get("id_usuario")
        try:
            return int(raw) if raw is not None else None
        except (TypeError, ValueError):
            return None

    for model in (TutorLog, Activity, Comment, LegacyProgress, ResourceDownload):
        for row in session.scalars(select(model)).all():
            if _payload_uid(row) == uid:
                session.delete(row)


_USER_MUTABLE_FIELDS: tuple[str, ...] = (
    "nombre_completo",
    "correo",
    "username",
    "password",
    "id_rol",
    "activo",
    "foto_perfil",
    "foto_actualizada_en",
    "fecha_registro",
    "sobre_mi",
    "nivel_academico",
    "grado",
    "preferencias_aprendizaje",
    "progreso_materias",
)


def _borrar_dependencias_usuario(session, uid: int) -> None:
    """Elimina filas hijas (FK + payload) de un usuario."""
    _purge_user_fk_references(session, uid)

    from models import (
        CatalogProgress,
        CourseAssignment,
        DiagnosticRecord,
        QuizResult,
        StreakLog,
        StreakRecord,
        SystemActivity,
        TutorDailyUsage,
        TutorSession,
    )

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

    session.execute(
        delete(AdminNotification).where(AdminNotification.user_id == uid)
    )
    _delete_payload_rows_for_user(uid, session=session)
    session.flush()


def _merge_user_from_dict(row: User, data: dict) -> None:
    from password_security import normalize_password_for_storage

    for campo in _USER_MUTABLE_FIELDS:
        if campo not in data:
            continue
        valor = data[campo]
        if campo == "password":
            if not valor or not str(valor).strip():
                continue
            setattr(row, campo, normalize_password_for_storage(str(valor)))
            continue
        if campo == "preferencias_aprendizaje" and isinstance(valor, dict):
            prefs = dict(row.preferencias_aprendizaje or {})
            prefs.update(valor)
            row.preferencias_aprendizaje = prefs
            continue
        if hasattr(row, campo):
            setattr(row, campo, valor)


def _sync_usuarios(datos: list[dict]) -> None:
    """
    Sincroniza usuarios sin DELETE masivo de la tabla (evita violación de FK).
    Si falta un id en la lista, delega en eliminar_usuario_completo.
    """
    import models  # noqa: F401

    incoming: dict[int, dict] = {}
    for item in datos:
        incoming[int(item["id_usuario"])] = item

    session = get_db()
    existentes = set(session.scalars(select(User.id_usuario)).all())
    for uid in sorted(existentes - set(incoming.keys())):
        eliminar_usuario_completo(uid)

    with _WRITE_LOCK:
        session = get_db()
        try:
            roles_ok = {int(r) for r in session.scalars(select(Role.id_rol)).all()}
            for rid, nombre, desc in _ROLES_BASE:
                if rid not in roles_ok:
                    session.add(
                        Role(id_rol=rid, nombre_rol=nombre, descripcion=desc)
                    )
                    roles_ok.add(rid)
            session.flush()
            for uid, item in incoming.items():
                id_rol = int(item.get("id_rol", 2))
                if id_rol not in roles_ok:
                    raise ValueError(
                        f"El rol id_rol={id_rol} no existe. "
                        "Ejecuta: python scripts/setup_database.py"
                    )
                row = session.get(User, uid)
                if row is None:
                    session.add(User.from_dict(item))
                else:
                    _merge_user_from_dict(row, item)
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            detalle = getattr(getattr(exc, "orig", None), "diagmessage", None) or str(exc)
            raise ValueError(
                f"No se pudo sincronizar usuarios: {detalle}"
            ) from exc
        except SQLAlchemyError:
            session.rollback()
            raise


def actualizar_campos_usuario(id_usuario: int, cambios: dict) -> dict:
    """Actualiza campos de un usuario sin reemplazar toda la tabla."""
    uid = int(id_usuario)
    session = get_db()
    with _WRITE_LOCK:
        try:
            usuario = session.get(User, uid)
            if usuario is None:
                raise ValueError("Usuario no encontrado.")
            if "password" in cambios:
                from password_security import normalize_password_for_storage

                raw = cambios.pop("password")
                if raw and str(raw).strip():
                    usuario.password = normalize_password_for_storage(str(raw))
            if "plan" in cambios:
                prefs = dict(usuario.preferencias_aprendizaje or {})
                prefs["plan"] = str(cambios.pop("plan")).strip().lower()
                usuario.preferencias_aprendizaje = prefs
            if "preferencias_aprendizaje" in cambios:
                prefs = dict(usuario.preferencias_aprendizaje or {})
                prefs.update(cambios.pop("preferencias_aprendizaje") or {})
                usuario.preferencias_aprendizaje = prefs
            for key, valor in cambios.items():
                if hasattr(usuario, key):
                    setattr(usuario, key, valor)
            session.commit()
            return usuario.to_dict()
        except SQLAlchemyError:
            session.rollback()
            raise


def eliminar_usuario_completo(id_usuario: int) -> None:
    """
    Elimina un usuario y sus datos relacionados.
    Solo DELETE SQL por fila — nunca vaciar la tabla usuarios.
    """
    import models  # noqa: F401

    uid = int(id_usuario)
    session = get_db()

    with _WRITE_LOCK:
        try:
            if session.get(User, uid) is None:
                raise ValueError("Estudiante no encontrado.")

            _borrar_dependencias_usuario(session, uid)

            borrados = session.execute(
                text("DELETE FROM usuarios WHERE id_usuario = :uid"),
                {"uid": uid},
            )
            if borrados.rowcount == 0:
                raise ValueError("Estudiante no encontrado.")

            session.commit()
        except IntegrityError as exc:
            session.rollback()
            detalle = getattr(getattr(exc, "orig", None), "diagmessage", None) or str(exc)
            logger.error("eliminar_usuario_completo IntegrityError uid=%s: %s", uid, detalle)
            raise ValueError(
                "No se pudo eliminar el estudiante: aún hay datos vinculados. "
                f"Detalle: {detalle}"
            ) from exc
        except SQLAlchemyError as exc:
            session.rollback()
            logger.exception("eliminar_usuario_completo SQLAlchemyError uid=%s", uid)
            raise ValueError(
                f"Error de base de datos al eliminar el estudiante: {exc}"
            ) from exc


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


def ensure_postgres_usuario_on_delete_cascade(app) -> int:
    """
    Ajusta FKs hacia usuarios con ON DELETE CASCADE en PostgreSQL existente.
    Idempotente: solo recrea restricciones que aún no tienen CASCADE.
    """
    uri = (app.config.get("SQLALCHEMY_DATABASE_URI") or "").lower()
    if "postgresql" not in uri:
        return 0

    import models  # noqa: F401

    actualizadas = 0
    with app.app_context():
        conn = db.engine.connect()
        trans = conn.begin()
        try:
            for tabla, columna in _TABLAS_FK_USUARIO_SQL:
                fila = conn.execute(
                    text(
                        """
                        SELECT c.conname
                        FROM pg_constraint c
                        JOIN pg_class t ON t.oid = c.conrelid
                        JOIN pg_class ref ON ref.oid = c.confrelid
                        WHERE c.contype = 'f'
                          AND t.relname = :tabla
                          AND ref.relname = 'usuarios'
                          AND pg_get_constraintdef(c.oid) NOT ILIKE '%ON DELETE CASCADE%'
                        LIMIT 1
                        """
                    ),
                    {"tabla": tabla},
                ).first()
                if not fila:
                    continue
                conname = fila[0]
                conn.execute(text(f'ALTER TABLE "{tabla}" DROP CONSTRAINT "{conname}"'))
                conn.execute(
                    text(
                        f'ALTER TABLE "{tabla}" ADD CONSTRAINT "{conname}" '
                        f'FOREIGN KEY ("{columna}") REFERENCES usuarios(id_usuario) '
                        f"ON DELETE CASCADE"
                    )
                )
                actualizadas += 1
            trans.commit()
        except Exception:
            trans.rollback()
            raise
        finally:
            conn.close()

    if actualizadas:
        logger.info("PostgreSQL: %d FK(s) a usuarios con ON DELETE CASCADE", actualizadas)
    return actualizadas


def ensure_roles_seeded(app) -> None:
    """Garantiza roles 1 (admin) y 2 (estudiante) — evita FK al crear usuarios."""
    with app.app_context():
        session = get_db()
        insertados = 0
        for id_rol, nombre, desc in _ROLES_BASE:
            if session.get(Role, id_rol) is None:
                session.add(Role(id_rol=id_rol, nombre_rol=nombre, descripcion=desc))
                insertados += 1
        if insertados:
            session.commit()
            logger.info("Roles base insertados: %d", insertados)


def _maybe_import_json_on_empty_db(app) -> None:
    """Primera ejecución con SQLite: importa data/*.json si no hay usuarios."""
    from db import is_sqlite_url
    from models import User

    uri = app.config.get("SQLALCHEMY_DATABASE_URI") or ""
    if not is_sqlite_url(uri):
        return
    with app.app_context():
        if get_db().query(User).count() > 0:
            return
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    usuarios_json = os.path.join(data_dir, "usuarios.json")
    if not os.path.isfile(usuarios_json):
        logger.warning(
            "Base SQLite vacía y sin data/usuarios.json — ejecuta: "
            "python scripts/migrate_json_to_postgres.py"
        )
        return
    try:
        import importlib.util
        import sys

        if sys.platform == "win32":
            for stream in (sys.stdout, sys.stderr):
                try:
                    stream.reconfigure(encoding="utf-8")
                except Exception:
                    pass

        script_path = os.path.join(
            os.path.dirname(__file__), "scripts", "migrate_json_to_postgres.py"
        )
        spec = importlib.util.spec_from_file_location("migrate_json_to_postgres", script_path)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)

        logger.info("SQLite vacío: importando datos desde data/*.json …")
        mod.ejecutar_importacion(app, dry_run=False, force=False)
        logger.info("Importación JSON completada.")
    except Exception as exc:
        logger.warning(
            "No se pudo importar JSON automáticamente: %s. Ejecuta: "
            "python scripts/migrate_json_to_postgres.py",
            exc,
        )


def bootstrap_postgres(app) -> list[str]:
    """Conexión + creación de tablas (sin semillas de config)."""
    from db import is_sqlite_url, verify_database_connection

    init_database(app)
    verify_database_connection(app)
    tablas = ensure_schema(app)
    ensure_roles_seeded(app)
    _maybe_import_json_on_empty_db(app)
    if not is_sqlite_url(app.config.get("SQLALCHEMY_DATABASE_URI") or ""):
        try:
            ensure_postgres_usuario_on_delete_cascade(app)
        except Exception as exc:
            logger.warning("No se pudo aplicar ON DELETE CASCADE en FK de usuarios: %s", exc)
    if "config_sistema" not in tablas:
        raise RuntimeError(
            "No se pudo crear la tabla config_sistema. "
            "Revisa permisos del usuario en Render o ejecuta: "
            "python scripts/setup_database.py"
        )
    try:
        from catalog_service import ensure_catalog_seeded

        ensure_catalog_seeded(app)
    except Exception as exc:
        logger.warning("Catálogo académico: no se pudo inicializar (%s)", exc)
    return tablas


def plan_de_usuario_dict(usuario: dict | None) -> str:
    """Plan de suscripción (free / pro) a partir del dict de usuario."""
    if not usuario:
        return "free"
    if int(usuario.get("id_rol") or 0) == 1:
        return "pro"
    plan = usuario.get("plan")
    if not plan:
        prefs = usuario.get("preferencias_aprendizaje") or {}
        if isinstance(prefs, dict):
            plan = prefs.get("plan", "free")
    return str(plan or "free").strip().lower() or "free"


def activar_plan_pro_usuario(id_usuario: int) -> dict:
    """Activa Plan Pro para un estudiante (persiste en preferencias_aprendizaje)."""
    uid = int(id_usuario)
    usuario = next(
        (u for u in cargar_datos("usuarios") if int(u.get("id_usuario", 0)) == uid),
        None,
    )
    if not usuario:
        raise ValueError("Usuario no encontrado.")
    if int(usuario.get("id_rol") or 0) != 2:
        raise ValueError("Solo los estudiantes pueden mejorar a Plan Pro.")
    if not usuario.get("activo", True):
        raise ValueError("Tu cuenta está suspendida. Contacta al administrador.")
    if plan_de_usuario_dict(usuario) in ("pro", "premium"):
        return {
            "ok": True,
            "ya_activo": True,
            "plan": plan_de_usuario_dict(usuario),
            "mensaje": "Ya tienes Plan Pro activo.",
        }
    actualizar_campos_usuario(uid, {"plan": "pro"})
    try:
        from notificaciones_admin_service import crear_notificacion_admin

        crear_notificacion_admin(
            "plan_pro",
            f"{usuario.get('nombre_completo', 'Estudiante')} activó Plan Pro",
            titulo="Plan Pro",
            id_usuario=uid,
        )
    except Exception:
        pass
    return {
        "ok": True,
        "ya_activo": False,
        "plan": "pro",
        "mensaje": "Plan Pro activado. Disfruta acceso ampliado al tutor con IA.",
    }


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
        from db import is_sqlite_url

        uri = app.config.get("SQLALCHEMY_DATABASE_URI") or ""
        if is_sqlite_url(uri):
            logger.info(
                "SQLite conectado (%s). Datos en data/*.json se importan al primer arranque.",
                target["database"],
            )
        else:
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
