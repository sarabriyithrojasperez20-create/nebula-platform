# -*- coding: utf-8 -*-
"""Catálogo académico administrable — cursos, lecciones y evaluaciones en BD."""

from __future__ import annotations

import copy
import logging
import re
import unicodedata
from typing import Any

from sqlalchemy import select

from extensions import db
from models import CatalogCourse, CatalogEvaluation, CatalogLesson, CatalogQuestion

logger = logging.getLogger("nebula.catalog")

_DIAGNOSTICO_CACHE: dict[str, dict] = {}
_QUIZ_CACHE: dict[str, dict] = {}
_LECCION_CONTENIDO_CACHE: dict[str, dict] = {}
_NIVEL_LECCION_CACHE: dict[str, dict[str, str]] = {}


def slugify(text: str) -> str:
    raw = unicodedata.normalize("NFKD", (text or "").strip())
    raw = raw.encode("ascii", "ignore").decode("ascii").lower()
    raw = re.sub(r"[^\w\s-]", "", raw)
    slug = re.sub(r"[-\s]+", "-", raw).strip("-")
    return slug or "curso"


def _pregunta_a_dict(q: CatalogQuestion) -> dict:
    opciones = q.opciones or {}
    return {
        "tipo": q.tipo or "Opción múltiple",
        "enunciado": q.enunciado,
        "opciones": opciones,
        "correcta": (q.respuesta_correcta or "A").upper(),
        "explicacion": q.explicacion or "",
        "pista": q.pista or "",
        "leccion_id": q.leccion_id or "",
        "tema": q.tema or "",
        "dificultad": q.dificultad or "media",
        "id": q.id,
    }


def _evaluacion_a_quiz(ev: CatalogEvaluation) -> dict:
    preguntas = [_pregunta_a_dict(q) for q in ev.preguntas if q.enunciado]
    return {
        "id": ev.id,
        "titulo_tema": ev.titulo or "Evaluación",
        "tipo": ev.tipo,
        "porcentaje_aprobacion": ev.porcentaje_aprobacion,
        "preguntas": preguntas,
    }


def rebuild_runtime_catalog() -> None:
    """Actualiza CURSOS_CATALOGO en app y cachés de contenido."""
    import app as nebula_app

    global _DIAGNOSTICO_CACHE, _QUIZ_CACHE, _LECCION_CONTENIDO_CACHE, _NIVEL_LECCION_CACHE
    _DIAGNOSTICO_CACHE = {}
    _QUIZ_CACHE = {}
    _LECCION_CONTENIDO_CACHE = {}
    _NIVEL_LECCION_CACHE = {}

    cursos_db = db.session.scalars(
        select(CatalogCourse).order_by(CatalogCourse.orden, CatalogCourse.titulo)
    ).all()

    nuevo_catalogo: dict[str, dict] = {}
    nuevo_orden: list[str] = []
    nuevo_materia: dict[str, str] = {}

    for row in cursos_db:
        if not row.activo:
            continue
        slug = row.slug
        nuevo_orden.append(slug)
        nuevo_materia[slug] = row.categoria or "todas"

        lecciones_rows = sorted(
            [l for l in row.lecciones if l.activo],
            key=lambda x: (x.orden, x.id),
        )
        lecciones = [
            {
                "id": l.leccion_id,
                "titulo": l.titulo,
                "duracion": l.duracion or "30 min",
                "estado": "pendiente",
            }
            for l in lecciones_rows
        ]

        for l in lecciones_rows:
            clave = f"{slug}:{l.leccion_id}"
            if l.contenido:
                _LECCION_CONTENIDO_CACHE[clave] = copy.deepcopy(l.contenido)

        for ev in row.evaluaciones:
            if not ev.activo:
                continue
            quiz = _evaluacion_a_quiz(ev)
            if not quiz["preguntas"]:
                continue
            if ev.tipo == "diagnostico":
                _DIAGNOSTICO_CACHE[slug] = quiz
                if ev.nivel_lecciones:
                    _NIVEL_LECCION_CACHE[slug] = copy.deepcopy(ev.nivel_lecciones)
            elif ev.tipo == "quiz":
                key = slug
                if ev.leccion_id:
                    key = f"{slug}:{ev.leccion_id}"
                _QUIZ_CACHE[key] = quiz

        nuevo_catalogo[slug] = {
            "id_curso": row.orden or len(nuevo_orden),
            "slug": slug,
            "titulo": row.titulo,
            "nivel": row.nivel,
            "porcentaje": 0,
            "duracion_total": row.duracion_total or "",
            "descripcion": row.descripcion or "",
            "imagen": row.imagen or "",
            "temas": list(row.temas or []),
            "modulos": list(row.modulos or []),
            "lecciones": lecciones,
            "activo": row.activo,
        }

    nebula_app.CURSOS_CATALOGO.clear()
    nebula_app.CURSOS_CATALOGO.update(nuevo_catalogo)
    nebula_app.ORDEN_CURSOS_CATALOGO.clear()
    nebula_app.ORDEN_CURSOS_CATALOGO.extend(nuevo_orden)
    nebula_app.MATERIA_POR_SLUG.clear()
    nebula_app.MATERIA_POR_SLUG.update(nuevo_materia)

    logger.info("Catálogo en memoria: %d cursos activos", len(nuevo_orden))


