# -*- coding: utf-8 -*-
"""Agregación de datos reales para el panel de administrador."""

import json
import os
from collections import defaultdict
from datetime import datetime, timedelta

from grado_materias_service import GRADO_ETIQUETAS, etiqueta_grado, normalizar_grado


def _nebula():
    import app as nebula_app

    return nebula_app


def _catalogo():
    n = _nebula()
    return n.CURSOS_CATALOGO, n.ORDEN_CURSOS_CATALOGO, n.MATERIA_POR_SLUG


def cargar_datos(nombre):
    return _nebula().cargar_datos(nombre)


def aplicar_progreso_a_curso(curso, id_usuario):
    return _nebula().aplicar_progreso_a_curso(curso, id_usuario)


def obtener_curso_catalogo(slug):
    return _nebula().obtener_curso_catalogo(slug)


def obtener_leccion_curso(curso, leccion_id):
    return _nebula().obtener_leccion_curso(curso, leccion_id)


def _mapa_usuarios():
    usuarios = cargar_datos("usuarios")
    return {u["id_usuario"]: u for u in usuarios}


def _mapa_roles():
    roles = cargar_datos("roles")
    return {r["id_rol"]: r.get("nombre_rol", "") for r in roles}


def _nombre_usuario(id_usuario, usuarios=None):
    if usuarios is None:
        usuarios = _mapa_usuarios()
    u = usuarios.get(id_usuario, {})
    return u.get("nombre_completo", f"Usuario {id_usuario}")


def contar_lecciones_catalogo():
    CURSOS_CATALOGO, ORDEN_CURSOS_CATALOGO, _ = _catalogo()
    total = 0
    for slug in ORDEN_CURSOS_CATALOGO:
        curso = CURSOS_CATALOGO.get(slug)
        if curso:
            total += len(curso.get("lecciones", []))
    return total


def obtener_asignaciones_por_usuario():
    asignaciones = cargar_datos("cursos_asignados")
    por_usuario = defaultdict(list)
    for item in asignaciones:
        por_usuario[item["id_usuario"]].append(item)
    return por_usuario


def obtener_asignaciones_por_curso():
    asignaciones = cargar_datos("cursos_asignados")
    por_curso = defaultdict(list)
    for item in asignaciones:
        por_curso[item["slug"]].append(item)
    return por_curso


def _intentos_quiz_usuario_leccion(id_usuario, slug, leccion_id, registros=None):
    if registros is None:
        registros = cargar_datos("resultados_quiz")
    return sum(
        1
        for r in registros
        if r.get("id_usuario") == id_usuario
        and r.get("slug") == slug
        and r.get("leccion_id") == leccion_id
    )


def _ultimo_quiz_usuario_leccion(id_usuario, slug, leccion_id, registros=None):
    if registros is None:
        registros = cargar_datos("resultados_quiz")
    filtrados = [
        r
        for r in registros
        if r.get("id_usuario") == id_usuario
        and r.get("slug") == slug
        and r.get("leccion_id") == leccion_id
    ]
    if not filtrados:
        return None
    return max(filtrados, key=lambda x: x.get("fecha", ""))


def obtener_resumen_admin():
    CURSOS_CATALOGO, _, _ = _catalogo()
    usuarios = cargar_datos("usuarios")
    diagnosticos = cargar_datos("diagnosticos_catalogo")
    quizzes = cargar_datos("resultados_quiz")

    return {
        "total_usuarios": len(usuarios),
        "total_cursos": len(CURSOS_CATALOGO),
        "total_lecciones": contar_lecciones_catalogo(),
        "total_evaluaciones": len(diagnosticos) + len(quizzes),
    }


def obtener_distribucion_roles():
    usuarios = cargar_datos("usuarios")
    roles_map = _mapa_roles()
    conteo = defaultdict(int)
    for u in usuarios:
        conteo[u.get("id_rol", 0)] += 1

    total = len(usuarios) or 1
    items = []
    etiquetas_rol = {
        1: "Administradores",
        2: "Estudiantes",
    }
    for id_rol, cantidad in sorted(conteo.items()):
        nombre = etiquetas_rol.get(id_rol) or roles_map.get(id_rol, f"Rol {id_rol}")
        items.append(
            {
                "nombre": nombre,
                "cantidad": cantidad,
                "porcentaje": round((cantidad / total) * 100),
            }
        )
    return {"total": len(usuarios), "por_rol": items}


def obtener_cursos_populares(limite=4):
    CURSOS_CATALOGO, ORDEN_CURSOS_CATALOGO, MATERIA_POR_SLUG = _catalogo()
    por_curso = obtener_asignaciones_por_curso()
    progreso_regs = cargar_datos("progreso_catalogo")
    diagnosticos = cargar_datos("diagnosticos_catalogo")
    filas = []

    for slug in ORDEN_CURSOS_CATALOGO:
        base = CURSOS_CATALOGO.get(slug)
        if not base:
            continue
        estudiantes = por_curso.get(slug, [])
        n_est = len(estudiantes)
        if n_est == 0:
            promedio = 0
        else:
            suma = 0
            for est in estudiantes:
                curso = aplicar_progreso_a_curso(
                    obtener_curso_catalogo(slug), est["id_usuario"]
                )
                suma += curso.get("porcentaje", 0)
            promedio = round(suma / n_est)

        filas.append(
            {
                "slug": slug,
                "titulo": base["titulo"],
                "estudiantes": n_est,
                "progreso_promedio": promedio,
                "materia": MATERIA_POR_SLUG.get(slug, "general"),
            }
        )

    filas.sort(key=lambda x: x["estudiantes"], reverse=True)
    return filas[:limite]


def calcular_rango_periodo(dias: int) -> tuple[str, str, str]:
    """Devuelve (fecha_desde, fecha_hasta, etiqueta) para filtros de analytics."""
    dias = max(1, min(int(dias or 30), 365))
    hasta = datetime.now().date()
    desde = hasta - timedelta(days=dias - 1)
    etiquetas = {7: "Últimos 7 días", 30: "Último mes", 365: "Último año"}
    etiqueta = etiquetas.get(dias, f"Últimos {dias} días")
    return desde.strftime("%Y-%m-%d"), hasta.strftime("%Y-%m-%d"), etiqueta


def calcular_rango_periodo_admin(periodo: str) -> tuple[str, str, str, int]:
    """Rango para el resumen del dashboard admin: 7, 30 o este mes."""
    hoy = datetime.now().date()
    p = (periodo or "30").strip().lower()
    if p in ("mes", "este_mes", "month"):
        desde = hoy.replace(day=1)
        dias = (hoy - desde).days + 1
        return desde.strftime("%Y-%m-%d"), hoy.strftime("%Y-%m-%d"), "Este mes", dias
    if p in ("7", "7d", "semana"):
        dias = 7
    else:
        dias = 30
    desde = hoy - timedelta(days=dias - 1)
    etiqueta = "Últimos 7 días" if dias == 7 else "Últimos 30 días"
    return desde.strftime("%Y-%m-%d"), hoy.strftime("%Y-%m-%d"), etiqueta, dias


