# -*- coding: utf-8 -*-
"""Utilidades de sesión Flask — roles y guards."""

from __future__ import annotations

from flask import redirect, session, url_for


def session_rol() -> int | None:
    """Rol numérico de la sesión (1=admin, 2=estudiante)."""
    raw = session.get("id_rol", session.get("rol"))
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def sync_session_roles(id_rol: int) -> None:
    """Mantiene ``rol`` e ``id_rol`` sincronizados tras un login exitoso."""
    rid = int(id_rol)
    session["rol"] = rid
    session["id_rol"] = rid


def repair_session_role_keys() -> None:
    """Compatibilidad con cookies antiguas que solo tenían rol o id_rol."""
    if "id_usuario" not in session:
        return
    rol = session_rol()
    if rol is None:
        return
    session["rol"] = rol
    session["id_rol"] = rol


def is_admin_session() -> bool:
    return session_rol() == 1


def is_estudiante_session() -> bool:
    return session_rol() == 2


def require_admin_redirect():
    """Redirige si no es administrador; None si OK."""
    repair_session_role_keys()
    if "id_usuario" not in session:
        return redirect(url_for("login"))
    if not is_admin_session():
        return redirect(url_for("dashboard"))
    return None