def ensure_catalog_seeded(app) -> None:
    """Primera ejecución: importa catálogo hardcodeado a BD."""
    with app.app_context():
        from sqlalchemy import func

        if (db.session.scalar(select(func.count()).select_from(CatalogCourse)) or 0) > 0:
            rebuild_runtime_catalog()
            return

        import app as nebula_app
        from diagnosticos_contenido import DIAGNOSTICO_POR_CURSO, NIVEL_LECCION_POR_CURSO
        from lecciones_contenido import CONTENIDO_LECCIONES
        from quizzes_contenido import QUIZ_POR_CURSO

        orden = 0
        for slug in nebula_app.ORDEN_CURSOS_CATALOGO:
            base = nebula_app.CURSOS_CATALOGO.get(slug)
            if not base:
                continue
            orden += 1
            curso = CatalogCourse(
                slug=slug,
                titulo=base.get("titulo", slug),
                nivel=base.get("nivel", "Intermedio"),
                categoria=nebula_app.MATERIA_POR_SLUG.get(slug, "matematicas"),
                descripcion=base.get("descripcion", ""),
                imagen=base.get("imagen", ""),
                duracion_total=base.get("duracion_total", ""),
                temas=list(base.get("temas") or []),
                modulos=list(base.get("modulos") or []),
                activo=True,
                orden=orden,
            )
            db.session.add(curso)

            for i, lec in enumerate(base.get("lecciones") or []):
                lid = lec.get("id", f"leccion-{i}")
                clave = f"{slug}:{lid}"
                contenido = copy.deepcopy(CONTENIDO_LECCIONES.get(clave) or {})
                db.session.add(
                    CatalogLesson(
                        curso_slug=slug,
                        leccion_id=lid,
                        titulo=lec.get("titulo", lid),
                        duracion=lec.get("duracion", "30 min"),
                        orden=i,
                        activo=True,
                        contenido=contenido or None,
                    )
                )

            diag = DIAGNOSTICO_POR_CURSO.get(slug)
            if diag:
                ev_d = CatalogEvaluation(
                    curso_slug=slug,
                    tipo="diagnostico",
                    titulo=diag.get("titulo_tema", "Diagnóstico"),
                    porcentaje_aprobacion=70,
                    activo=True,
                    nivel_lecciones=NIVEL_LECCION_POR_CURSO.get(slug),
                )
                db.session.add(ev_d)
                db.session.flush()
                for i, p in enumerate(diag.get("preguntas") or []):
                    db.session.add(
                        CatalogQuestion(
                            evaluacion_id=ev_d.id,
                            orden=i,
                            enunciado=p.get("enunciado", ""),
                            tipo=p.get("tipo", "Opción múltiple"),
                            opciones=p.get("opciones") or {},
                            respuesta_correcta=(p.get("correcta") or "A").upper(),
                            explicacion=p.get("explicacion", ""),
                            pista=p.get("pista", ""),
                            leccion_id=p.get("leccion_id"),
                        )
                    )

            quiz = QUIZ_POR_CURSO.get(slug)
            if quiz:
                ev_q = CatalogEvaluation(
                    curso_slug=slug,
                    tipo="quiz",
                    titulo=quiz.get("titulo_tema", "Quiz"),
                    porcentaje_aprobacion=70,
                    activo=True,
                )
                db.session.add(ev_q)
                db.session.flush()
                for i, p in enumerate(quiz.get("preguntas") or []):
                    db.session.add(
                        CatalogQuestion(
                            evaluacion_id=ev_q.id,
                            orden=i,
                            enunciado=p.get("enunciado", ""),
                            tipo=p.get("tipo", "Opción múltiple"),
                            opciones=p.get("opciones") or {},
                            respuesta_correcta=(p.get("correcta") or "A").upper(),
                            explicacion=p.get("explicacion", ""),
                            pista=p.get("pista", ""),
                        )
                    )

        db.session.commit()
        logger.info("Catálogo inicial importado desde contenido hardcodeado.")
        rebuild_runtime_catalog()


