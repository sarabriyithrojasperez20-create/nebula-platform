"""
Servicio de perfil de estudiante — actualización de datos y foto.
"""

from __future__ import annotations

import logging
import os
import re
import uuid
from typing import Any, Optional

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

logger = logging.getLogger("nebula.perfil")

UPLOAD_SUBDIR = os.path.join("uploads", "perfiles")
UPLOAD_ABS_DIR = os.path.join("static", UPLOAD_SUBDIR)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_FOTO_BYTES = 5 * 1024 * 1024

PREFERENCIAS_VALIDAS = ("visual", "auditivo", "kinestesico")


def _email_valido(correo: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", correo))


def _username_valido(username: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9._-]{3,32}$", username))


def _bytes_son_imagen(data: bytes) -> bool:
    if len(data) < 12:
        return False
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return True
    if data[:3] == b"\xff\xd8\xff":
        return True
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return True
    return False


def asegurar_carpeta_fotos() -> None:
    os.makedirs(UPLOAD_ABS_DIR, exist_ok=True)


def url_foto_estatica(foto_perfil: Optional[str]) -> str:
    """Ruta relativa para url_for('static', filename=...)."""
    if not foto_perfil:
        return ""
    if foto_perfil.startswith("http://") or foto_perfil.startswith("https://"):
        return foto_perfil
    return foto_perfil.lstrip("/").replace("static/", "", 1)


AVATAR_ESTUDIANTE_DEFAULT = (
    "https://lh3.googleusercontent.com/aida-public/AB6AXuBlwoGAr4OcQHRwHR-lcqSiVtRczHOqU4jSeFWxNy7vEHCCeSC_b1mKIRSSHlj-Uah3OA6pbCC0gL6OOi-k9lVNngXgPGI8SMaNT5qfa2MvmU_9BDlAs2sFfycz7MTtG1JhdpkytvtTvG0qlm796rX77xURSs3c0qR1vFJfRms9-GFoWgsllXenDXJ4WbdK-n98_bzU82KSmO2gh53b7AdV-AawOUYUnwE3qSGyNOAiyNmiNSUmRB79gyWgUowkW0vRWKOHp2m4EFo"
)


def resolve_avatar_url(
    foto_perfil: Optional[str],
    foto_actualizada_en: Optional[str] = None,
    static_url_builder=None,
    default: str = "",
) -> str:
    """URL absoluta o ruta servible para avatar; default si no hay archivo."""
    if not foto_perfil_existe(foto_perfil):
        return default
    rel = url_foto_estatica(foto_perfil)
    if rel.startswith("http://") or rel.startswith("https://"):
        base = rel
    elif static_url_builder and rel:
        base = static_url_builder(rel)
    else:
        return default
    version = foto_actualizada_en or ""
    if version and base:
        sep = "&" if "?" in base else "?"
        return f"{base}{sep}v={version}"
    return base or default


def foto_perfil_existe(foto_perfil: Optional[str]) -> bool:
    """True si la foto existe en disco o es una URL remota válida."""
    rel = url_foto_estatica(foto_perfil)
    if not rel:
        return False
    if rel.startswith("http://") or rel.startswith("https://"):
        return True
    ruta = os.path.join("static", rel.replace("/", os.sep))
    return os.path.isfile(ruta)


def normalizar_usuario_perfil(usuario: dict) -> dict:
    prefs = usuario.get("preferencias_aprendizaje")
    if not isinstance(prefs, dict):
        prefs = {"dominante": "visual"}
    dominante = prefs.get("dominante", "visual")
    if dominante not in PREFERENCIAS_VALIDAS:
        dominante = "visual"
    foto = usuario.get("foto_perfil") or usuario.get("profile_image") or ""
    return {
        **usuario,
        "foto_perfil": foto,
        "profile_image": foto,
        "sobre_mi": (usuario.get("sobre_mi") or "").strip(),
        "nivel_academico": (usuario.get("nivel_academico") or "").strip(),
        "preferencias_aprendizaje": {**prefs, "dominante": dominante},
    }


def validar_datos_perfil(
    datos: dict,
    id_usuario: int,
    usuarios: list,
) -> tuple[Optional[dict], Optional[str]]:
    nombre = (datos.get("nombre_completo") or "").strip()
    username = (datos.get("username") or "").strip().lower()
    correo = (datos.get("correo") or "").strip().lower()
    sobre_mi = (datos.get("sobre_mi") or "").strip()[:800]
    nivel = (datos.get("nivel_academico") or "").strip()[:120]
    dominante = (datos.get("preferencia_dominante") or "visual").strip().lower()

    if len(nombre) < 2:
        return None, "El nombre completo debe tener al menos 2 caracteres."
    if not _username_valido(username):
        return None, "El usuario solo puede tener letras, números, punto, guion (3-32 caracteres)."
    if not _email_valido(correo):
        return None, "Ingresa un correo electrónico válido."
    if dominante not in PREFERENCIAS_VALIDAS:
        return None, "Selecciona una preferencia de aprendizaje válida."

    for u in usuarios:
        if u.get("id_usuario") == id_usuario:
            continue
        if u.get("username", "").lower() == username:
            return None, "Ese nombre de usuario ya está en uso."
        if u.get("correo", "").lower() == correo:
            return None, "Ese correo ya está registrado."

    return {
        "nombre_completo": nombre,
        "username": username,
        "correo": correo,
        "sobre_mi": sobre_mi,
        "nivel_academico": nivel,
        "preferencias_aprendizaje": {"dominante": dominante},
    }, None


def actualizar_usuario_en_lista(
    usuarios: list,
    id_usuario: int,
    cambios: dict,
) -> Optional[dict]:
    actualizado = None
    for i, u in enumerate(usuarios):
        if u.get("id_usuario") == id_usuario:
            usuarios[i] = {**u, **cambios}
            actualizado = usuarios[i]
            break
    return actualizado


MIME_TO_EXT = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/pjpeg": "jpg",
    "image/png": "png",
    "image/x-png": "png",
    "image/webp": "webp",
}