def fecha_en_rango(fecha_str: str, fecha_desde: str, fecha_hasta: str) -> bool:
    if not fecha_str:
        return not fecha_desde and not fecha_hasta
    f = (fecha_str or "")[:10]
    if fecha_desde and f < fecha_desde:
        return False
    if fecha_hasta and f > fecha_hasta:
        return False
    return True


def _resumen_usuario(id_usuario, usuarios, roles_map, asignaciones_u, diagnosticos, progreso_regs, quizzes):
    CURSOS_CATALOGO, _, _ = _catalogo()
    usuario = usuarios.get(id_usuario, {})
    cursos_asignados = []
    for asig in asignaciones_u.get(id_usuario, []):
        slug = asig["slug"]
        base = CURSOS_CATALOGO.get(slug)
        if not base:
            continue
        curso = aplicar_progreso_a_curso(obtener_curso_catalogo(slug), id_usuario)
        diag = next(
            (d for d in diagnosticos if d["id_usuario"] == id_usuario and d["slug"] == slug),
            None,
        )
        cursos_asignados.append(
            {
                "slug": slug,
                "titulo": base["titulo"],
                "progreso": curso.get("porcentaje", 0),
                "diagnostico": diag,
            }
        )

    lecciones_completadas = []
    for reg in progreso_regs:
        if reg.get("id_usuario") != id_usuario:
            continue
        slug = reg["slug"]
        base = CURSOS_CATALOGO.get(slug)
        if not base:
            continue
        fecha_leccion = reg.get("fecha_actualizacion", "") or ""
        for lid in reg.get("lecciones_completadas", []):
            lec = obtener_leccion_curso(base, lid)
            lecciones_completadas.append(
                {
                    "curso": base["titulo"],
                    "leccion": lec["titulo"] if lec else lid,
                    "slug": slug,
                    "leccion_id": lid,
                    "fecha": fecha_leccion,
                    "estado": "Completada",
                }
            )

    evaluaciones_usuario = []
    for d in diagnosticos:
        if d.get("id_usuario") == id_usuario:
            evaluaciones_usuario.append(
                {
                    "tipo": "diagnostico",
                    "curso": CURSOS_CATALOGO.get(d["slug"], {}).get("titulo", d["slug"]),
                    "tema": "Quiz diagnóstico",
                    "porcentaje": d.get("porcentaje", 0),
                    "aprobado": None,
                    "nivel": d.get("nivel"),
                    "fecha": d.get("fecha", ""),
                }
            )

    for q in quizzes:
        if q.get("id_usuario") == id_usuario:
            evaluaciones_usuario.append(
                {
                    "tipo": "quiz_final",
                    "curso": q.get("titulo_curso", q.get("slug", "")),
                    "tema": q.get("titulo_leccion", q.get("leccion_id", "")),
                    "porcentaje": q.get("porcentaje", 0),
                    "aprobado": q.get("aprobado", False),
                    "nivel": None,
                    "fecha": q.get("fecha", ""),
                    "intentos": q.get("intento", 1),
                }
            )

    aprobadas = sum(1 for e in evaluaciones_usuario if e.get("aprobado") is True)
    reprobadas = sum(1 for e in evaluaciones_usuario if e.get("aprobado") is False)

    from flask import url_for
    from perfil_service import AVATAR_ESTUDIANTE_DEFAULT, resolve_avatar_url

    avatar_url = resolve_avatar_url(
        usuario.get("foto_perfil"),
        usuario.get("foto_actualizada_en"),
        lambda rel: url_for("static", filename=rel),
        AVATAR_ESTUDIANTE_DEFAULT if usuario.get("id_rol") == 2 else "",
    )

    return {
        "id_usuario": id_usuario,
        "nombre_completo": usuario.get("nombre_completo", ""),
        "correo": usuario.get("correo", ""),
        "username": usuario.get("username", ""),
        "avatar_url": avatar_url,
        "rol": roles_map.get(usuario.get("id_rol"), ""),
        "id_rol": usuario.get("id_rol"),
        "activo": usuario.get("activo", True),
        "fecha_registro": usuario.get("fecha_registro", "—"),
        "grado": etiqueta_grado(usuario.get("grado") or usuario.get("nivel_academico")),
        "cursos_asignados": cursos_asignados,
        "total_cursos": len(cursos_asignados),
        "lecciones_completadas": lecciones_completadas,
        "total_lecciones_completadas": len(lecciones_completadas),
        "diagnosticos": [
            c["diagnostico"]
            for c in cursos_asignados
            if c.get("diagnostico")
        ],
        "evaluaciones": evaluaciones_usuario,
        "quizzes_aprobados": aprobadas,
        "quizzes_no_aprobados": reprobadas,
    }


def obtener_lista_usuarios_admin():
    usuarios_map = _mapa_usuarios()
    roles_map = _mapa_roles()
    asignaciones_u = obtener_asignaciones_por_usuario()
    diagnosticos = cargar_datos("diagnosticos_catalogo")
    progreso_regs = cargar_datos("progreso_catalogo")
    quizzes = cargar_datos("resultados_quiz")

    lista = []
    for id_usuario in sorted(usuarios_map.keys()):
        lista.append(
            _resumen_usuario(
                id_usuario,
                usuarios_map,
                roles_map,
                asignaciones_u,
                diagnosticos,
                progreso_regs,
                quizzes,
            )
        )
    return lista


def obtener_lista_cursos_admin():
    from catalog_service import listar_cursos_admin_db

    CURSOS_CATALOGO, ORDEN_CURSOS_CATALOGO, MATERIA_POR_SLUG = _catalogo()
    por_curso = obtener_asignaciones_por_curso()
    diagnosticos = cargar_datos("diagnosticos_catalogo")
    quizzes = cargar_datos("resultados_quiz")
    progreso_regs = cargar_datos("progreso_catalogo")
    lista = []
    db_cursos = listar_cursos_admin_db()
    slugs_orden = [c["slug"] for c in sorted(db_cursos, key=lambda x: (x.get("orden") or 0, x.get("titulo") or ""))]

    for slug in slugs_orden:
        base = CURSOS_CATALOGO.get(slug)
        db_row = next((c for c in db_cursos if c["slug"] == slug), None)
        if not base and db_row:
            base = {
                "titulo": db_row.get("titulo", slug),
                "nivel": db_row.get("nivel", "—"),
                "lecciones": [],
            }
        if not base:
            continue
        estudiantes = por_curso.get(slug, [])
        n_est = len(estudiantes)
        diag_count = sum(1 for d in diagnosticos if d.get("slug") == slug)
        quiz_count = sum(1 for q in quizzes if q.get("slug") == slug)

        if n_est:
            suma_prog = 0
            aprobados = 0
            evaluaciones_curso = 0
            for est in estudiantes:
                uid = est["id_usuario"]
                curso = aplicar_progreso_a_curso(obtener_curso_catalogo(slug), uid)
                suma_prog += curso.get("porcentaje", 0)
                for q in quizzes:
                    if q.get("slug") == slug and q.get("id_usuario") == uid:
                        evaluaciones_curso += 1
                        if q.get("aprobado"):
                            aprobados += 1
            promedio_prog = round(suma_prog / n_est)
            prom_aprobacion = (
                round((aprobados / quiz_count) * 100) if quiz_count else 0
            )
        else:
            promedio_prog = 0
            prom_aprobacion = 0

        num_lecciones = len(base.get("lecciones", []))
        num_evaluaciones = 0
        if db_row:
            num_lecciones = db_row.get("num_lecciones", num_lecciones)
            num_evaluaciones = db_row.get("num_evaluaciones", 0)

        lista.append(
            {
                "slug": slug,
                "titulo": base["titulo"],
                "categoria": (db_row.get("categoria") if db_row else MATERIA_POR_SLUG.get(slug, "general")).capitalize(),
                "nivel": base.get("nivel", "—"),
                "activo": db_row.get("activo", True) if db_row else True,
                "estudiantes_inscritos": n_est,
                "num_lecciones": num_lecciones,
                "num_evaluaciones": num_evaluaciones,
                "progreso_promedio": promedio_prog,
                "diagnosticos_realizados": diag_count,
                "quizzes_finales": quiz_count,
                "promedio_aprobacion": prom_aprobacion,
                "estudiantes": [
                    {
                        "id_usuario": e["id_usuario"],
                        "nombre": _nombre_usuario(e["id_usuario"]),
                        "fecha_asignacion": e.get("fecha_asignacion", ""),
                        "progreso": aplicar_progreso_a_curso(
                            obtener_curso_catalogo(slug), e["id_usuario"]
                        ).get("porcentaje", 0),
                    }
                    for e in estudiantes
                ],
            }
        )
    return lista