def get_diagnostico(slug: str) -> dict | None:
    if slug in _DIAGNOSTICO_CACHE:
        return copy.deepcopy(_DIAGNOSTICO_CACHE[slug])
    from diagnosticos_contenido import DIAGNOSTICO_POR_CURSO

    if slug in DIAGNOSTICO_POR_CURSO:
        return copy.deepcopy(DIAGNOSTICO_POR_CURSO[slug])
    return None


def get_quiz(slug: str, leccion_id: str | None = None) -> dict | None:
    if leccion_id:
        key = f"{slug}:{leccion_id}"
        if key in _QUIZ_CACHE:
            return copy.deepcopy(_QUIZ_CACHE[key])
    if slug in _QUIZ_CACHE:
        return copy.deepcopy(_QUIZ_CACHE[slug])
    from quizzes_contenido import QUIZ_POR_CURSO

    if slug in QUIZ_POR_CURSO:
        return copy.deepcopy(QUIZ_POR_CURSO[slug])
    return None


def get_leccion_contenido(slug: str, leccion_id: str) -> dict | None:
    clave = f"{slug}:{leccion_id}"
    if clave in _LECCION_CONTENIDO_CACHE:
        return copy.deepcopy(_LECCION_CONTENIDO_CACHE[clave])
    from lecciones_contenido import CONTENIDO_LECCIONES

    if clave in CONTENIDO_LECCIONES:
        return copy.deepcopy(CONTENIDO_LECCIONES[clave])
    return None


def get_nivel_lecciones(slug: str) -> dict[str, str]:
    if slug in _NIVEL_LECCION_CACHE:
        return copy.deepcopy(_NIVEL_LECCION_CACHE[slug])
    from diagnosticos_contenido import NIVEL_LECCION_POR_CURSO

    return copy.deepcopy(NIVEL_LECCION_POR_CURSO.get(slug, {}))


def curso_activo(slug: str) -> bool:
    row = db.session.get(CatalogCourse, slug)
    return bool(row and row.activo)


def _validar_curso_payload(data: dict) -> tuple[dict, str | None]:
    titulo = (data.get("titulo") or "").strip()
    if len(titulo) < 2:
        return {}, "El nombre del curso es obligatorio."
    slug = (data.get("slug") or "").strip() or slugify(titulo)
    if len(slug) < 2:
        return {}, "El identificador del curso no es válido."
    return {
        "slug": slug,
        "titulo": titulo,
        "nivel": (data.get("nivel") or "Intermedio").strip(),
        "categoria": (data.get("categoria") or "matematicas").strip(),
        "descripcion": (data.get("descripcion") or "").strip(),
        "imagen": (data.get("imagen") or "").strip(),
        "duracion_total": (data.get("duracion_total") or "").strip(),
        "temas": data.get("temas") if isinstance(data.get("temas"), list) else [],
        "modulos": data.get("modulos") if isinstance(data.get("modulos"), list) else [],
        "activo": bool(data.get("activo", True)),
    }, None


