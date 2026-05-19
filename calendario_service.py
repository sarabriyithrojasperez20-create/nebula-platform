# -*- coding: utf-8 -*-
"""Eventos académicos del calendario del estudiante (persistencia en actividades)."""

from datetime import date, datetime, timedelta

CATEGORIAS = frozenset({"evaluacion", "tarea", "estudio", "reunion", "clase", "examen", "quiz"})
PRIORIDADES = frozenset({"baja", "media", "alta"})
ESTADOS = frozenset({"pendiente", "en_curso", "completada"})
RECORDATORIOS = frozenset({"ninguno", "15", "60", "1440"})

TIPO_ETIQUETA = {
    "evaluacion": "Examen",
    "examen": "Examen",
    "quiz": "Quiz",
    "tarea": "Tarea",
    "estudio": "Clase",
    "clase": "Clase",
    "reunion": "Reunión",
}

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


def _normalizar_categoria(raw: dict) -> str:
    categoria = (
        raw.get("categoria")
        or raw.get("tipo_evento")
        or raw.get("tipo")
        or "estudio"
    )
    if isinstance(categoria, str):
        categoria = categoria.lower().strip()
    else:
        categoria = "estudio"
    alias = {
        "quiz": "evaluacion",
        "examen": "evaluacion",
        "importante": "evaluacion",
        "tutoria": "clase",
        "clase": "clase",
    }
    categoria = alias.get(categoria, categoria)
    if categoria not in CATEGORIAS:
        categoria = "estudio"
    return categoria


def etiqueta_tipo_evento(categoria: str) -> str:
    return TIPO_ETIQUETA.get((categoria or "").lower(), "Actividad")


