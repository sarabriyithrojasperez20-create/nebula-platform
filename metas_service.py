# -*- coding: utf-8 -*-
"""Metas personalizadas del estudiante (persistencia en actividades, tipo meta)."""

from __future__ import annotations

from datetime import datetime

ESTADOS_META = frozenset({"pendiente", "en_progreso", "completada"})


def _normalizar_estado(raw: str) -> str:
    estado = (raw or "pendiente").strip().lower()
    if estado == "completada" or estado == "completado":
        return "completada"
    if estado in ("en_progreso", "en curso", "en_curso"):
        return "en_progreso"
    if estado not in ESTADOS_META:
        return "pendiente"
    return estado


def normalizar_meta(raw: dict, id_usuario: int) -> dict:
    try:
        progreso = int(raw.get("progreso", 0))
    except (TypeError, ValueError):
        progreso = 0
    progreso = max(0, min(100, progreso))
    estado = _normalizar_estado(raw.get("estado"))
    if progreso >= 100:
        estado = "completada"
        progreso = 100
    pk = raw.get("id_actividad")
    return {
        "id": str(pk) if pk is not None else str(raw.get("id", "")),
        "id_actividad": pk,
        "id_usuario": id_usuario,
        "tipo": "meta",
        "titulo": (raw.get("titulo") or "").strip()[:120],
        "descripcion": (raw.get("descripcion") or "").strip()[:800],
        "progreso": progreso,
        "estado": estado,
        "creado_en": raw.get("creado_en") or datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def listar_metas_usuario(actividades: list, id_usuario: int) -> list:
    out = []
    for act in actividades:
        if act.get("id_usuario") != id_usuario:
            continue
        if act.get("tipo") != "meta":
            continue
        out.append(normalizar_meta(act, id_usuario))
    out.sort(key=lambda m: m.get("creado_en") or "")
    return out


def validar_meta(payload: dict) -> tuple[dict | None, str | None]:
    if not payload:
        return None, "Datos incompletos."
    titulo = (payload.get("titulo") or "").strip()
    if len(titulo) < 2:
        return None, "El título debe tener al menos 2 caracteres."
    return payload, None


def guardar_meta(
    actividades: list,
    id_usuario: int,
    payload: dict,
    generar_id,
) -> dict:
    datos, err = validar_meta(payload)
    if err:
        raise ValueError(err)
    meta = normalizar_meta({**datos, "id_usuario": id_usuario}, id_usuario)
    if payload.get("id_actividad"):
        idx = next(
            (
                i
                for i, a in enumerate(actividades)
                if a.get("id_actividad") == payload["id_actividad"]
                and a.get("id_usuario") == id_usuario
                and a.get("tipo") == "meta"
            ),
            None,
        )
        if idx is None:
            raise ValueError("Meta no encontrada.")
        existente = actividades[idx]
        meta["id_actividad"] = existente["id_actividad"]
        meta["creado_en"] = existente.get("creado_en", meta["creado_en"])
        actividades[idx] = meta
    else:
        meta["id_actividad"] = generar_id(actividades, "id_actividad")
        actividades.append(meta)
    return normalizar_meta(meta, id_usuario)


def eliminar_meta(actividades: list, id_usuario: int, id_actividad: int) -> bool:
    for i, act in enumerate(actividades):
        if (
            act.get("id_actividad") == id_actividad
            and act.get("id_usuario") == id_usuario
            and act.get("tipo") == "meta"
        ):
            actividades.pop(i)
            return True
    return False
