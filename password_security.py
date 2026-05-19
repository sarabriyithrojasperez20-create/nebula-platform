# -*- coding: utf-8 -*-
"""Hash y verificación de contraseñas (Werkzeug scrypt / pbkdf2)."""

from __future__ import annotations

import secrets

from werkzeug.security import check_password_hash, generate_password_hash

# Prefijos de hashes generados por Werkzeug
_HASH_PREFIXES = ("pbkdf2:", "scrypt:", "argon2:")


def is_password_hashed(value: str | None) -> bool:
    if not value:
        return False
    return str(value).startswith(_HASH_PREFIXES)


def hash_password(plain: str) -> str:
    """Genera hash seguro; no volver a hashear si ya es hash."""
    if not plain:
        raise ValueError("La contraseña no puede estar vacía.")
    if is_password_hashed(plain):
        return plain
    return generate_password_hash(plain.strip(), method="scrypt")


def normalize_password_for_storage(value: str | None) -> str:
    """Texto plano → hash; hash existente → sin cambios."""
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if is_password_hashed(text):
        return text
    return hash_password(text)


def verify_password(plain: str, stored: str | None) -> bool:
    """
    Compara contraseña en texto plano con hash almacenado.
    Compatibilidad: si el valor legacy está en texto plano, compara con timing-safe.
    """
    if not plain or not stored:
        return False
    plain = plain.strip()
    stored = str(stored)
    if is_password_hashed(stored):
        return check_password_hash(stored, plain)
    return secrets.compare_digest(plain, stored)


def upgrade_password_hash_if_legacy(id_usuario: int, plain: str, stored: str) -> None:
    """Tras login correcto con contraseña legacy, persiste hash en PostgreSQL."""
    if is_password_hashed(stored):
        return
    from nebula_data import actualizar_campos_usuario

    actualizar_campos_usuario(int(id_usuario), {"password": plain})