def obtener_lista_lecciones_admin():
    CURSOS_CATALOGO, ORDEN_CURSOS_CATALOGO, _ = _catalogo()
    por_curso = obtener_asignaciones_por_curso()
    progreso_regs = cargar_datos("progreso_catalogo")
    quizzes = cargar_datos("resultados_quiz")
    lista = []

    for slug in ORDEN_CURSOS_CATALOGO:
        base = CURSOS_CATALOGO.get(slug)
        if not base:
            continue
        estudiantes_ids = {e["id_usuario"] for e in por_curso.get(slug, [])}

        for leccion in base.get("lecciones", []):
            lid = leccion["id"]
            iniciaron = set()
            completaron = set()
            porcentajes_quiz = []

            for uid in estudiantes_ids:
                curso_u = aplicar_progreso_a_curso(obtener_curso_catalogo(slug), uid)
                lec_u = obtener_leccion_curso(curso_u, lid)
                if not lec_u:
                    continue
                estado = lec_u.get("estado")
                if estado in ("en_progreso", "completado"):
                    iniciaron.add(uid)
                if estado == "completado":
                    completaron.add(uid)

                ultimo = _ultimo_quiz_usuario_leccion(uid, slug, lid, quizzes)
                if ultimo:
                    iniciaron.add(uid)
                    porcentajes_quiz.append(ultimo.get("porcentaje", 0))

            n_ini = len(iniciaron) or len(completaron)
            n_comp = len(completaron)
            pct_fin = round((n_comp / n_ini) * 100) if n_ini else 0
            prom_aprob = (
                round(sum(porcentajes_quiz) / len(porcentajes_quiz))
                if porcentajes_quiz
                else 0
            )
            aprobados_quiz = sum(1 for p in porcentajes_quiz if p >= 60)

            lista.append(
                {
                    "leccion_id": lid,
                    "titulo": leccion["titulo"],
                    "curso": base["titulo"],
                    "slug": slug,
                    "duracion": leccion.get("duracion", "—"),
                    "estado_catalogo": leccion.get("estado", "pendiente"),
                    "iniciaron": len(iniciaron),
                    "completaron": n_comp,
                    "porcentaje_finalizacion": pct_fin,
                    "promedio_quiz": prom_aprob,
                    "quizzes_realizados": len(porcentajes_quiz),
                    "quizzes_aprobados": aprobados_quiz,
                }
            )
    return lista


def obtener_lista_evaluaciones_admin():
    CURSOS_CATALOGO, _, _ = _catalogo()
    usuarios = _mapa_usuarios()
    diagnosticos = cargar_datos("diagnosticos_catalogo")
    quizzes = cargar_datos("resultados_quiz")
    lista = []

    for d in diagnosticos:
        uid = d.get("id_usuario")
        slug = d.get("slug", "")
        base = CURSOS_CATALOGO.get(slug, {})
        lista.append(
            {
                "id": f"diag-{d.get('id_diagnostico', uid)}",
                "estudiante": _nombre_usuario(uid, usuarios),
                "id_usuario": uid,
                "curso": base.get("titulo", slug),
                "tipo": "diagnostico",
                "tema": "Quiz diagnóstico",
                "puntaje": f"{d.get('correctas', 0)}/{d.get('total', 0)}",
                "porcentaje": d.get("porcentaje", 0),
                "estado": d.get("titulo_nivel") or d.get("nivel", "—"),
                "aprobado": None,
                "nivel": d.get("nivel"),
                "fecha": d.get("fecha", ""),
                "intentos": 1,
            }
        )

    for q in quizzes:
        uid = q.get("id_usuario")
        lista.append(
            {
                "id": f"quiz-{q.get('id_resultado', '')}",
                "estudiante": _nombre_usuario(uid, usuarios),
                "id_usuario": uid,
                "curso": q.get("titulo_curso", q.get("slug", "")),
                "tipo": "quiz_final",
                "tema": q.get("titulo_leccion", q.get("leccion_id", "")),
                "puntaje": f"{q.get('correctas', 0)}/{q.get('total', 0)}",
                "porcentaje": q.get("porcentaje", 0),
                "estado": "Aprobado" if q.get("aprobado") else "No aprobado",
                "aprobado": q.get("aprobado", False),
                "nivel": None,
                "fecha": q.get("fecha", ""),
                "intentos": q.get("intento", 1),
            }
        )

    lista.sort(key=lambda x: x.get("fecha", ""), reverse=True)
    return lista


def _icono_actividad(tipo):
    return {
        "registro_usuario": "person_add",
        "curso_anadido": "library_add",
        "diagnostico_completado": "quiz",
        "leccion_iniciada": "play_lesson",
        "leccion_completada": "task_alt",
        "quiz_aprobado": "verified",
        "quiz_no_aprobado": "cancel",
        "meta_creada": "flag",
        "evento_creado": "event",
    }.get(tipo, "info")


def _categoria_resumen_actividad(tipo: str) -> str:
    """Agrupa tipos de actividad_sistema en series del gráfico."""
    t = (tipo or "").strip().lower()
    if t == "registro_usuario":
        return "registros"
    if t == "curso_anadido":
        return "cursos"
    if t == "diagnostico_completado":
        return "diagnosticos"
    if t in ("quiz_aprobado", "quiz_no_aprobado"):
        return "quizzes"
    if t in ("leccion_completada", "leccion_iniciada"):
        return "lecciones"
    if t == "meta_creada":
        return "metas"
    if t == "evento_creado":
        return "eventos"
    return "otros"


def _obtener_actividades_sistema_completas() -> list[dict]:
    actividades = cargar_datos("actividad_sistema")
    if not actividades:
        actividades = _reconstruir_actividad_desde_datos()
    return actividades


