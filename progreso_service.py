# -*- coding: utf-8 -*-
"""Cálculo dinámico de progreso por curso, materia y dashboard."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from diagnosticos_contenido import obtener_diagnostico_curso
from quizzes_contenido import QUIZ_POR_CURSO


def _cargar():
    from nebula_data import cargar_datos

    return cargar_datos


def _guardar_usuario_progreso_materias(id_usuario: int, progreso_materias: dict) -> None:
    from nebula_data import actualizar_campos_usuario

    actualizar_campos_usuario(id_usuario, {"progreso_materias": progreso_materias})


def curso_tiene_diagnostico(slug: str) -> bool:
    return obtener_diagnostico_curso(slug) is not None


def leccion_tiene_quiz(slug: str, leccion_id: str) -> bool:
    if slug in QUIZ_POR_CURSO:
        return True
    return bool(leccion_id)


def _quizzes_aprobados_por_curso(id_usuario: int, slug: str) -> set[str]:
    registros = _cargar()("resultados_quiz")
    aprobados: set[str] = set()
    for r in registros:
        if (
            r.get("id_usuario") == id_usuario
            and r.get("slug") == slug
            and r.get("aprobado")
        ):
            lid = r.get("leccion_id")
            if lid:
                aprobados.add(str(lid))
    return aprobados


def calcular_progreso_curso(
    curso: dict,
    id_usuario: int,
    *,
    progreso_regs: list | None = None,
    diagnosticos: list | None = None,
    quizzes: list | None = None,
) -> dict[str, Any]:
    """
    Progreso = (completados / total_elementos) * 100
    Elementos: diagnóstico (1) + lecciones + quizzes por lección.
    """
    slug = curso.get("slug", "")
    lecciones = curso.get("lecciones") or []

    if progreso_regs is None:
        progreso_regs = _cargar()("progreso_catalogo")
    if diagnosticos is None:
        diagnosticos = _cargar()("diagnosticos_catalogo")
    if quizzes is None:
        quizzes = _cargar()("resultados_quiz")

    registro = next(
        (
            r
            for r in progreso_regs
            if r.get("id_usuario") == id_usuario and r.get("slug") == slug
        ),
        None,
    )
    lecciones_hechas = set(registro.get("lecciones_completadas", []) if registro else [])
    diag_hecho = any(
        d.get("id_usuario") == id_usuario and d.get("slug") == slug for d in diagnosticos
    )
    quizzes_ok = _quizzes_aprobados_por_curso(id_usuario, slug)

    total = 0
    completados = 0
    detalle: dict[str, Any] = {
        "diagnostico": {"total": 0, "completados": 0},
        "lecciones": {"total": 0, "completados": 0},
        "quizzes": {"total": 0, "completados": 0},
    }

    if curso_tiene_diagnostico(slug):
        detalle["diagnostico"]["total"] = 1
        total += 1
        if diag_hecho:
            detalle["diagnostico"]["completados"] = 1
            completados += 1

    for lec in lecciones:
        lid = lec.get("id")
        if not lid:
            continue
        detalle["lecciones"]["total"] += 1
        total += 1
        if lid in lecciones_hechas or lec.get("estado") == "completado":
            detalle["lecciones"]["completados"] += 1
            completados += 1

        if leccion_tiene_quiz(slug, lid):
            detalle["quizzes"]["total"] += 1
            total += 1
            if lid in quizzes_ok:
                detalle["quizzes"]["completados"] += 1
                completados += 1

    porcentaje = round((completados / total) * 100) if total else 0
    porcentaje = max(0, min(100, porcentaje))

    if porcentaje >= 100:
        estado_texto = "Curso completado"
        estado_curso = "Completado"
    elif porcentaje > 0:
        estado_texto = f"{porcentaje}% completado"
        estado_curso = "Curso en progreso"
    else:
        estado_texto = "Por comenzar"
        estado_curso = "Por comenzar"

    modulos = curso.get("modulos") or []
    modulos_prog = _progreso_por_modulos(lecciones, lecciones_hechas, modulos)

    return {
        "slug": slug,
        "porcentaje": porcentaje,
        "total_elementos": total,
        "elementos_completados": completados,
        "detalle": detalle,
        "estado_texto": estado_texto,
        "estado_curso": estado_curso,
        "diagnostico_completado": diag_hecho,
        "ultima_actividad": (registro or {}).get("fecha_actualizacion") or "",
        "modulos": modulos_prog,
        "completado": porcentaje >= 100,
    }


def _progreso_por_modulos(
    lecciones: list, lecciones_hechas: set, modulos: list
) -> list[dict]:
    if not modulos:
        return []
    n_mod = len(modulos)
    chunk = max(1, (len(lecciones) + n_mod - 1) // n_mod)
    resultado = []
    for i, nombre in enumerate(modulos):
        slice_lec = lecciones[i * chunk : (i + 1) * chunk]
        if not slice_lec:
            resultado.append(
                {"nombre": nombre, "porcentaje": 0, "desbloqueado": i == 0}
            )
            continue
        hechas = sum(1 for l in slice_lec if l.get("id") in lecciones_hechas)
        pct = round((hechas / len(slice_lec)) * 100)
        desbloq = i == 0 or pct > 0 or (
            i > 0 and resultado[i - 1].get("porcentaje", 0) >= 50
        )
        resultado.append(
            {"nombre": nombre, "porcentaje": pct, "desbloqueado": desbloq}
        )
    return resultado


def aplicar_progreso_calculado(curso: dict, id_usuario: int) -> dict:
    """Enriquece el curso con porcentaje y estados de lección."""
    import copy

    curso = copy.deepcopy(curso)
    slug = curso.get("slug", "")

    progreso_regs = _cargar()("progreso_catalogo")
    registro = next(
        (
            r
            for r in progreso_regs
            if r.get("id_usuario") == id_usuario and r.get("slug") == slug
        ),
        None,
    )
    lecciones_hechas = set(registro.get("lecciones_completadas", []) if registro else [])

    for leccion in curso.get("lecciones", []):
        if leccion.get("id") in lecciones_hechas:
            leccion["estado"] = "completado"

    stats = calcular_progreso_curso(curso, id_usuario, progreso_regs=progreso_regs)
    curso["porcentaje"] = stats["porcentaje"]
    curso["progreso_detalle"] = stats["detalle"]
    curso["estado_texto"] = stats["estado_texto"]
    curso["estado_curso"] = stats["estado_curso"]
    curso["modulos_progreso"] = stats["modulos"]
    curso["completado"] = stats["completado"]

    en_progreso = False
    for leccion in curso.get("lecciones", []):
        if leccion.get("estado") == "completado":
            continue
        if leccion.get("bloqueada"):
            continue
        if not en_progreso:
            leccion["estado"] = "en_progreso"
            en_progreso = True
        elif leccion.get("estado") == "en_progreso":
            leccion["estado"] = "pendiente"

    return curso


def sincronizar_progreso_materias_usuario(id_usuario: int) -> dict:
    """Actualiza progreso_materias del usuario desde cursos asignados."""
    from app import obtener_slugs_cursos_asignados, obtener_curso_catalogo

    slugs = obtener_slugs_cursos_asignados(id_usuario)
    por_slug_directo: dict[str, int] = {}

    for slug in slugs:
        base = obtener_curso_catalogo(slug)
        if not base:
            continue
        stats = calcular_progreso_curso(base, id_usuario)
        por_slug_directo[slug] = stats["porcentaje"]

    progreso_materias = {slug: por_slug_directo[slug] for slug in slugs if slug in por_slug_directo}

    _guardar_usuario_progreso_materias(id_usuario, progreso_materias)
    return progreso_materias


def obtener_resumen_progreso_usuario(id_usuario: int) -> dict[str, Any]:
    """Resumen para dashboard, página progreso y APIs."""
    from app import listar_cursos_catalogo_usuario, aplicar_progreso_a_curso

    sincronizar_progreso_materias_usuario(id_usuario)
    cursos = listar_cursos_catalogo_usuario(id_usuario)

    total_lecciones = 0
    lecciones_ok = 0
    cursos_completados = 0
    suma_pct = 0

    cursos_resumen = []
    for c in cursos:
        pct = int(c.get("porcentaje", 0))
        suma_pct += pct
        if pct >= 100:
            cursos_completados += 1
        det = c.get("progreso_detalle") or {}
        total_lecciones += det.get("lecciones", {}).get("total", len(c.get("lecciones", [])))
        lecciones_ok += det.get("lecciones", {}).get("completados", 0)
        cursos_resumen.append(
            {
                "slug": c.get("slug"),
                "titulo": c.get("titulo"),
                "porcentaje": pct,
                "estado_texto": c.get("estado_texto", ""),
                "estado_curso": c.get("estado_curso", ""),
                "completado": pct >= 100,
            }
        )

    n = len(cursos) or 1
    promedio = round(suma_pct / n) if cursos else 0

    tendencia = _tendencia_rendimiento(id_usuario, cursos)

    from grado_materias_service import clases_activas_desde_cursos_asignados

    clases = clases_activas_desde_cursos_asignados(cursos)

    return {
        "promedio_general": promedio,
        "cursos_activos": len(cursos),
        "cursos_completados": cursos_completados,
        "lecciones_completadas": lecciones_ok,
        "total_lecciones": total_lecciones,
        "cursos": cursos_resumen,
        "clases_activas": clases,
        "tendencia": tendencia,
        "actualizado_en": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def _tendencia_rendimiento(id_usuario: int, cursos: list) -> list[dict]:
    """Puntos para gráfico (últimos cursos / promedios por materia)."""
    puntos = []
    for c in cursos[:6]:
        puntos.append(
            {
                "etiqueta": (c.get("titulo") or "")[:14],
                "valor": int(c.get("porcentaje", 0)),
            }
        )
    if not puntos:
        return [{"etiqueta": "—", "valor": 0}]
    return puntos


def persistir_fecha_progreso(id_usuario: int, slug: str) -> None:
    registros = _cargar()("progreso_catalogo")
    reg = next(
        (
            r
            for r in registros
            if r.get("id_usuario") == id_usuario and r.get("slug") == slug
        ),
        None,
    )
    if reg:
        reg["fecha_actualizacion"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        from nebula_data import guardar_datos

        guardar_datos("progreso_catalogo", registros)