def crear_curso(data: dict) -> dict:
    payload, err = _validar_curso_payload(data)
    if err:
        raise ValueError(err)
    if db.session.get(CatalogCourse, payload["slug"]):
        raise ValueError("Ya existe un curso con ese identificador.")
    max_orden = db.session.scalar(select(db.func.max(CatalogCourse.orden))) or 0
    row = CatalogCourse(orden=max_orden + 1, **payload)
    db.session.add(row)
    db.session.commit()
    rebuild_runtime_catalog()
    return {"ok": True, "slug": row.slug, "curso": payload}


def actualizar_curso(slug: str, data: dict) -> dict:
    row = db.session.get(CatalogCourse, slug)
    if not row:
        raise ValueError("Curso no encontrado.")
    titulo = (data.get("titulo") or row.titulo).strip()
    if len(titulo) < 2:
        raise ValueError("El nombre del curso es obligatorio.")
    row.titulo = titulo
    row.nivel = (data.get("nivel") or row.nivel).strip()
    row.categoria = (data.get("categoria") or row.categoria).strip()
    row.descripcion = (data.get("descripcion") or row.descripcion or "").strip()
    row.imagen = (data.get("imagen") or row.imagen or "").strip()
    row.duracion_total = (data.get("duracion_total") or row.duracion_total or "").strip()
    if "temas" in data and isinstance(data["temas"], list):
        row.temas = data["temas"]
    if "modulos" in data and isinstance(data["modulos"], list):
        row.modulos = data["modulos"]
    if "activo" in data:
        row.activo = bool(data["activo"])
    db.session.commit()
    rebuild_runtime_catalog()
    return {"ok": True, "slug": slug}


def eliminar_curso(slug: str) -> dict:
    row = db.session.get(CatalogCourse, slug)
    if not row:
        raise ValueError("Curso no encontrado.")
    db.session.delete(row)
    db.session.commit()
    rebuild_runtime_catalog()
    return {"ok": True}


def crear_leccion(data: dict) -> dict:
    curso_slug = (data.get("curso_slug") or "").strip()
    if not curso_slug or not db.session.get(CatalogCourse, curso_slug):
        raise ValueError("Debe seleccionar un curso válido.")
    titulo = (data.get("titulo") or "").strip()
    if len(titulo) < 2:
        raise ValueError("El título de la lección es obligatorio.")
    leccion_id = (data.get("leccion_id") or "").strip() or slugify(titulo)
    existente = db.session.scalar(
        select(CatalogLesson).where(
            CatalogLesson.curso_slug == curso_slug,
            CatalogLesson.leccion_id == leccion_id,
        )
    )
    if existente:
        raise ValueError("Ya existe una lección con ese identificador en el curso.")
    max_ord = db.session.scalar(
        select(db.func.max(CatalogLesson.orden)).where(CatalogLesson.curso_slug == curso_slug)
    ) or 0
    contenido = data.get("contenido") if isinstance(data.get("contenido"), dict) else {}
    row = CatalogLesson(
        curso_slug=curso_slug,
        leccion_id=leccion_id,
        titulo=titulo,
        duracion=(data.get("duracion") or "30 min").strip(),
        orden=int(data.get("orden", max_ord + 1)),
        activo=bool(data.get("activo", True)),
        contenido=contenido,
    )
    db.session.add(row)
    db.session.commit()
    rebuild_runtime_catalog()
    return {"ok": True, "id": row.id, "leccion_id": leccion_id}


def actualizar_leccion(lesson_pk: int, data: dict) -> dict:
    row = db.session.get(CatalogLesson, lesson_pk)
    if not row:
        raise ValueError("Lección no encontrada.")
    titulo = (data.get("titulo") or row.titulo).strip()
    if len(titulo) < 2:
        raise ValueError("El título de la lección es obligatorio.")
    row.titulo = titulo
    row.duracion = (data.get("duracion") or row.duracion or "30 min").strip()
    if "orden" in data:
        row.orden = int(data["orden"])
    if "activo" in data:
        row.activo = bool(data["activo"])
    if "contenido" in data and isinstance(data["contenido"], dict):
        row.contenido = data["contenido"]
    db.session.commit()
    rebuild_runtime_catalog()
    return {"ok": True, "id": row.id}