def _fechas_en_rango(fecha_desde: str, fecha_hasta: str) -> list[str]:
    try:
        d0 = datetime.strptime(fecha_desde, "%Y-%m-%d").date()
        d1 = datetime.strptime(fecha_hasta, "%Y-%m-%d").date()
    except ValueError:
        return []
    out = []
    cur = d0
    while cur <= d1:
        out.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=1)
    return out


def _etiqueta_dia_corta(fecha_str: str) -> str:
    try:
        dt = datetime.strptime(fecha_str, "%Y-%m-%d")
        return ["L", "M", "X", "J", "V", "S", "D"][dt.weekday()]
    except ValueError:
        return fecha_str[-2:] if fecha_str else "—"


def obtener_resumen_actividad_dashboard(periodo: str = "30") -> dict:
    """Datos para la tarjeta «Resumen de actividad» del dashboard admin."""
    fecha_desde, fecha_hasta, etiqueta, dias = calcular_rango_periodo_admin(periodo)
    actividades = _obtener_actividades_sistema_completas()

    filtradas = [
        a
        for a in actividades
        if fecha_en_rango((a.get("fecha") or "")[:10], fecha_desde, fecha_hasta)
    ]

    conteos_tipo = {
        "registros": 0,
        "cursos": 0,
        "diagnosticos": 0,
        "quizzes": 0,
        "lecciones": 0,
        "metas": 0,
        "eventos": 0,
        "otros": 0,
    }
    for act in filtradas:
        cat = _categoria_resumen_actividad(act.get("tipo"))
        conteos_tipo[cat] = conteos_tipo.get(cat, 0) + 1

    fechas = _fechas_en_rango(fecha_desde, fecha_hasta)
    por_dia: dict[str, dict[str, int]] = {f: {k: 0 for k in conteos_tipo} for f in fechas}
    for act in filtradas:
        f = (act.get("fecha") or "")[:10]
        if f not in por_dia:
            continue
        cat = _categoria_resumen_actividad(act.get("tipo"))
        por_dia[f][cat] = por_dia[f].get(cat, 0) + 1

    max_total = 0
    columnas = []
    for f in fechas:
        segmentos = por_dia.get(f, {})
        total_dia = sum(segmentos.values())
        max_total = max(max_total, total_dia)
        columnas.append(
            {
                "fecha": f,
                "etiqueta": _etiqueta_dia_corta(f) if dias <= 14 else f[8:10] + "/" + f[5:7],
                "total": total_dia,
                "segmentos": segmentos,
            }
        )

    if max_total <= 0:
        max_total = 1

    for col in columnas:
        segs = []
        total_dia = col["total"] or 0
        for key, color, label in _SERIES_RESUMEN_ACTIVIDAD:
            val = col["segmentos"].get(key, 0)
            if val <= 0:
                continue
            segs.append(
                {
                    "clave": key,
                    "valor": val,
                    "altura_pct": round((val / total_dia) * 100) if total_dia else 0,
                    "color": color,
                    "label": label,
                }
            )
        col["segmentos_visibles"] = segs
        col["altura_pct"] = (
            max(12, round((total_dia / max_total) * 100)) if total_dia else 0
        )

    quizzes_aprob = sum(
        1 for a in filtradas if a.get("tipo") == "quiz_aprobado"
    )
    quizzes_total = conteos_tipo["quizzes"]
    prom_aprob = round((quizzes_aprob / quizzes_total) * 100) if quizzes_total else 0

    evaluaciones = conteos_tipo["diagnosticos"] + conteos_tipo["quizzes"]
    actividad_total = sum(conteos_tipo.values()) - conteos_tipo.get("otros", 0)

    return {
        "periodo": {
            "clave": periodo,
            "dias": dias,
            "etiqueta": etiqueta,
            "desde": fecha_desde,
            "hasta": fecha_hasta,
        },
        "vacio": actividad_total <= 0,
        "columnas": columnas,
        "leyenda": [
            {"clave": k, "label": lbl, "color": c}
            for k, c, lbl in _SERIES_RESUMEN_ACTIVIDAD
        ],
        "indicadores": {
            "nuevos_usuarios": conteos_tipo["registros"],
            "cursos_anadidos": conteos_tipo["cursos"],
            "lecciones_completadas": conteos_tipo["lecciones"],
            "evaluaciones_realizadas": evaluaciones,
            "promedio_aprobacion": prom_aprob,
            "actividad_total": actividad_total,
            "metas_creadas": conteos_tipo["metas"],
            "eventos_creados": conteos_tipo["eventos"],
        },
        "actividad_reciente": _actividad_reciente_en_periodo(fecha_desde, fecha_hasta, 8),
    }


_SERIES_RESUMEN_ACTIVIDAD = (
    ("registros", "var(--nb-primary)", "Registros"),
    ("cursos", "#8b6cff", "Cursos añadidos"),
    ("diagnosticos", "#a78bfa", "Diagnósticos"),
    ("quizzes", "#c4b5fd", "Quizzes"),
    ("lecciones", "#10b981", "Lecciones"),
    ("metas", "#f59e0b", "Metas"),
    ("eventos", "#6366f1", "Eventos"),
)


def obtener_actividad_reciente_admin(limite=8):
    actividades = cargar_datos("actividad_sistema")
    usuarios = _mapa_usuarios()

    if not actividades:
        actividades = _reconstruir_actividad_desde_datos()

    items = []
    for act in sorted(actividades, key=lambda x: x.get("fecha", ""), reverse=True)[:limite]:
        items.append(
            {
                "tipo": act.get("tipo", "info"),
                "titulo": act.get("titulo", "Actividad"),
                "descripcion": act.get("descripcion", ""),
                "fecha": act.get("fecha", ""),
                "icono": _icono_actividad(act.get("tipo")),
                "relativo": _formato_tiempo_relativo(act.get("fecha", "")),
            }
        )
    return items


def _formato_tiempo_relativo(fecha_str):
    if not fecha_str:
        return ""
    try:
        if len(fecha_str) > 10:
            dt = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M")
        else:
            dt = datetime.strptime(fecha_str, "%Y-%m-%d")
        diff = datetime.now() - dt
        mins = int(diff.total_seconds() / 60)
        if mins < 1:
            return "AHORA"
        if mins < 60:
            return f"HACE {mins} MIN"
        horas = mins // 60
        if horas < 24:
            return f"HACE {horas} H"
        dias = horas // 24
        return f"HACE {dias} D"
    except ValueError:
        return fecha_str


