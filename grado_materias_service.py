# -*- coding: utf-8 -*-
"""Materias del panel principal según grado académico del estudiante."""

GRADOS_VALIDOS = frozenset({"noveno", "decimo", "once", "universidad"})

GRADO_ETIQUETAS = {
    "noveno": "Noveno",
    "decimo": "Décimo",
    "once": "Once",
    "universidad": "Universidad",
}

MATERIAS_POR_GRADO = {
    "noveno": [
        {"slug": "matematicas-basicas", "titulo": "Matemáticas básicas"},
        {"slug": "ciencias-naturales", "titulo": "Ciencias naturales"},
        {"slug": "espanol", "titulo": "Español"},
        {"slug": "ingles", "titulo": "Inglés"},
        {"slug": "sociales", "titulo": "Sociales"},
        {"slug": "informatica", "titulo": "Informática"},
    ],
    "decimo": [
        {"slug": "algebra", "titulo": "Álgebra"},
        {"slug": "fisica-basica", "titulo": "Física básica"},
        {"slug": "quimica", "titulo": "Química"},
        {"slug": "filosofia", "titulo": "Filosofía"},
        {"slug": "ingles-avanzado", "titulo": "Inglés avanzado"},
        {"slug": "programacion-basica", "titulo": "Programación básica"},
    ],
    "once": [
        {"slug": "calculo-basico", "titulo": "Cálculo básico"},
        {"slug": "fisica-avanzada", "titulo": "Física avanzada"},
        {"slug": "estadistica", "titulo": "Estadística"},
        {"slug": "lectura-critica", "titulo": "Lectura crítica"},
        {"slug": "emprendimiento", "titulo": "Emprendimiento"},
        {"slug": "desarrollo-web", "titulo": "Desarrollo web"},
    ],
    "universidad": [
        {"slug": "programacion", "titulo": "Programación"},
        {"slug": "bases-de-datos", "titulo": "Bases de datos"},
        {"slug": "ingles-profesional", "titulo": "Inglés profesional"},
        {"slug": "comunicacion-academica", "titulo": "Comunicación académica"},
        {"slug": "investigacion", "titulo": "Investigación"},
        {"slug": "gestion-de-proyectos", "titulo": "Gestión de proyectos"},
        {"slug": "inteligencia-artificial", "titulo": "Inteligencia artificial"},
        {"slug": "matematica-aplicada", "titulo": "Matemática aplicada"},
    ],
}

_ALIASES_GRADO = {
    "9": "noveno",
    "9°": "noveno",
    "9 grado": "noveno",
    "noveno": "noveno",
    "9no": "noveno",
    "10": "decimo",
    "10°": "decimo",
    "decimo": "decimo",
    "décimo": "decimo",
    "10mo": "decimo",
    "11": "once",
    "11°": "once",
    "once": "once",
    "11vo": "once",
    "12": "once",
    "12°": "once",
    "doce": "once",
    "universidad": "universidad",
    "uni": "universidad",
    "universitario": "universidad",
}


def normalizar_grado(valor):
    """Clave canónica del grado; por defecto noveno si falta o es desconocido."""
    if valor is None or str(valor).strip() == "":
        return "noveno"
    clave = str(valor).strip().lower()
    if clave in GRADOS_VALIDOS:
        return clave
    return _ALIASES_GRADO.get(clave, "noveno")


def etiqueta_grado(valor):
    """Etiqueta legible para UI y administración."""
    return GRADO_ETIQUETAS.get(normalizar_grado(valor), "Noveno")


def grado_valido_para_registro(valor):
    """True si el valor enviado en el formulario es un grado permitido."""
    if valor is None or str(valor).strip() == "":
        return False
    clave = str(valor).strip().lower()
    if clave in GRADOS_VALIDOS:
        return True
    return clave in ("9", "10", "11", "universidad")


def resolver_grado_registro(valor):
    """Normaliza el grado del formulario de registro."""
    if not grado_valido_para_registro(valor):
        return None
    return normalizar_grado(valor)


def obtener_materias_por_grado(grado):
    return list(MATERIAS_POR_GRADO.get(normalizar_grado(grado), MATERIAS_POR_GRADO["noveno"]))


_ICONO_POR_SLUG = {
    "matematicas-basicas": "calculate",
    "algebra": "functions",
    "calculo-basico": "ssid_chart",
    "programacion": "code",
    "programacion-basica": "terminal",
    "desarrollo-web": "language",
    "fisica-basica": "science",
    "fisica-avanzada": "biotech",
    "quimica": "experiment",
    "ciencias-naturales": "eco",
    "espanol": "menu_book",
    "ingles": "translate",
    "historia": "history_edu",
    "sociales": "public",
    "informatica": "computer",
    "estadistica": "bar_chart",
    "bases-de-datos": "storage",
    "inteligencia-artificial": "psychology",
}

_TEMA_COLORES = ("violet", "indigo", "sky", "emerald", "amber", "rose")


def _metadata_clase(materia: dict, porcentaje: int, indice: int) -> dict:
    slug = materia["slug"]
    if porcentaje >= 70:
        dificultad, estado, badge = "Avanzado", "Dominio sólido", "avanzado"
    elif porcentaje >= 40:
        dificultad, estado, badge = "Intermedio", "En progreso", "proceso"
    elif porcentaje > 0:
        dificultad, estado, badge = "Básico", "Reforzando", "reforzar"
    else:
        dificultad, estado, badge = "Inicio", "Por comenzar", "nuevo"
    restante = max(0, 100 - porcentaje)
    min_est = max(15, int(restante * 0.45))
    return {
        "icono": _ICONO_POR_SLUG.get(slug, "school"),
        "color_theme": _TEMA_COLORES[indice % len(_TEMA_COLORES)],
        "proxima_leccion": "Siguiente módulo · Unidad " + str((porcentaje // 25) + 1),
        "tiempo_restante": f"~{min_est} min restantes",
        "dificultad": dificultad,
        "estado_curso": estado,
        "badge": badge,
        "ia_recomendado": porcentaje < 45,
    }


def clases_activas_desde_materias(usuario):
    """Estructura enriquecida para tarjetas premium del dashboard."""
    if not usuario:
        usuario = {}
    grado = normalizar_grado(usuario.get("grado") or usuario.get("nivel_academico"))
    progreso = usuario.get("progreso_materias") or {}
    clases = []
    for i, materia in enumerate(obtener_materias_por_grado(grado)):
        slug = materia["slug"]
        try:
            porcentaje = int(progreso.get(slug, 0))
        except (TypeError, ValueError):
            porcentaje = 0
        porcentaje = max(0, min(100, porcentaje))
        meta = _metadata_clase(materia, porcentaje, i)
        clases.append(
            {
                "titulo": materia["titulo"],
                "slug": slug,
                "porcentaje": porcentaje,
                **meta,
            }
        )
    return clases[:6]