def eliminar_leccion(lesson_pk: int) -> dict:
    row = db.session.get(CatalogLesson, lesson_pk)
    if not row:
        raise ValueError("Lección no encontrada.")
    db.session.delete(row)
    db.session.commit()
    rebuild_runtime_catalog()
    return {"ok": True}


def listar_evaluaciones_catalogo() -> list[dict]:
    rows = db.session.scalars(
        select(CatalogEvaluation).order_by(CatalogEvaluation.curso_slug, CatalogEvaluation.tipo)
    ).all()
    out = []
    for ev in rows:
        curso = db.session.get(CatalogCourse, ev.curso_slug)
        out.append(
            {
                "id": ev.id,
                "curso_slug": ev.curso_slug,
                "curso_titulo": curso.titulo if curso else ev.curso_slug,
                "tipo": ev.tipo,
                "leccion_id": ev.leccion_id,
                "titulo": ev.titulo,
                "porcentaje_aprobacion": ev.porcentaje_aprobacion,
                "activo": ev.activo,
                "num_preguntas": len(ev.preguntas),
            }
        )
    return out


def crear_evaluacion(data: dict) -> dict:
    curso_slug = (data.get("curso_slug") or "").strip()
    if not curso_slug or not db.session.get(CatalogCourse, curso_slug):
        raise ValueError("Debe asociar la evaluación a un curso.")
    tipo = (data.get("tipo") or "").strip().lower()
    if tipo not in ("diagnostico", "quiz"):
        raise ValueError("Tipo de evaluación inválido (diagnostico o quiz).")
    titulo = (data.get("titulo") or "").strip() or (
        "Diagnóstico" if tipo == "diagnostico" else "Quiz final"
    )
    if tipo == "diagnostico":
        existente = db.session.scalar(
            select(CatalogEvaluation).where(
                CatalogEvaluation.curso_slug == curso_slug,
                CatalogEvaluation.tipo == "diagnostico",
            )
        )
        if existente:
            raise ValueError("Este curso ya tiene un diagnóstico. Edítelo en lugar de crear otro.")
    activo = bool(data.get("activo", True))
    preguntas_in = data.get("preguntas") or []
    if activo and not preguntas_in:
        raise ValueError("Una evaluación activa debe tener al menos una pregunta.")
    ev = CatalogEvaluation(
        curso_slug=curso_slug,
        tipo=tipo,
        leccion_id=(data.get("leccion_id") or "").strip() or None,
        titulo=titulo,
        porcentaje_aprobacion=int(data.get("porcentaje_aprobacion", 70)),
        activo=activo,
        nivel_lecciones=data.get("nivel_lecciones")
        if isinstance(data.get("nivel_lecciones"), dict)
        else None,
    )
    db.session.add(ev)
    db.session.flush()
    for i, p in enumerate(preguntas_in):
        _guardar_pregunta_en_evaluacion(ev.id, p, i)
    db.session.commit()
    rebuild_runtime_catalog()
    return {"ok": True, "id": ev.id}


def actualizar_evaluacion(ev_id: int, data: dict) -> dict:
    ev = db.session.get(CatalogEvaluation, ev_id)
    if not ev:
        raise ValueError("Evaluación no encontrada.")
    if "titulo" in data:
        ev.titulo = (data.get("titulo") or ev.titulo).strip()
    if "porcentaje_aprobacion" in data:
        ev.porcentaje_aprobacion = int(data["porcentaje_aprobacion"])
    if "activo" in data:
        ev.activo = bool(data["activo"])
    if "leccion_id" in data:
        ev.leccion_id = (data.get("leccion_id") or "").strip() or None
    if ev.activo and not ev.preguntas and not data.get("preguntas"):
        raise ValueError("Una evaluación activa debe tener al menos una pregunta.")
    db.session.commit()
    rebuild_runtime_catalog()
    return {"ok": True, "id": ev.id}


def eliminar_evaluacion(ev_id: int) -> dict:
    ev = db.session.get(CatalogEvaluation, ev_id)
    if not ev:
        raise ValueError("Evaluación no encontrada.")
    db.session.delete(ev)
    db.session.commit()
    rebuild_runtime_catalog()
    return {"ok": True}


