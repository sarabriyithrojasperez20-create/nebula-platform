# -*- coding: utf-8 -*-
"""Autenticación de usuarios (sin exponer hashes)."""

from __future__ import annotations

from sqlalchemy import func, select

from db import get_db
from models import User
from password_security import upgrade_password_hash_if_legacy, verify_password


def autenticar_por_correo(correo: str, password: str) -> dict | None:
    """
    Valida credenciales contra PostgreSQL.
    Devuelve dict público del usuario (sin password) o None.
    """
    correo_norm = (correo or "").strip().lower()
    if not correo_norm or not password:
        return None

    session = get_db()
    usuario = session.scalar(
        select(User).where(func.lower(User.correo) == correo_norm)
    )
    if usuario is None:
        return None

    if not verify_password(password, usuario.password):
        return None
    if not usuario.activo:
        return None

    upgrade_password_hash_if_legacy(usuario.id_usuario, password, usuario.password)
    return usuario.to_dict()