def _reconstruir_actividad_desde_datos():
    """Genera actividad a partir de registros existentes si el log está vacío."""
    CURSOS_CATALOGO, _, _ = _catalogo()
    usuarios = _mapa_usuarios()
    items = []

    for u in usuarios.values():
        if u.get("fecha_registro"):
            items.append(
                {
                    "tipo": "registro_usuario",
                    "titulo": "Nuevo usuario registrado",
                    "descripcion": f"{u.get('nombre_completo', '')} se registró en la plataforma",
                    "fecha": u.get("fecha_registro") + " 12:00",
                    "id_usuario": u.get("id_usuario"),
                }
            )

    for asig in cargar_datos("cursos_asignados"):
        base = CURSOS_CATALOGO.get(asig.get("slug", ""), {})
        items.append(
            {
                "tipo": "curso_anadido",
                "titulo": "Curso añadido",
                "descripcion": f"{_nombre_usuario(asig['id_usuario'])} añadió {base.get('titulo', asig.get('slug', ''))}",
                "fecha": (asig.get("fecha_asignacion") or "") + " 12:00",
                "id_usuario": asig.get("id_usuario"),
            }
        )

    for d in cargar_datos("diagnosticos_catalogo"):
        base = CURSOS_CATALOGO.get(d.get("slug", ""), {})
        items.append(
            {
                "tipo": "diagnostico_completado",
                "titulo": "Diagnóstico completado",
                "descripcion": f"{_nombre_usuario(d['id_usuario'])} — {base.get('titulo', '')} ({d.get('titulo_nivel', '')})",
                "fecha": d.get("fecha", ""),
                "id_usuario": d.get("id_usuario"),
            }
        )

    for reg in cargar_datos("progreso_catalogo"):
        base = CURSOS_CATALOGO.get(reg.get("slug", ""), {})
        for lid in reg.get("lecciones_completadas", []):
            lec = obtener_leccion_curso(base, lid) if base else None
            items.append(
                {
                    "tipo": "leccion_completada",
                    "titulo": "Lección completada",
                    "descripcion": f"{_nombre_usuario(reg['id_usuario'])} completó {(lec or {}).get('titulo', lid)}",
                    "fecha": (reg.get("fecha_actualizacion") or "") + " 18:00",
                    "id_usuario": reg.get("id_usuario"),
                }
            )

    for q in cargar_datos("resultados_quiz"):
        tipo = "quiz_aprobado" if q.get("aprobado") else "quiz_no_aprobado"
        items.append(
            {
                "tipo": tipo,
                "titulo": "Quiz final aprobado" if q.get("aprobado") else "Quiz final no aprobado",
                "descripcion": f"{_nombre_usuario(q['id_usuario'])} — {q.get('titulo_leccion', '')} ({q.get('porcentaje', 0)}%)",
                "fecha": q.get("fecha", ""),
                "id_usuario": q.get("id_usuario"),
            }
        )

    for act in cargar_datos("actividades"):
        uid = act.get("id_usuario")
        if act.get("tipo") == "meta":
            items.append(
                {
                    "tipo": "meta_creada",
                    "titulo": "Meta personalizada creada",
                    "descripcion": f"{_nombre_usuario(uid)} — {act.get('titulo', 'Meta')}",
                    "fecha": act.get("creado_en") or act.get("fecha", ""),
                    "id_usuario": uid,
                }
            )
        elif act.get("tipo") in ("calendario", "evaluacion"):
            items.append(
                {
                    "tipo": "evento_creado",
                    "titulo": "Evento en calendario",
                    "descripcion": f"{_nombre_usuario(uid)} — {act.get('titulo', 'Evento')}",
                    "fecha": act.get("creado_en") or act.get("fecha", ""),
                    "id_usuario": uid,
                }
            )

    return items


def obtener_datos_admin_completos():
    resumen = obtener_resumen_admin()
    resumen_actividad = obtener_resumen_actividad_dashboard("30")
    return {
        "resumen": resumen,
        "usuarios": obtener_lista_usuarios_admin(),
        "cursos": obtener_lista_cursos_admin(),
        "lecciones": obtener_lista_lecciones_admin(),
        "evaluaciones": obtener_lista_evaluaciones_admin(),
        "cursos_populares": obtener_cursos_populares(),
        "distribucion_roles": obtener_distribucion_roles(),
        "actividad_reciente": resumen_actividad.get("actividad_reciente")
        or obtener_actividad_reciente_admin(),
        "resumen_actividad": resumen_actividad,
    }


def contar_lecciones_completadas() -> int:
    total = 0
    for reg in cargar_datos("progreso_catalogo"):
        total += len(reg.get("lecciones_completadas") or [])
    return total


def contar_cursos_activos() -> int:
    asignaciones = cargar_datos("cursos_asignados")
    if not asignaciones:
        return 0
    return len({a.get("slug") for a in asignaciones if a.get("slug")})


def obtener_progreso_general_estudiantes() -> int:
    lista = obtener_lista_usuarios_admin()
    estudiantes = [u for u in lista if u.get("id_rol") == 2]
    suma = 0
    count = 0
    for u in estudiantes:
        for c in u.get("cursos_asignados") or []:
            suma += int(c.get("progreso") or 0)
            count += 1
    return round(suma / count) if count else 0


def _contar_estudiantes_registrados() -> int:
    return sum(1 for u in cargar_datos("usuarios") if u.get("id_rol") == 2)


def _contar_estudiantes_activos() -> int:
    return sum(
        1
        for u in cargar_datos("usuarios")
        if u.get("id_rol") == 2 and u.get("activo", True)
    )


def _contar_por_grado() -> list[dict]:
    orden = ("noveno", "decimo", "once", "universidad")
    conteo = {g: 0 for g in orden}
    for u in cargar_datos("usuarios"):
        if u.get("id_rol") != 2:
            continue
        clave = normalizar_grado(u.get("grado") or u.get("nivel_academico"))
        if clave in conteo:
            conteo[clave] += 1
    total = sum(conteo.values()) or 1
    items = []
    for clave in orden:
        cantidad = conteo[clave]
        items.append(
            {
                "clave": clave,
                "nombre": GRADO_ETIQUETAS.get(clave, clave.title()),
                "cantidad": cantidad,
                "porcentaje": round((cantidad / total) * 100),
            }
        )
    return {"total": sum(conteo.values()), "por_grado": items}


def _segmentos_donut_grado(por_grado: list[dict]) -> list[dict]:
    colores = {
        "noveno": "#532cd8",
        "decimo": "#ab5200",
        "once": "#6c4cf1",
        "universidad": "#c7c4dd",
    }
    offset = 0
    segmentos = []
    for item in por_grado:
        pct = item.get("porcentaje", 0)
        if pct <= 0:
            continue
        segmentos.append(
            {
                "stroke": colores.get(item["clave"], "#532cd8"),
                "dasharray": f"{pct} 100",
                "dashoffset": -offset,
            }
        )
        offset += pct
    if not segmentos:
        segmentos.append({"stroke": "#f1ebf9", "dasharray": "100 100", "dashoffset": 0})
    return segmentos


def _contar_cursos_completados() -> int:
    CURSOS_CATALOGO, _, _ = _catalogo()
    completados = 0
    for u in obtener_lista_usuarios_admin():
        if u.get("id_rol") != 2:
            continue
        for c in u.get("cursos_asignados") or []:
            if int(c.get("progreso") or 0) >= 100:
                completados += 1
    return completados


def _contar_rachas_activas() -> int:
    try:
        registros = cargar_datos("racha_diaria")
    except Exception:
        return 0
    if not isinstance(registros, list):
        return 0
    return sum(1 for r in registros if int(r.get("racha_actual") or 0) > 0)