def etiqueta_countdown(fecha_str: str, hoy: date | None = None) -> str:
    """Devuelve 'Hoy', 'Mañana' o 'Faltan N días'."""
    if not fecha_str:
        return ""
    try:
        objetivo = datetime.strptime(fecha_str[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return ""
    ref = hoy or date.today()
    delta = (objetivo - ref).days
    if delta < 0:
        return "Pasado"
    if delta == 0:
        return "Hoy"
    if delta == 1:
        return "Mañana"
    return f"Faltan {delta} días"


def normalizar_evento(raw: dict, id_usuario: int) -> dict:
    """Normaliza un evento de calendario para API y plantillas."""
    fecha = (raw.get("fecha") or "")[:10]
    hora = (raw.get("hora") or raw.get("horario") or "").strip()[:5]
    categoria = _normalizar_categoria(raw)
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
    curso_slug = (raw.get("curso_slug") or raw.get("curso_id") or "").strip()
    leccion_id = raw.get("leccion_id")
    if leccion_id is not None:
        leccion_id = str(leccion_id).strip() or None
    curso_titulo = (raw.get("curso_titulo") or "").strip()
    materia = (raw.get("materia") or curso_slug or "").strip()[:80]
    return {
        "id_actividad": raw.get("id_actividad"),
        "id_usuario": id_usuario,
        "tipo": "calendario",
        "titulo": (raw.get("titulo") or "").strip()[:120],
        "materia": materia,
        "curso_slug": curso_slug,
        "leccion_id": leccion_id,
        "curso_titulo": curso_titulo,
        "fecha": fecha,
        "hora": hora,
        "horario": hora,
        "categoria": categoria,
        "tipo_evento": categoria,
        "tipo_label": etiqueta_tipo_evento(categoria),
        "countdown": etiqueta_countdown(fecha),
        "prioridad": prioridad,
        "descripcion": (raw.get("descripcion") or "").strip()[:800],
        "recordatorio": recordatorio,
        "estado": estado,
        "mes": mes,
        "dia": dia,
        "creado_en": raw.get("creado_en") or datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def enriquecer_eventos_con_cursos(eventos: list, cursos_por_slug: dict) -> list:
    """Añade curso_titulo y countdown a cada evento."""
    for ev in eventos:
        slug = ev.get("curso_slug") or ""
        if slug and slug in cursos_por_slug and not ev.get("curso_titulo"):
            ev["curso_titulo"] = cursos_por_slug[slug].get("titulo") or slug
        ev["tipo_label"] = etiqueta_tipo_evento(ev.get("categoria"))
        ev["countdown"] = etiqueta_countdown(ev.get("fecha"))
    return eventos


def validar_evento(payload: dict, slugs_asignados: set | None = None) -> tuple:
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
    curso_slug = (payload.get("curso_slug") or payload.get("materia") or "").strip()
    if slugs_asignados is not None and curso_slug and curso_slug not in slugs_asignados:
        return None, "El curso seleccionado no está asignado a tu cuenta."
    if slugs_asignados is not None and slugs_asignados and not curso_slug:
        return None, "Selecciona un curso para vincular el evento."
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
            ev["tipo_label"] = etiqueta_tipo_evento("evaluacion")
        out.append(ev)
    out.sort(key=lambda e: (e.get("fecha") or "", e.get("hora") or ""))
    return out


def eventos_proximos_evaluaciones(eventos: list, limite: int = 5) -> list:
    hoy = datetime.now().strftime("%Y-%m-%d")
    filtrados = [
        e for e in eventos
        if e.get("categoria") in ("evaluacion", "examen", "quiz")
        and (e.get("fecha") or "") >= hoy
    ]
    if not filtrados:
        filtrados = [e for e in eventos if (e.get("fecha") or "") >= hoy]
    return filtrados[:limite]


def obtener_evento_usuario(actividades: list, id_usuario: int, id_actividad: int) -> dict | None:
    for act in actividades:
        if act.get("id_actividad") == id_actividad and act.get("id_usuario") == id_usuario:
            if act.get("tipo") not in ("calendario", "evaluacion"):
                return None
            return normalizar_evento(act, id_usuario)
    return None


def resolver_destino_curso(
    evento: dict,
    slugs_asignados: set,
    cursos_catalogo: dict,
    resolver_leccion_fn=None,
) -> dict:
    """
    Resuelve URL de destino para un evento vinculado a un curso.
    resolver_leccion_fn(slug) -> leccion_id opcional si no hay en el evento.
    """
    slug = (evento.get("curso_slug") or evento.get("materia") or "").strip()
    if not slug:
        return {
            "ok": True,
            "disponible": False,
            "mensaje": "Curso no disponible",
            "evento": evento,
        }
    if slug not in slugs_asignados or slug not in cursos_catalogo:
        return {
            "ok": True,
            "disponible": False,
            "mensaje": "Curso no disponible",
            "evento": evento,
        }
    curso = cursos_catalogo[slug]
    titulo = evento.get("curso_titulo") or curso.get("titulo") or slug
    leccion_id = evento.get("leccion_id")
    if not leccion_id and resolver_leccion_fn:
        leccion_id = resolver_leccion_fn(slug, curso)
    fragment = ""
    cat = evento.get("categoria") or ""
    if cat == "evaluacion":
        fragment = "#evaluacion"
    elif cat == "tarea":
        fragment = "#tarea"
    params = {}
    if evento.get("id_actividad"):
        params["evento"] = evento["id_actividad"]
    return {
        "ok": True,
        "disponible": True,
        "curso_slug": slug,
        "curso_titulo": titulo,
        "leccion_id": leccion_id,
        "fragment": fragment,
        "query": params,
        "evento": evento,
        "mensaje": None,
    }


def guardar_evento(
    actividades: list,
    id_usuario: int,
    payload: dict,
    generar_id,
    slugs_asignados: set | None = None,
) -> dict:
    datos, err = validar_evento(payload, slugs_asignados)
    if err:
        raise ValueError(err)
    curso_slug = (datos.get("curso_slug") or datos.get("materia") or "").strip()
    if curso_slug:
        datos["curso_slug"] = curso_slug
        datos["materia"] = curso_slug
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