def _extension_desde_bytes(data: bytes) -> str:
    if len(data) < 12:
        return ""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return ""


def _normalizar_ext(ext: str) -> str:
    ext = (ext or "").lower().strip()
    if ext == "jpeg":
        return "jpg"
    return ext if ext in ALLOWED_EXTENSIONS else ""


def _resolver_extension_archivo(
    filename: Optional[str],
    mimetype: Optional[str],
    data: bytes,
) -> str:
    raw = secure_filename(filename or "")
    if raw and "." in raw:
        ext = _normalizar_ext(raw.rsplit(".", 1)[-1])
        if ext:
            return ext
    mt = (mimetype or "").split(";")[0].strip().lower()
    if mt in MIME_TO_EXT:
        return MIME_TO_EXT[mt]
    return _normalizar_ext(_extension_desde_bytes(data))


def guardar_foto_perfil(
    archivo: FileStorage,
    id_usuario: int,
    foto_anterior: Optional[str] = None,
) -> tuple[Optional[str], Optional[str]]:
    """Guarda imagen y devuelve ruta relativa static (uploads/perfiles/...)."""
    if archivo is None:
        return None, "No se recibió ninguna imagen."

    asegurar_carpeta_fotos()

    try:
        archivo.stream.seek(0)
        data = archivo.read()
    except Exception:
        logger.exception("Error leyendo archivo de foto")
        return None, "Error al leer la imagen."

    if not data:
        return None, "No se recibió ninguna imagen."

    if len(data) > MAX_FOTO_BYTES:
        return None, "La imagen supera el tamaño permitido (máx. 5 MB)."

    if not _bytes_son_imagen(data):
        return None, "Formato no permitido. Usa JPG, PNG o WEBP."

    ext = _resolver_extension_archivo(archivo.filename, archivo.mimetype, data)
    if not ext:
        return None, "Formato no permitido. Usa JPG, PNG o WEBP."

    nombre_final = f"user_{id_usuario}_{uuid.uuid4().hex[:12]}.{ext}"
    ruta_abs = os.path.join(UPLOAD_ABS_DIR, nombre_final)

    try:
        with open(ruta_abs, "wb") as f:
            f.write(data)
    except OSError:
        logger.exception("Error guardando foto de perfil en disco")
        return None, "Error al subir la imagen. Verifica permisos de la carpeta uploads."

    if foto_anterior:
        _eliminar_foto_antigua(foto_anterior)

    ruta_rel = os.path.join(UPLOAD_SUBDIR, nombre_final).replace("\\", "/")
    return ruta_rel, None


def marca_foto_actualizada(cambios: dict) -> dict:
    from datetime import datetime

    now = datetime.now()
    cambios = dict(cambios)
    cambios["foto_actualizada_en"] = now.strftime("%Y%m%d%H%M%S")
    cambios["updated_at"] = now.strftime("%Y-%m-%d %H:%M:%S")
    if cambios.get("foto_perfil"):
        cambios["profile_image"] = cambios["foto_perfil"]
    return cambios


def eliminar_foto_perfil_usuario(
    usuarios: list,
    id_usuario: int,
) -> tuple[Optional[dict], Optional[str]]:
    """Quita la foto del usuario y borra el archivo en disco."""
    usuario = None
    for u in usuarios:
        if u.get("id_usuario") == id_usuario:
            usuario = u
            break
    if not usuario:
        return None, "Usuario no encontrado."
    anterior = usuario.get("foto_perfil") or usuario.get("profile_image")
    if anterior:
        _eliminar_foto_antigua(anterior)
    from datetime import datetime

    cambios = {
        "foto_perfil": "",
        "profile_image": "",
        "foto_actualizada_en": datetime.now().strftime("%Y%m%d%H%M%S"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return actualizar_usuario_en_lista(usuarios, id_usuario, cambios), None


def _eliminar_foto_antigua(foto_perfil: str) -> None:
    if not foto_perfil or foto_perfil.startswith("http"):
        return
    rel = url_foto_estatica(foto_perfil)
    if not rel.startswith("uploads/perfiles/"):
        return
    ruta = os.path.join("static", rel)
    try:
        if os.path.isfile(ruta):
            os.remove(ruta)
    except OSError:
        logger.warning("No se pudo eliminar foto anterior: %s", ruta)
