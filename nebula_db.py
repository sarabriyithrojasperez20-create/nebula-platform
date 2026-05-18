# -*- coding: utf-8 -*-
"""Configuración del sistema y snapshots de analytics — PostgreSQL."""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from db import database_url, get_db
from extensions import db
from models import StatisticsSnapshot, SystemConfig

logger = logging.getLogger("nebula.db")

SYNC_MIN_INTERVAL_SEC = 20

DEFAULT_CONFIG: dict[str, str] = {
    "nombre_plataforma": "Nébula",
    "modo_mantenimiento": "0",
    "correo_smtp_host": "",
    "correo_smtp_puerto": "587",
    "correo_remitente": "noreply@nebula.com",
    "correo_smtp_usuario": "",
    "seguridad_mfa_obligatorio": "0",
    "seguridad_bloqueo_intentos": "1",
    "sesiones_simultaneas": "3",
}

METRICAS_SYNC_KEYS = frozenset(
    {
        "total_usuarios",
        "total_estudiantes",
        "usuarios_activos",
        "cursos_activos",
        "cursos_completados",
        "lecciones_completadas",
        "total_evaluaciones",
        "progreso_general",
        "tasa_finalizacion",
        "rachas_activas",
        "rendimiento_promedio",
    }
)

_config_lock = threading.Lock()
_config_ready = False
_sync_lock = threading.Lock()
_last_sync_at = 0.0
_last_sync_hash = ""


def _ahora_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_default_config() -> None:
    global _config_ready
    if _config_ready:
        return
    with _config_lock:
        if _config_ready:
            return
        session = get_db()
        ahora = _ahora_iso()
        for clave, valor in DEFAULT_CONFIG.items():
            existe = session.get(SystemConfig, clave)
            if existe is None:
                session.add(SystemConfig(clave=clave, valor=valor, actualizado_en=ahora))
        try:
            session.commit()
            _config_ready = True
            logger.info("Configuración del sistema inicializada en PostgreSQL")
        except SQLAlchemyError:
            session.rollback()
            raise


def init_app(app) -> None:
    """Semillas de config_sistema (PostgreSQL ya inicializado por nebula_data)."""
    with app.app_context():
        _ensure_default_config()


def _filtrar_metricas_sync(metricas: dict[str, Any]) -> dict[str, int]:
    resultado: dict[str, int] = {}
    for clave in METRICAS_SYNC_KEYS:
        if clave not in metricas:
            continue
        try:
            resultado[clave] = int(metricas[clave])
        except (TypeError, ValueError):
            continue
    return resultado


def _debe_sincronizar(metricas_filtradas: dict[str, int]) -> bool:
    if not metricas_filtradas:
        return False
    payload = json.dumps(metricas_filtradas, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    now = time.monotonic()
    global _last_sync_at, _last_sync_hash
    with _sync_lock:
        if (
            digest == _last_sync_hash
            and (now - _last_sync_at) < SYNC_MIN_INTERVAL_SEC
        ):
            return False
        _last_sync_hash = digest
        _last_sync_at = now
    return True


def sincronizar_estadisticas(metricas: dict[str, Any]) -> None:
    filtradas = _filtrar_metricas_sync(metricas)
    if not _debe_sincronizar(filtradas):
        return

    session = get_db()
    ahora = _ahora_iso()
    try:
        for nombre, valor in filtradas.items():
            session.add(
                StatisticsSnapshot(metrica=nombre, valor=valor, capturado_en=ahora)
            )
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise


def obtener_config() -> dict[str, str]:
    session = get_db()
    cfg = dict(DEFAULT_CONFIG)
    filas = session.scalars(select(SystemConfig)).all()
    for fila in filas:
        cfg[fila.clave] = fila.valor
    return cfg


def guardar_config(actualizaciones: dict[str, Any]) -> dict[str, str]:
    session = get_db()
    ahora = _ahora_iso()
    try:
        for clave, valor in actualizaciones.items():
            fila = session.get(SystemConfig, clave)
            if fila is None:
                session.add(
                    SystemConfig(clave=clave, valor=str(valor), actualizado_en=ahora)
                )
            else:
                fila.valor = str(valor)
                fila.actualizado_en = ahora
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise
    return obtener_config()


def estado_bd() -> dict[str, Any]:
    conectada = False
    tablas = 0
    try:
        with db.engine.connect() as conn:
            conectada = True
            tablas = len(db.metadata.tables)
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.warning("estado_bd: %s", exc)
    url = database_url()
    motor = "PostgreSQL" if "postgresql" in url else "SQL"
    return {
        "conectada": conectada,
        "motor": motor,
        "ruta": url.split("@")[-1] if "@" in url else url,
        "tamaño_kb": 0,
        "tablas": tablas,
        "wal": False,
    }


def obtener_ultimas_estadisticas() -> dict[str, int]:
    session = get_db()
    subq = (
        select(
            StatisticsSnapshot.metrica,
            func.max(StatisticsSnapshot.id).label("max_id"),
        )
        .group_by(StatisticsSnapshot.metrica)
        .subquery()
    )
    filas = session.execute(
        select(StatisticsSnapshot).join(
            subq,
            (StatisticsSnapshot.metrica == subq.c.metrica)
            & (StatisticsSnapshot.id == subq.c.max_id),
        )
    ).scalars()
    return {fila.metrica: int(fila.valor) for fila in filas}