def obtener_evaluacion_completa(ev_id: int) -> dict | None:
    ev = db.session.get(CatalogEvaluation, ev_id)
    if not ev:
        return None
    return {
        "id": ev.id,
        "curso_slug": ev.curso_slug,
        "tipo": ev.tipo,
        "leccion_id": ev.leccion_id,
        "titulo": ev.titulo,
        "porcentaje_aprobacion": ev.porcentaje_aprobacion,
        "activo": ev.activo,
        "preguntas": [_pregunta_a_dict(q) for q in sorted(ev.preguntas, key=lambda x: x.orden)],
    }


def _guardar_pregunta_en_evaluacion(ev_id: int, data: dict, orden: int | None = None) -> CatalogQuestion:
    enunciado = (data.get("enunciado") or "").strip()
    if len(enunciado) < 3:
        raise ValueError("El enunciado de la pregunta es obligatorio.")
    correcta = (data.get("respuesta_correcta") or data.get("correcta") or "").strip().upper()
    if correcta not in ("A", "B", "C", "D"):
        raise ValueError("Debe indicar la respuesta correcta (A, B, C o D).")
    opciones = data.get("opciones") or {}
    if not isinstance(opciones, dict):
        opciones = {
            "A": data.get("opcion_a", ""),
            "B": data.get("opcion_b", ""),
            "C": data.get("opcion_c", ""),
            "D": data.get("opcion_d", ""),
        }
    q = CatalogQuestion(
        evaluacion_id=ev_id,
        orden=int(orden if orden is not None else data.get("orden", 0)),
        enunciado=enunciado,
        tipo=(data.get("tipo") or "Opción múltiple"),
        opciones=opciones,
        respuesta_correcta=correcta,
        explicacion=(data.get("explicacion") or "").strip(),
        pista=(data.get("pista") or "").strip(),
        tema=(data.get("tema") or "").strip(),
        dificultad=(data.get("dificultad") or "media").strip(),
        leccion_id=(data.get("leccion_id") or "").strip() or None,
    )
    db.session.add(q)
    return q


def crear_pregunta(ev_id: int, data: dict) -> dict:
    ev = db.session.get(CatalogEvaluation, ev_id)
    if not ev:
        raise ValueError("Evaluación no encontrada.")
    max_ord = max((q.orden for q in ev.preguntas), default=-1)
    q = _guardar_pregunta_en_evaluacion(ev, data, max_ord + 1)
    db.session.commit()
    rebuild_runtime_catalog()
    return {"ok": True, "id": q.id}


def actualizar_pregunta(pregunta_id: int, data: dict) -> dict:
    q = db.session.get(CatalogQuestion, pregunta_id)
    if not q:
        raise ValueError("Pregunta no encontrada.")
    enunciado = (data.get("enunciado") or q.enunciado).strip()
    if len(enunciado) < 3:
        raise ValueError("El enunciado de la pregunta es obligatorio.")
    q.enunciado = enunciado
    correcta = (data.get("respuesta_correcta") or data.get("correcta") or q.respuesta_correcta).upper()
    if correcta not in ("A", "B", "C", "D"):
        raise ValueError("Debe indicar la respuesta correcta (A, B, C o D).")
    q.respuesta_correcta = correcta
    if "opciones" in data and isinstance(data["opciones"], dict):
        q.opciones = data["opciones"]
    elif any(data.get(k) for k in ("opcion_a", "opcion_b", "opcion_c", "opcion_d")):
        prev = q.opciones or {}
        q.opciones = {
            "A": data.get("opcion_a", prev.get("A", "")),
            "B": data.get("opcion_b", prev.get("B", "")),
            "C": data.get("opcion_c", prev.get("C", "")),
            "D": data.get("opcion_d", prev.get("D", "")),
        }
    if "explicacion" in data:
        q.explicacion = (data.get("explicacion") or "").strip()
    if "pista" in data:
        q.pista = (data.get("pista") or "").strip()
    if "tema" in data:
        q.tema = (data.get("tema") or "").strip()
    if "dificultad" in data:
        q.dificultad = (data.get("dificultad") or "media").strip()
    if "leccion_id" in data:
        q.leccion_id = (data.get("leccion_id") or "").strip() or None
    db.session.commit()
    rebuild_runtime_catalog()
    return {"ok": True, "id": q.id}