def _promedio_rendimiento_evaluaciones() -> int:
    quizzes = cargar_datos("resultados_quiz")
    if not quizzes:
        return 0
    return round(sum(int(q.get("porcentaje") or 0) for q in quizzes) / len(quizzes))


def _heatmap_actividad_semanal() -> list[dict]:
    """Siete columnas (L–D) con intensidad 0–4 según actividad del sistema."""
    actividades = cargar_datos("actividad_sistema")
    if not actividades:
        actividades = _reconstruir_actividad_desde_datos()
    por_dia = [0] * 7
    for act in actividades:
        fecha = (act.get("fecha") or "")[:10]
        if not fecha:
            continue
        try:
            wd = datetime.strptime(fecha, "%Y-%m-%d").weekday()
            por_dia[wd] += 1
        except ValueError:
            continue
    maximo = max(por_dia) or 1
    etiquetas = ["L", "M", "M", "J", "V", "S", "D"]

    def nivel(cuenta: int) -> int:
        if cuenta <= 0:
            return 0
        ratio = cuenta / maximo
        if ratio >= 0.85:
            return 4
        if ratio >= 0.55:
            return 3
        if ratio >= 0.3:
            return 2
        return 1

    columnas = []
    for i in range(7):
        n = nivel(por_dia[i])
        filas = []
        for row in range(4):
            intensidad = max(0, min(4, n - (3 - row))) if n else 0
            filas.append({"intensidad": intensidad})
        columnas.append({"etiqueta": etiquetas[i], "celdas": filas})
    return columnas


def _insights_desde_datos(metricas: dict, por_grado: list[dict], cursos_pop: list) -> list[str]:
    insights = []
    total = metricas.get("total_estudiantes", 0)
    if total:
        insights.append(
            f"<span class=\"font-bold text-primary\">Registro:</span> Hay {total} estudiantes registrados en la plataforma."
        )
    if por_grado:
        top = max(por_grado, key=lambda x: x.get("cantidad", 0))
        if top.get("cantidad", 0) > 0:
            insights.append(
                f"<span class=\"font-bold text-primary\">Grado líder:</span> {top['nombre']} concentra {top['cantidad']} estudiantes ({top['porcentaje']}%)."
            )
    if cursos_pop:
        lider = cursos_pop[0]
        insights.append(
            f"<span class=\"font-bold text-primary\">Curso destacado:</span> \"{lider['titulo']}\" con {lider['estudiantes']} inscripciones activas."
        )
    if metricas.get("rachas_activas", 0):
        insights.append(
            f"<span class=\"font-bold text-primary\">Rachas:</span> {metricas['rachas_activas']} estudiantes mantienen una racha diaria activa."
        )
    while len(insights) < 3:
        insights.append(
            "<span class=\"font-bold text-primary\">Nébula:</span> Los datos se actualizan desde los registros reales del sistema."
        )
    return insights[:3]


def _conteo_actividad_estudiante_periodo(
    id_usuario: int,
    fecha_desde: str,
    fecha_hasta: str,
    progreso_regs=None,
    diagnosticos=None,
    quizzes=None,
) -> dict:
    if progreso_regs is None:
        progreso_regs = cargar_datos("progreso_catalogo")
    if diagnosticos is None:
        diagnosticos = cargar_datos("diagnosticos_catalogo")
    if quizzes is None:
        quizzes = cargar_datos("resultados_quiz")

    lecciones = 0
    for reg in progreso_regs:
        if reg.get("id_usuario") != id_usuario:
            continue
        fa = (reg.get("fecha_actualizacion") or "")[:10]
        if fecha_en_rango(fa, fecha_desde, fecha_hasta):
            lecciones += len(reg.get("lecciones_completadas") or [])

    quizzes_n = 0
    for d in diagnosticos:
        if d.get("id_usuario") == id_usuario and fecha_en_rango(
            (d.get("fecha") or "")[:10], fecha_desde, fecha_hasta
        ):
            quizzes_n += 1
    for q in quizzes:
        if q.get("id_usuario") == id_usuario and fecha_en_rango(
            (q.get("fecha") or "")[:10], fecha_desde, fecha_hasta
        ):
            quizzes_n += 1

    return {"lecciones_periodo": lecciones, "quizzes_periodo": quizzes_n}


def _metricas_globales_periodo(fecha_desde: str, fecha_hasta: str) -> dict:
    progreso_regs = cargar_datos("progreso_catalogo")
    diagnosticos = cargar_datos("diagnosticos_catalogo")
    quizzes = cargar_datos("resultados_quiz")
    actividades = cargar_datos("actividad_sistema")
    if not actividades:
        actividades = _reconstruir_actividad_desde_datos()

    lecciones = 0
    for reg in progreso_regs:
        fa = (reg.get("fecha_actualizacion") or "")[:10]
        if fecha_en_rango(fa, fecha_desde, fecha_hasta):
            lecciones += len(reg.get("lecciones_completadas") or [])

    evals = 0
    for d in diagnosticos:
        if fecha_en_rango((d.get("fecha") or "")[:10], fecha_desde, fecha_hasta):
            evals += 1
    for q in quizzes:
        if fecha_en_rango((q.get("fecha") or "")[:10], fecha_desde, fecha_hasta):
            evals += 1

    usuarios_activos = set()
    for act in actividades:
        fa = (act.get("fecha") or "")[:10]
        if fecha_en_rango(fa, fecha_desde, fecha_hasta) and act.get("id_usuario"):
            usuarios_activos.add(act["id_usuario"])

    return {
        "lecciones_periodo": lecciones,
        "evaluaciones_periodo": evals,
        "usuarios_activos_periodo": len(usuarios_activos),
    }


def _barras_actividad_semanal(limite: int = 6, fecha_desde: str = "", fecha_hasta: str = "") -> list[dict]:
    """Alturas relativas (0–100) para gráfica de actividad según log del sistema."""
    actividades = cargar_datos("actividad_sistema")
    if not actividades:
        actividades = _reconstruir_actividad_desde_datos()
    por_dia: dict[str, int] = defaultdict(int)
    for act in actividades:
        fecha = (act.get("fecha") or "")[:10]
        if not fecha:
            continue
        if fecha_desde or fecha_hasta:
            if not fecha_en_rango(fecha, fecha_desde, fecha_hasta):
                continue
        por_dia[fecha] += 1
    dias = sorted(por_dia.keys(), reverse=True)[:limite]
    dias.reverse()
    if not dias:
        return [{"etiqueta": "—", "altura": 20} for _ in range(limite)]
    maximo = max(por_dia[d] for d in dias) or 1
    etiquetas = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    barras = []
    for i, d in enumerate(dias):
        barras.append(
            {
                "etiqueta": etiquetas[i % len(etiquetas)],
                "altura": max(15, round((por_dia[d] / maximo) * 95)),
                "valor": por_dia[d],
            }
        )
    while len(barras) < limite:
        barras.append({"etiqueta": "—", "altura": 12, "valor": 0})
    return barras[:limite]


