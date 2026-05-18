# -*- coding: utf-8 -*-
"""Eventos académicos del calendario del estudiante (persistencia en actividades.json)."""

from datetime import datetime

CATEGORIAS = frozenset({"evaluacion", "tarea", "estudio", "reunion"})
PRIORIDADES = frozenset({"baja", "media", "alta"})
ESTADOS = frozenset({"pendiente", "en_curso", "completada"})
RECORDATORIOS = frozenset({"ninguno", "15", "60", "1440"})

MESES_CORTO = (
    "ENE", "FEB", "MAR", "ABR", "MAY", "JUN",
    "JUL", "AGO", "SEP", "OCT", "NOV", "DIC",
)


def _mes_dia(fecha_str: str) -> tuple:
    try:
        dt = datetime.strptime(fecha_str[:10], "%Y-%m-%d")
        return MESES_CORTO[dt.month - 1], str(dt.day)
    except (ValueError, TypeError):
        return "—", "—"


def normalizar_evento(raw: dict, id_usuario: int) -> dict:
    """Normaliza un evento de calendario para API y plantillas."""
    fecha = (raw.get("fecha") or "")[:10]
    hora = (raw.get("hora") or raw.get("horario") or "").strip()[:5]
    categoria = (raw.get("categoria") or raw.get("tipo_evento") or "estudio").lower()
    if categoria == "quiz":
        categoria = "evaluacion"
    if categoria not in CATEGORIAS:
        categoria = "estudio"
    prioridad = (raw.get("prioridad") or "media").lower()
    if prioridad not in PRIORIDADES:
        prioridad = "media"
    estado = (raw.get("estado") or "pendiente").lower()
    if estado == "en_progreso":
        estado = "en_curso"
    if estado not in ESTADOS:
        estado = "pendiente"
    recordatorio = str(raw.get("recordatorio") or "ninguno").lower()
    if recordatorio not in RECORDATORIOS:
        recordatorio = "ninguno"
    mes, dia = _mes_dia(fecha)
    return {
        "id_actividad": raw.get("id_actividad"),
        "id_usuario": id_usuario,
        "tipo": "calendario",
        "titulo": (raw.get("titulo") or "").strip()[:120],
        "materia": (raw.get("materia") or "").strip()[:80],
        "fecha": fecha,
        "hora": hora,
        "horario": hora,
        "categoria": categoria,
        "prioridad": prioridad,
        "descripcion": (raw.get("descripcion") or "").strip()[:800],
        "recordatorio": recordatorio,
        "estado": estado,
        "mes": mes,
        "dia": dia,
        "creado_en": raw.get("creado_en") or datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def validar_evento(payload: dict) -> tuple:
    if not payload:
        return None, "Datos incompletos."
    titulo = (payload.get("titulo") or "").strip()
    if len(titulo) < 2:
        return None, "El título debe tener al menos 2 caracteres."
    fecha = (payload.get("fecha") or "").strip()
    if not fecha:
        return None, "La fecha es obligatoria."
    try:
        datetime.strptime(fecha[:10], "%Y-%m-%d")
    except ValueError:
        return None, "Fecha inválida."
    return payload, None


def listar_eventos_usuario(actividades: list, id_usuario: int) -> list:
    out = []
    for act in actividades:
        if act.get("id_usuario") != id_usuario:
            continue
        if act.get("tipo") not in ("calendario", "evaluacion"):
            continue
        ev = normalizar_evento(act, id_usuario)
        if act.get("tipo") == "evaluacion":
            ev["categoria"] = "evaluacion"
        out.append(ev)
    out.sort(key=lambda e: (e.get("fecha") or "", e.get("hora") or ""))
    return out


def eventos_proximos_evaluaciones(eventos: list, limite: int = 5) -> list:
    hoy = datetime.now().strftime("%Y-%m-%d")
    filtrados = [
        e for e in eventos
        if e.get("categoria") == "evaluacion" and (e.get("fecha") or "") >= hoy
    ]
    return filtrados[:limite]


def guardar_evento(actividades: list, id_usuario: int, payload: dict, generar_id) -> dict:
    datos, err = validar_evento(payload)
    if err:
        raise ValueError(err)
    evento = normalizar_evento({**datos, "id_usuario": id_usuario}, id_usuario)
    if payload.get("id_actividad"):
        idx = next(
            (
                i for i, a in enumerate(actividades)
                if a.get("id_actividad") == payload["id_actividad"]
                and a.get("id_usuario") == id_usuario
            ),
            None,
        )
        if idx is None:
            raise ValueError("Evento no encontrado.")
        evento["id_actividad"] = payload["id_actividad"]
        evento["creado_en"] = actividades[idx].get("creado_en", evento["creado_en"])
        actividades[idx] = evento
    else:
        evento["id_actividad"] = generar_id(actividades, "id_actividad")
        actividades.append(evento)
    return evento


def eliminar_evento(actividades: list, id_usuario: int, id_actividad: int) -> bool:
    for i, act in enumerate(actividades):
        if act.get("id_actividad") == id_actividad and act.get("id_usuario") == id_usuario:
            actividades.pop(i)
            return True
    return False