def eliminar_pregunta(pregunta_id: int) -> dict:
    q = db.session.get(CatalogQuestion, pregunta_id)
    if not q:
        raise ValueError("Pregunta no encontrada.")
    ev_id = q.evaluacion_id
    db.session.delete(q)
    db.session.flush()
    ev = db.session.get(CatalogEvaluation, ev_id)
    if ev and ev.activo and not ev.preguntas:
        raise ValueError(
            "No puede eliminar la última pregunta de una evaluación activa. "
            "Desactive la evaluación o agregue otra pregunta primero."
        )
    db.session.commit()
    rebuild_runtime_catalog()
    return {"ok": True}


def listar_cursos_admin_db() -> list[dict]:
    rows = db.session.scalars(
        select(CatalogCourse).order_by(CatalogCourse.orden, CatalogCourse.titulo)
    ).all()
    out = []
    for row in rows:
        lecciones = [l for l in row.lecciones if l.activo]
        evals = [e for e in row.evaluaciones if e.activo]
        out.append(
            {
                "slug": row.slug,
                "titulo": row.titulo,
                "nivel": row.nivel,
                "categoria": row.categoria,
                "descripcion": row.descripcion,
                "imagen": row.imagen,
                "duracion_total": row.duracion_total,
                "temas": list(row.temas or []),
                "modulos": list(row.modulos or []),
                "activo": row.activo,
                "orden": row.orden,
                "num_lecciones": len(lecciones),
                "num_evaluaciones": len(evals),
            }
        )
    return out


def obtener_curso_admin(slug: str) -> dict | None:
    row = db.session.get(CatalogCourse, slug)
    if not row:
        return None
    return {
        "slug": row.slug,
        "titulo": row.titulo,
        "nivel": row.nivel,
        "categoria": row.categoria,
        "descripcion": row.descripcion,
        "imagen": row.imagen,
        "duracion_total": row.duracion_total,
        "temas": list(row.temas or []),
        "modulos": list(row.modulos or []),
        "activo": row.activo,
        "orden": row.orden,
        "lecciones": [
            {
                "id": l.id,
                "leccion_id": l.leccion_id,
                "titulo": l.titulo,
                "duracion": l.duracion,
                "orden": l.orden,
                "activo": l.activo,
            }
            for l in sorted(row.lecciones, key=lambda x: (x.orden, x.id))
        ],
    }


def obtener_leccion_admin(lesson_pk: int) -> dict | None:
    row = db.session.get(CatalogLesson, lesson_pk)
    if not row:
        return None
    return {
        "id": row.id,
        "curso_slug": row.curso_slug,
        "leccion_id": row.leccion_id,
        "titulo": row.titulo,
        "duracion": row.duracion,
        "orden": row.orden,
        "activo": row.activo,
        "contenido": row.contenido or {},
    }


def umbral_aprobacion_quiz(slug: str, leccion_id: str | None = None) -> int:
    key = f"{slug}:{leccion_id}" if leccion_id else slug
    quiz = _QUIZ_CACHE.get(key) or _QUIZ_CACHE.get(slug)
    if quiz and quiz.get("porcentaje_aprobacion") is not None:
        return int(quiz["porcentaje_aprobacion"])
    return 70


def listar_lecciones_db() -> list[dict]:
    rows = db.session.scalars(
        select(CatalogLesson).order_by(CatalogLesson.curso_slug, CatalogLesson.orden)
    ).all()
    out = []
    for l in rows:
        curso = db.session.get(CatalogCourse, l.curso_slug)
        out.append(
            {
                "id": l.id,
                "leccion_id": l.leccion_id,
                "curso_slug": l.curso_slug,
                "curso": curso.titulo if curso else l.curso_slug,
                "titulo": l.titulo,
                "duracion": l.duracion,
                "orden": l.orden,
                "activo": l.activo,
            }
        )
    return out