def _tabla_rendimiento_estudiantes(
    limite: int = 8,
    fecha_desde: str = "",
    fecha_hasta: str = "",
) -> list[dict]:
    from perfil_service import AVATAR_ESTUDIANTE_DEFAULT

    progreso_regs = cargar_datos("progreso_catalogo")
    diagnosticos = cargar_datos("diagnosticos_catalogo")
    quizzes_data = cargar_datos("resultados_quiz")

    filas = []
    for u in obtener_lista_usuarios_admin():
        if u.get("id_rol") != 2:
            continue
        cursos = u.get("cursos_asignados") or []
        if not cursos:
            progreso = 0
            curso_titulo = "Sin curso asignado"
        else:
            mejor = max(cursos, key=lambda c: c.get("progreso", 0))
            progreso = mejor.get("progreso", 0)
            curso_titulo = mejor.get("titulo", "—")
        iniciales = "".join(p[0].upper() for p in (u.get("nombre_completo") or "U").split()[:2])
        estado = "Completado" if progreso >= 100 else ("Activo" if progreso > 0 else "Pendiente")
        periodo = _conteo_actividad_estudiante_periodo(
            u["id_usuario"],
            fecha_desde,
            fecha_hasta,
            progreso_regs,
            diagnosticos,
            quizzes_data,
        )
        filas.append(
            {
                "id_usuario": u["id_usuario"],
                "nombre": u.get("nombre_completo", ""),
                "iniciales": iniciales[:2],
                "avatar_url": u.get("avatar_url") or AVATAR_ESTUDIANTE_DEFAULT,
                "curso": curso_titulo,
                "progreso": progreso,
                "lecciones_periodo": periodo["lecciones_periodo"],
                "quizzes_periodo": periodo["quizzes_periodo"],
                "ultima_actividad": u.get("fecha_registro", "—"),
                "estado": estado,
            }
        )
    filas.sort(
        key=lambda x: (x["lecciones_periodo"] + x["quizzes_periodo"], x["progreso"]),
        reverse=True,
    )
    return filas[:limite]


def obtener_datos_analytics(dias: int = 30):
    from nebula_db import estado_bd, obtener_ultimas_estadisticas, sincronizar_estadisticas

    fecha_desde, fecha_hasta, periodo_etiqueta = calcular_rango_periodo(dias)
    metricas_periodo = _metricas_globales_periodo(fecha_desde, fecha_hasta)

    resumen = obtener_resumen_admin()
    lecciones_comp = contar_lecciones_completadas()
    cursos_activos = contar_cursos_activos()
    cursos_completados = _contar_cursos_completados()
    progreso_general = obtener_progreso_general_estudiantes()
    total_estudiantes = _contar_estudiantes_registrados()
    usuarios_activos = _contar_estudiantes_activos()
    rachas_activas = _contar_rachas_activas()
    rendimiento_prom = _promedio_rendimiento_evaluaciones()
    dist_grado = _contar_por_grado()
    cursos_pop = obtener_cursos_populares(4)
    max_inscritos = max((c.get("estudiantes", 0) for c in cursos_pop), default=1) or 1
    for curso in cursos_pop:
        curso["ancho_barra"] = round((curso.get("estudiantes", 0) / max_inscritos) * 100)

    metricas = {
        "total_usuarios": resumen["total_usuarios"],
        "total_estudiantes": total_estudiantes,
        "usuarios_activos": metricas_periodo["usuarios_activos_periodo"] or usuarios_activos,
        "cursos_activos": cursos_activos or resumen["total_cursos"],
        "cursos_completados": cursos_completados,
        "lecciones_completadas": metricas_periodo["lecciones_periodo"] or lecciones_comp,
        "total_evaluaciones": metricas_periodo["evaluaciones_periodo"] or resumen["total_evaluaciones"],
        "progreso_general": progreso_general,
        "tasa_finalizacion": progreso_general,
        "rachas_activas": rachas_activas,
        "rendimiento_promedio": rendimiento_prom,
        "periodo_dias": dias,
        "periodo_etiqueta": periodo_etiqueta,
        "periodo_desde": fecha_desde,
        "periodo_hasta": fecha_hasta,
        "grado_noveno": next(
            (g["cantidad"] for g in dist_grado["por_grado"] if g["clave"] == "noveno"), 0
        ),
        "grado_decimo": next(
            (g["cantidad"] for g in dist_grado["por_grado"] if g["clave"] == "decimo"), 0
        ),
        "grado_once": next(
            (g["cantidad"] for g in dist_grado["por_grado"] if g["clave"] == "once"), 0
        ),
        "grado_universidad": next(
            (g["cantidad"] for g in dist_grado["por_grado"] if g["clave"] == "universidad"), 0
        ),
    }
    try:
        sincronizar_estadisticas(metricas)
        metricas_sqlite = obtener_ultimas_estadisticas()
    except Exception as exc:
        import logging

        logging.getLogger("nebula.analytics").warning(
            "No se pudo sincronizar estadísticas en BD: %s", exc
        )
        metricas_sqlite = {}

    return {
        "metricas": metricas,
        "metricas_sqlite": metricas_sqlite,
        "actividad_reciente": _actividad_reciente_en_periodo(fecha_desde, fecha_hasta, 8),
        "cursos_populares": cursos_pop,
        "distribucion_grado": dist_grado,
        "donut_segmentos": _segmentos_donut_grado(dist_grado["por_grado"]),
        "distribucion_roles": obtener_distribucion_roles(),
        "barras_semana": _barras_actividad_semanal(7, fecha_desde, fecha_hasta),
        "heatmap_semana": _heatmap_actividad_semanal(),
        "rendimiento_estudiantes": _tabla_rendimiento_estudiantes(
            12, fecha_desde, fecha_hasta
        ),
        "insights": _insights_desde_datos(metricas, dist_grado["por_grado"], cursos_pop),
        "estado_bd": estado_bd(),
        "periodo": {
            "dias": dias,
            "etiqueta": periodo_etiqueta,
            "desde": fecha_desde,
            "hasta": fecha_hasta,
        },
    }


def _actividad_reciente_en_periodo(fecha_desde: str, fecha_hasta: str, limite: int = 8) -> list:
    actividades = _obtener_actividades_sistema_completas()
    filtradas = [
        a
        for a in actividades
        if fecha_en_rango((a.get("fecha") or "")[:10], fecha_desde, fecha_hasta)
    ]
    if not filtradas:
        return obtener_actividad_reciente_admin(limite)
    items = []
    for act in sorted(filtradas, key=lambda x: x.get("fecha", ""), reverse=True)[:limite]:
        items.append(
            {
                "tipo": act.get("tipo", "info"),
                "titulo": act.get("titulo", "Actividad"),
                "descripcion": act.get("descripcion", ""),
                "fecha": act.get("fecha", ""),
                "icono": _icono_actividad(act.get("tipo")),
                "relativo": _formato_tiempo_relativo(act.get("fecha", "")),
            }
        )
    return items


def listar_estudiantes_export():
    """Lista ligera de estudiantes para selectores y exportación PDF."""
    lista = []
    for u in obtener_lista_usuarios_admin():
        if u.get("id_rol") != 2:
            continue
        lista.append(
            {
                "id_usuario": u["id_usuario"],
                "nombre_completo": u["nombre_completo"],
                "correo": u.get("correo", ""),
                "grado": u.get("grado", ""),
                "activo": u.get("activo", True),
                "total_cursos": u.get("total_cursos", 0),
                "total_lecciones_completadas": u.get("total_lecciones_completadas", 0),
            }
        )
    return lista


