# -*- coding: utf-8 -*-
"""Notificaciones del panel de administrador — persistencia JSON + eventos."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

DATA_FILE = os.path.join("data", "notificaciones_admin.json")
MAX_NOTIFICACIONES = 200

TIPO_META = {
    "registro_estudiante": {"icon": "person_add", "titulo": "Nuevo estudiante"},
    "registro_admin": {"icon": "admin_panel_settings", "titulo": "Nuevo administrador"},
    "foto_perfil": {"icon": "photo_camera", "titulo": "Foto de perfil actualizada"},
    "perfil_completado": {"icon": "badge", "titulo": "Perfil actualizado"},
    "curso_inscrito": {"icon": "bookmark_add", "titulo": "Inscripción a curso"},
    "curso_completado": {"icon": "emoji_events", "titulo": "Curso completado"},
    "evaluacion": {"icon": "assignment_turned_in", "titulo": "Evaluación presentada"},
    "calificacion": {"icon": "grade", "titulo": "Nueva calificación"},
    "curso_creado": {"icon": "add_circle", "titulo": "Curso creado"},
    "leccion_creada": {"icon": "menu_book", "titulo": "Lección creada"},
    "quiz_aprobado": {"icon": "quiz", "titulo": "Quiz aprobado"},
    "quiz_no_aprobado": {"icon": "quiz", "titulo": "Quiz no aprobado"},
    "diagnostico_completado": {"icon": "psychology", "titulo": "Diagnóstico completado"},
    "leccion_completada": {"icon": "check_circle", "titulo": "Lección completada"},
    "registro_usuario": {"icon": "person_add", "titulo": "Nuevo usuario"},
    "curso_anadido": {"icon": "bookmark_add", "titulo": "Curso añadido"},
}

MAPA_ACTIVIDAD_A_NOTIF = {
    "registro_usuario": "registro_estudiante",
    "curso_anadido": "curso_inscrito",
    "diagnostico_completado": "evaluacion",
    "quiz_aprobado": "calificacion",
    "quiz_no_aprobado": "evaluacion",
    "leccion_completada": "leccion_completada",
}


def _nebula():
    import app as nebula_app

    return nebula_app


def _ahora_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _cargar() -> list:
    from nebula_data import cargar_datos

    try:
        data = cargar_datos("notificaciones_admin")
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _guardar(notificaciones: list) -> None:
    from nebula_data import guardar_datos

    guardar_datos("notificaciones_admin", notificaciones[-MAX_NOTIFICACIONES:])


def _siguiente_id(notificaciones: list) -> int:
    if not notificaciones:
        return 1
    return max(int(n.get("id", 0)) for n in notificaciones) + 1


def _avatar_usuario(id_usuario: Optional[int]) -> str:
    if not id_usuario:
        return ""
    try:
        n = _nebula()
        usuario = n.obtener_usuario_por_id(id_usuario)
        if not usuario:
            return ""
        url = n._avatar_url_usuario(usuario)
        return url or n.AVATAR_ESTUDIANTE_DEFAULT
    except Exception:
        return ""


def _nombre_usuario(id_usuario: Optional[int]) -> str:
    if not id_usuario:
        return "Usuario"
    n = _nebula()
    u = n.obtener_usuario_por_id(id_usuario)
    return (u or {}).get("nombre_completo", "Usuario")


def crear_notificacion_admin(
    tipo: str,
    mensaje: str,
    *,
    titulo: Optional[str] = None,
    id_usuario: Optional[int] = None,
    user_name: Optional[str] = None,
    avatar: Optional[str] = None,
    meta: Optional[dict] = None,
) -> dict:
    """Crea una notificación para todos los administradores (bandeja global)."""
    meta_tipo = TIPO_META.get(tipo, {"icon": "notifications", "titulo": "Actividad"})
    notificaciones = _cargar()
    item = {
        "id": _siguiente_id(notificaciones),
        "type": tipo,
        "title": titulo or meta_tipo.get("titulo", "Notificación"),
        "message": mensaje,
        "user_id": id_usuario,
        "user": user_name or _nombre_usuario(id_usuario),
        "avatar": avatar if avatar is not None else _avatar_usuario(id_usuario),
        "icon": meta_tipo.get("icon", "notifications"),
        "created_at": _ahora_iso(),
        "read": False,
        "meta": meta or {},
    }
    notificaciones.insert(0, item)
    _guardar(notificaciones)
    return item


def notificar_desde_actividad_sistema(
    tipo_actividad: str,
    id_usuario: int,
    titulo: str,
    descripcion: str,
) -> Optional[dict]:
    """Puente desde actividad_sistema → notificación admin."""
    tipo_notif = MAPA_ACTIVIDAD_A_NOTIF.get(tipo_actividad, tipo_actividad)
    if tipo_actividad == "registro_usuario":
        n = _nebula()
        u = n.obtener_usuario_por_id(id_usuario)
        if u and u.get("id_rol") == 1:
            tipo_notif = "registro_admin"
        else:
            tipo_notif = "registro_estudiante"
    return crear_notificacion_admin(
        tipo_notif,
        descripcion or titulo,
        titulo=titulo,
        id_usuario=id_usuario,
    )


def listar_notificaciones_admin(
    limite: int = 40,
    solo_no_leidas: bool = False,
    desde_id: Optional[int] = None,
) -> dict:
    notificaciones = _cargar()
    if desde_id:
        notificaciones = [n for n in notificaciones if int(n.get("id", 0)) > desde_id]
    if solo_no_leidas:
        notificaciones = [n for n in notificaciones if not n.get("read")]
    no_leidas = sum(1 for n in _cargar() if not n.get("read"))
    lista = notificaciones[:limite]
    for n in lista:
        n["relativo"] = tiempo_relativo(n.get("created_at", ""))
    return {
        "notificaciones": lista,
        "no_leidas": no_leidas,
        "ultimo_id": max((int(n.get("id", 0)) for n in _cargar()), default=0),
    }


def marcar_leida(id_notificacion: int) -> bool:
    notificaciones = _cargar()
    ok = False
    for n in notificaciones:
        if int(n.get("id")) == id_notificacion:
            n["read"] = True
            ok = True
            break
    if ok:
        _guardar(notificaciones)
    return ok


def marcar_todas_leidas() -> int:
    notificaciones = _cargar()
    count = 0
    for n in notificaciones:
        if not n.get("read"):
            n["read"] = True
            count += 1
    _guardar(notificaciones)
    return count


def tiempo_relativo(iso_str: str) -> str:
    if not iso_str:
        return "ahora"
    try:
        s = iso_str.replace("Z", "").split("+")[0].strip()
        if "T" in s:
            dt = datetime.fromisoformat(s)
        else:
            dt = datetime.strptime(s[:16], "%Y-%m-%d %H:%M")
        diff = int((datetime.now() - dt).total_seconds())
        if diff < 0:
            return "ahora"
        if diff < 60:
            return "hace 1 min" if diff < 45 else f"hace {diff} seg"
        if diff < 3600:
            m = max(1, diff // 60)
            return f"hace {m} min"
        if diff < 86400:
            h = max(1, diff // 3600)
            return f"hace {h} hora" if h == 1 else f"hace {h} horas"
        d = max(1, diff // 86400)
        return f"hace {d} día" if d == 1 else f"hace {d} días"
    except (ValueError, TypeError):
        return iso_str


def sincronizar_desde_actividad_sistema(limite: int = 25) -> int:
    """Importa actividades recientes si la bandeja está vacía (bootstrap)."""
    if _cargar():
        return 0
    n = _nebula()
    actividades = n.cargar_datos("actividad_sistema")
    creadas = 0
    for act in reversed(actividades[-limite:]):
        notificar_desde_actividad_sistema(
            act.get("tipo", "sistema"),
            act.get("id_usuario"),
            act.get("titulo", ""),
            act.get("descripcion", ""),
        )
        creadas += 1
    return creadas