def obtener_reporte_estudiante(
    id_usuario: int,
    tipo: str = "completo",
    fecha_desde: str = "",
    fecha_hasta: str = "",
) -> dict:
    """Datos agregados para generar PDF de un estudiante."""
    usuarios_map = _mapa_usuarios()
    if id_usuario not in usuarios_map:
        raise ValueError("Estudiante no encontrado.")
    u = usuarios_map[id_usuario]
    if u.get("id_rol") != 2:
        raise ValueError("El usuario seleccionado no es un estudiante.")

    roles_map = _mapa_roles()
    asignaciones_u = obtener_asignaciones_por_usuario()
    diagnosticos = cargar_datos("diagnosticos_catalogo")
    progreso_regs = cargar_datos("progreso_catalogo")
    quizzes = cargar_datos("resultados_quiz")
    detalle = _resumen_usuario(
        id_usuario,
        usuarios_map,
        roles_map,
        asignaciones_u,
        diagnosticos,
        progreso_regs,
        quizzes,
    )

    if not fecha_desde and not fecha_hasta:
        _, fecha_hasta_calc, _ = calcular_rango_periodo(30)
        fecha_hasta = fecha_hasta_calc
        fecha_desde = (datetime.strptime(fecha_hasta, "%Y-%m-%d").date() - timedelta(days=29)).strftime(
            "%Y-%m-%d"
        )

    evals = [
        e
        for e in detalle.get("evaluaciones", [])
        if fecha_en_rango((e.get("fecha") or "")[:10], fecha_desde, fecha_hasta)
    ]
    lecciones = [
        lec
        for lec in detalle.get("lecciones_completadas", [])
        if fecha_en_rango((lec.get("fecha") or "")[:10], fecha_desde, fecha_hasta)
    ]
    quizzes_detalle = [e for e in evals if e.get("tipo") == "quiz_final"]
    diagnosticos_detalle = [e for e in evals if e.get("tipo") == "diagnostico"]
    cursos = detalle.get("cursos_asignados", [])

    progreso_prom = 0
    if cursos:
        progreso_prom = round(sum(c.get("progreso", 0) for c in cursos) / len(cursos))

    quizzes_aprobados_periodo = sum(1 for e in quizzes_detalle if e.get("aprobado") is True)
    quizzes_no_aprobados_periodo = sum(1 for e in quizzes_detalle if e.get("aprobado") is False)

    from perfil_service import AVATAR_ESTUDIANTE_DEFAULT, resolve_avatar_url

    n = _nebula()
    avatar_url = resolve_avatar_url(
        u.get("foto_perfil"),
        u.get("foto_actualizada_en"),
        lambda rel: n.url_for("static", filename=rel),
        AVATAR_ESTUDIANTE_DEFAULT,
    )

    tipo = (tipo or "completo").lower()
    tipos_validos = ("academico", "progreso", "asistencia", "evaluaciones", "completo")
    if tipo not in tipos_validos:
        tipo = "completo"

    return {
        "tipo": tipo,
        "generado_en": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "rango": {"desde": fecha_desde or "—", "hasta": fecha_hasta or "—"},
        "estudiante": {
            "id_usuario": id_usuario,
            "nombre_completo": detalle["nombre_completo"],
            "correo": detalle.get("correo", ""),
            "grado": detalle.get("grado", ""),
            "activo": detalle.get("activo", True),
            "fecha_registro": detalle.get("fecha_registro", ""),
            "avatar_url": avatar_url,
        },
        "metricas": {
            "cursos_asignados": len(cursos),
            "lecciones_completadas": len(lecciones),
            "progreso_promedio": progreso_prom,
            "evaluaciones_total": len(evals),
            "quizzes_total": len(quizzes_detalle) + len(diagnosticos_detalle),
            "quizzes_aprobados": quizzes_aprobados_periodo,
            "quizzes_no_aprobados": quizzes_no_aprobados_periodo,
        },
        "cursos": cursos if tipo in ("academico", "progreso", "completo") else [],
        "lecciones": lecciones if tipo in ("progreso", "completo") else [],
        "quizzes": (quizzes_detalle + diagnosticos_detalle)
        if tipo in ("evaluaciones", "academico", "completo")
        else [],
        "evaluaciones": evals if tipo in ("evaluaciones", "academico", "completo") else [],
        "asistencia": {
            "activo": detalle.get("activo", True),
            "ultima_actividad": detalle.get("fecha_registro", "—"),
        }
        if tipo in ("asistencia", "completo")
        else None,
    }


def eliminar_estudiante(id_usuario: int, id_admin: int) -> None:
    """Elimina un estudiante y todos sus datos (PostgreSQL / capa nebula_data)."""
    if id_usuario == id_admin:
        raise ValueError("No puedes eliminar tu propia cuenta.")

    from extensions import db
    from models import User
    from nebula_data import eliminar_usuario_completo

    estudiante = db.session.get(User, int(id_usuario))
    if estudiante is None:
        raise ValueError("Estudiante no encontrado.")
    if estudiante.id_rol != 2:
        raise ValueError("Solo se pueden eliminar cuentas de estudiante.")

    eliminar_usuario_completo(id_usuario)


def suspender_estudiante(id_usuario: int, id_admin: int, activo: bool) -> dict:
    if id_usuario == id_admin:
        raise ValueError("No puedes suspender tu propia cuenta.")
    usuarios = cargar_datos("usuarios")
    idx = next(
        (i for i, u in enumerate(usuarios) if u.get("id_usuario") == id_usuario),
        None,
    )
    if idx is None:
        raise ValueError("Estudiante no encontrado.")
    if usuarios[idx].get("id_rol") != 2:
        raise ValueError("Solo se pueden suspender estudiantes.")
    from nebula_data import actualizar_campos_usuario

    actualizar_campos_usuario(int(id_usuario), {"activo": bool(activo)})
    return {
        "id_usuario": id_usuario,
        "activo": activo,
        "nombre_completo": usuarios[idx].get("nombre_completo", ""),
    }


def obtener_perfil_admin(id_usuario: int) -> dict:
    usuarios = _mapa_usuarios()
    roles_map = _mapa_roles()
    u = usuarios.get(id_usuario, {})
    resumen = obtener_resumen_admin()
    foto = u.get("foto_perfil") or ""
    return {
        "id_usuario": id_usuario,
        "nombre_completo": u.get("nombre_completo", "Administrador"),
        "correo": u.get("correo", ""),
        "username": u.get("username", ""),
        "rol": roles_map.get(u.get("id_rol"), "Administrador"),
        "fecha_registro": u.get("fecha_registro", "—"),
        "foto_url": foto,
        "activo": u.get("activo", True),
        "cursos_administrados": resumen["total_cursos"],
        "estadisticas": {
            "usuarios": resumen["total_usuarios"],
            "cursos": resumen["total_cursos"],
            "evaluaciones": resumen["total_evaluaciones"],
            "lecciones_completadas": contar_lecciones_completadas(),
        },
    }


