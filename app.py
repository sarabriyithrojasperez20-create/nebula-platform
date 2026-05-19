# -*- coding: utf-8 -*-
"""
Aplicación principal de Nébula (Flask).

Registra rutas HTTP, sesiones de usuario, panel de estudiante y administrador,
APIs JSON y la integración con catálogo académico, progreso, tutor IA y datos locales.
Punto de entrada local: ``python app.py`` (o ``py app.py`` en Windows).
"""

import logging

import nebula_config
from nebula_config import log_estado_openai, openai_configurado

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory, Response, stream_with_context
import copy
import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from urllib.parse import urlencode, urlparse

from lecciones_contenido import obtener_contenido_leccion
from diagnosticos_contenido import (
    aplicar_ruta_diagnostico_a_curso,
    evaluar_respuestas_diagnostico,
    obtener_diagnostico_curso,
    resolver_leccion_actual_con_ruta,
    TITULOS_NIVEL,
    MENSAJES_NIVEL,
)
from grado_materias_service import (
    etiqueta_grado,
    resolver_grado_registro,
)
from racha_diaria_service import (
    obtener_estado_racha,
    obtener_resumen_racha,
    preparar_racha_plan_estudios,
    registrar_actividad_automatica,
    registrar_actividad_racha,
    sincronizar_desde_fuentes_sistema,
    sincronizar_y_validar_hoy,
)

# Inicializa Flask y la clave de sesión (SECRET_KEY / FLASK_SECRET_KEY en .env).
app = Flask(__name__)
app.secret_key = (
    os.getenv("SECRET_KEY") or os.getenv("FLASK_SECRET_KEY") or "dev-nebula-cambiar-en-produccion"
)

# Motor SQLAlchemy: SQLite local o PostgreSQL según DATABASE_URL (ver db.py).
from db import RENDER_DATABASE_DEFAULT, apply_sqlalchemy_config

apply_sqlalchemy_config(app, default_url=RENDER_DATABASE_DEFAULT or None)

from nebula_data import cargar_datos, guardar_datos, generar_id, init_data_layer

init_data_layer(app)


# Antes de cada petición: normaliza claves de rol en cookies de sesión antiguas.
@app.before_request
def _nebula_repair_session():
    from session_auth import repair_session_role_keys

    repair_session_role_keys()


AVATAR_ESTUDIANTE_DEFAULT = (
    "https://lh3.googleusercontent.com/aida-public/AB6AXuBlwoGAr4OcQHRwHR-lcqSiVtRczHOqU4jSeFWxNy7vEHCCeSC_b1mKIRSSHlj-Uah3OA6pbCC0gL6OOi-k9lVNngXgPGI8SMaNT5qfa2MvmU_9BDlAs2sFfycz7MTtG1JhdpkytvtTvG0qlm796rX77xURSs3c0qR1vFJfRms9-GFoWgsllXenDXJ4WbdK-n98_bzU82KSmO2gh53b7AdV-AawOUYUnwE3qSGyNOAiyNmiNSUmRB79gyWgUowkW0vRWKOHp2m4EFo"
)

AVATAR_ADMIN_DEFAULT = (
    "https://lh3.googleusercontent.com/aida-public/AB6AXuAD6gE4jiVX_QOu_PJnl4RoiCuFtEVvl9zCo9MjQ-6uWcAni9hqFLMcI20-1qtdN9Q_xdVtZe05nF7Tlb6ausQOLPV6C1ehxI3Juo6jIIyt19DjM33_aq6eO5-l35Kz2AFteSqdTMTR3Zmp7iAYn60YTj-cA3gb1nSVquColSTkQmpq19qftiFfA2gTl1Z188WVEIvsp4Eo0t0ugfLEL9wZg7-Gdmo_49YAbnCDVSHyiBwV4CnWdJFFpZhHm_Y6WsxL54wboT6QzAU"
)


@app.context_processor
def inyectar_perfil_estudiante():
    """Avatar y datos de perfil en vistas de estudiante (rol 2) y administrador (rol 1)."""
    if "id_usuario" not in session:
        return {
            "nebula_avatar_url": "",
            "nebula_profile_boot": None,
        }
    from session_auth import session_rol

    rol = session_rol()
    if rol not in (1, 2):
        return {
            "nebula_avatar_url": "",
            "nebula_avatar_default": "",
            "nebula_profile_boot": None,
        }
    default_avatar = AVATAR_ADMIN_DEFAULT if rol == 1 else AVATAR_ESTUDIANTE_DEFAULT
    usuario = obtener_usuario_sesion()
    if not usuario:
        return {
            "nebula_avatar_url": default_avatar,
            "nebula_avatar_default": default_avatar,
            "nebula_profile_boot": None,
        }
    from perfil_service import normalizar_usuario_perfil

    usuario = normalizar_usuario_perfil(usuario)
    avatar_url = _avatar_url_usuario(usuario) or default_avatar
    prefs = usuario.get("preferencias_aprendizaje") or {}
    return {
        "nebula_avatar_url": avatar_url,
        "nebula_avatar_default": default_avatar,
        "nebula_menu_username": usuario.get("username", ""),
        "nebula_profile_boot": {
            "avatarDefault": default_avatar,
            "avatarUrl": avatar_url,
            "rol": rol,
            "foto_version": usuario.get("foto_actualizada_en", ""),
            "id_usuario": usuario.get("id_usuario"),
            "user": {
                "id_usuario": usuario.get("id_usuario"),
                "nombre_completo": usuario.get("nombre_completo", ""),
                "username": usuario.get("username", ""),
                "correo": usuario.get("correo", ""),
                "sobre_mi": usuario.get("sobre_mi", ""),
                "nivel_academico": usuario.get("nivel_academico", ""),
                "grado": usuario.get("grado", ""),
                "preferencia_dominante": prefs.get("dominante", "visual"),
                "avatar_url": avatar_url,
                "foto_actualizada_en": usuario.get("foto_actualizada_en", ""),
            },
        },
    }

DATA_DIR = "data"

ARCHIVOS = {
    "roles": "roles.json",
    "usuarios": "usuarios.json",
    "cursos": "cursos.json",
    "lecciones": "lecciones.json",
    "progreso": "progreso.json",
    "actividades": "actividades.json",
    "comentarios": "comentarios.json",
    "progreso_catalogo": "progreso_catalogo.json",
    "cursos_asignados": "cursos_asignados.json",
    "diagnosticos_catalogo": "diagnosticos_catalogo.json",
    "resultados_quiz": "resultados_quiz.json",
    "actividad_sistema": "actividad_sistema.json",
}


def registrar_actividad_sistema(tipo, id_usuario, titulo, descripcion):
    actividades = cargar_datos("actividad_sistema")
    actividades.append(
        {
            "id_actividad": generar_id(actividades, "id_actividad"),
            "tipo": tipo,
            "id_usuario": id_usuario,
            "titulo": titulo,
            "descripcion": descripcion,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
    )
    guardar_datos("actividad_sistema", actividades[-120:])
    try:
        from notificaciones_admin_service import notificar_desde_actividad_sistema

        notificar_desde_actividad_sistema(tipo, id_usuario, titulo, descripcion)
    except Exception:
        app.logger.exception("notificacion_admin desde actividad_sistema")


def guardar_resultado_quiz(
    id_usuario, slug, leccion_id, porcentaje, correctas, total, aprobado
):
    curso = obtener_curso_catalogo(slug)
    leccion = obtener_leccion_curso(curso, leccion_id) if curso else None
    registros = cargar_datos("resultados_quiz")
    intento = sum(
        1
        for r in registros
        if r.get("id_usuario") == id_usuario
        and r.get("slug") == slug
        and r.get("leccion_id") == leccion_id
    ) + 1

    registro = {
        "id_resultado": generar_id(registros, "id_resultado"),
        "id_usuario": id_usuario,
        "slug": slug,
        "leccion_id": leccion_id,
        "titulo_curso": curso["titulo"] if curso else slug,
        "titulo_leccion": leccion["titulo"] if leccion else leccion_id,
        "porcentaje": porcentaje,
        "correctas": correctas,
        "total": total,
        "aprobado": aprobado,
        "intento": intento,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    registros.append(registro)
    guardar_datos("resultados_quiz", registros)

    nombre = session.get("nombre", "Un estudiante")
    if aprobado:
        registrar_actividad_sistema(
            "quiz_aprobado",
            id_usuario,
            "Quiz final aprobado",
            f"{nombre} aprobó el quiz de {registro['titulo_leccion']} ({porcentaje}%)",
        )
        registrar_actividad_automatica(
            id_usuario,
            "quiz",
            {
                "slug": slug,
                "leccion_id": leccion_id,
                "porcentaje": porcentaje,
            },
        )
    else:
        registrar_actividad_sistema(
            "quiz_no_aprobado",
            id_usuario,
            "Quiz final no aprobado",
            f"{nombre} obtuvo {porcentaje}% en {registro['titulo_leccion']}",
        )
    if aprobado:
        from progreso_service import (
            persistir_fecha_progreso,
            sincronizar_progreso_materias_usuario,
        )

        persistir_fecha_progreso(id_usuario, slug)
        sincronizar_progreso_materias_usuario(id_usuario)
    return registro


def obtener_usuario_sesion():
    if "id_usuario" not in session:
        return None

    usuarios = cargar_datos("usuarios")

    for usuario in usuarios:
        if usuario["id_usuario"] == session["id_usuario"]:
            return usuario

    return None


MATERIA_POR_SLUG = {
    "fundamentos-algebra": "matematicas",
    "probabilidad-estadistica": "matematicas",
    "algoritmos-logica": "matematicas",
    "biologia-molecular": "ciencias",
    "fisica-cuantica-1": "ciencias",
    "quimica-organica": "ciencias",
}

ORDEN_CURSOS_CATALOGO = [
    "fundamentos-algebra",
    "biologia-molecular",
    "fisica-cuantica-1",
    "quimica-organica",
    "probabilidad-estadistica",
    "algoritmos-logica",
]

CURSOS_CATALOGO = {
    "fundamentos-algebra": {
        "id_curso": 1,
        "slug": "fundamentos-algebra",
        "titulo": "Fundamentos de álgebra",
        "nivel": "Intermedio",
        "porcentaje": 65,
        "duracion_total": "24 h estimadas",
        "descripcion": "Domine los conceptos básicos de ecuaciones lineales, funciones cuadráticas y operaciones polinomiales.",
        "imagen": "https://lh3.googleusercontent.com/aida-public/AB6AXuDGkQThWwMQkcWtnvjICj0vx0E_Fw1NRL7pu_32QKMccsL-k-5sb9HqcWWh0w9zXpp2O6OQNJkfOPMpxUMIqA7Sndn7-z1HBhNKBXVEJ0qVklDR6-_dcJP_-Qg7iEr5Ya7Azn2qrKbLqQBGZb7h1Tbbc6Qy8zXY0QH1itKxtU1AyKOhRwk2nbQHL-XCGEtyxfTlmpQKqosKfP7aeKEcquBzdW-N14yb_QGp5OCeBHs5mOWqB9lWaAHRbVz1nLL4F1bTh0BR-YNe0aA",
        "temas": [
            "Ecuaciones lineales",
            "Funciones cuadráticas",
            "Operaciones polinomiales",
            "Factorización y productos notables",
        ],
        "modulos": [
            "Módulo 1: Ecuaciones y desigualdades",
            "Módulo 2: Funciones y gráficas",
            "Módulo 3: Polinomios y factorización",
        ],
        "lecciones": [
            {"id": "intro-ecuaciones-lineales", "titulo": "Introducción a ecuaciones lineales", "duracion": "35 min", "estado": "completado"},
            {"id": "sistemas-ecuaciones-2x2", "titulo": "Sistemas de ecuaciones 2x2", "duracion": "45 min", "estado": "completado"},
            {"id": "funciones-cuadraticas", "titulo": "Funciones cuadráticas: vértice y raíces", "duracion": "50 min", "estado": "en_progreso"},
            {"id": "operaciones-polinomios", "titulo": "Operaciones con polinomios", "duracion": "40 min", "estado": "pendiente"},
        ],
    },
    "biologia-molecular": {
        "id_curso": 2,
        "slug": "biologia-molecular",
        "titulo": "Biología molecular",
        "nivel": "Avanzado",
        "porcentaje": 30,
        "duracion_total": "32 h estimadas",
        "descripcion": "Sumérjase en la estructura profunda del ADN, la síntesis de proteínas y los mecanismos celulares.",
        "imagen": "https://lh3.googleusercontent.com/aida-public/AB6AXuCJ8irHUvD4ESpzBD5gPZnckC_o9J3IGN1RKez2QTlkpIFGhSE-DlGBywd6aOAsi0El310qpLA59X2Di9eIwcFgANFYVPKCYH0ZXp0EpJFIojb1jZFgKIqHe-BLet-wE2RwzAA3POLLJg02Krq6gm-0kXg1ePz9zcQlsrlOMI2g8qSzDk3j5HJtKa6g_e7g1TOWBtPNj0iY9KKWtKWTITgcm0vc_gLm198YEPcdRefc44q4gK109buEWkiWm-ve-dv6U4bAi8hAejw",
        "temas": [
            "Estructura del ADN y ARN",
            "Síntesis de proteínas",
            "Mecanismos celulares",
            "Regulación génica",
        ],
        "modulos": [
            "Módulo 1: Ácidos nucleicos",
            "Módulo 2: Expresión génica",
            "Módulo 3: Biología celular avanzada",
        ],
        "lecciones": [
            {"id": "doble-helice-replicacion", "titulo": "Doble hélice y replicación", "duracion": "55 min", "estado": "completado"},
            {"id": "estructura-adn", "titulo": "Estructura del ADN", "duracion": "60 min", "estado": "en_progreso"},
            {"id": "organulos-metabolismo", "titulo": "Orgánulos y metabolismo celular", "duracion": "45 min", "estado": "pendiente"},
            {"id": "mutaciones-expresion", "titulo": "Mutaciones y expresión génica", "duracion": "50 min", "estado": "pendiente"},
        ],
    },
    "fisica-cuantica-1": {
        "id_curso": 3,
        "slug": "fisica-cuantica-1",
        "titulo": "Física cuántica I",
        "nivel": "Principiante",
        "porcentaje": 85,
        "duracion_total": "28 h estimadas",
        "descripcion": "Introducción a la dualidad onda-partícula, los principios de incertidumbre y la física moderna.",
        "imagen": "https://lh3.googleusercontent.com/aida-public/AB6AXuC17LSLL3cZZ3nOJXIgmlREGNUYMFpredU0BHUos578LKTO8k5qrUxV1ybalAd_XQyK4jH_We8WVA6gvSBcvRBAbKH4RA01QPUtCcElR8FgIMHRi_7NxgZGTOW-h1yYANp7sE1o6i9L12BKWV4WLIPmCDdsN_vQ_rtka_6ogYOR1xDt1_c97uV5BT8HMfWn_bjMkqGOql1ivNjoPynoWKynvcHz_olWan1H2FM06aEpPQ3hw-F7VOQBljAl9QVA9ZHUot5kwKPIG-g",
        "temas": [
            "Dualidad onda-partícula",
            "Principio de incertidumbre",
            "Función de onda",
            "Introducción a la mecánica cuántica",
        ],
        "modulos": [
            "Módulo 1: Orígenes de la física cuántica",
            "Módulo 2: Formalismo básico",
            "Módulo 3: Aplicaciones introductorias",
        ],
        "lecciones": [
            {"id": "luz-naturaleza-cuantica", "titulo": "Luz y naturaleza cuántica", "duracion": "40 min", "estado": "completado"},
            {"id": "experimento-doble-rendija", "titulo": "Experimento de la doble rendija", "duracion": "45 min", "estado": "completado"},
            {"id": "heisenberg-medicion", "titulo": "Heisenberg y límites de medición", "duracion": "50 min", "estado": "completado"},
            {"id": "dualidad-onda-particula", "titulo": "Dualidad onda-partícula", "duracion": "55 min", "estado": "en_progreso"},
        ],
    },
    "quimica-organica": {
        "id_curso": 4,
        "slug": "quimica-organica",
        "titulo": "Química orgánica",
        "nivel": "Intermedio",
        "porcentaje": 50,
        "duracion_total": "26 h estimadas",
        "descripcion": "Comprenda los compuestos de carbono, los grupos funcionales y las vías de reacción complejas.",
        "imagen": "https://lh3.googleusercontent.com/aida-public/AB6AXuDhWd9jJNPm7Vbo1iOxLBG-gUMScrQXhZiEh8A3LL6glN97JS31lE5bcZ7edT7ZoSlBnoVajHWrtd-REdh50Mc6ZnVwyTvtimNue-qI-LLP4QXoL7IVbXWf4ubHeIcrmL0RQPT1edYlsg8pWROHb3HvziJlP2BHDWOkVILGcQRs-LQhOQydQh_XmzGwbB-YYnnHNUOqihUtLmWmgYkn1VfxfkwOpwn1q0cWnp-lXS3PRrmCBvrZHJwTF7nYx8NLX8ihkKCQb5xpsZc",
        "temas": [
            "Hibridación del carbono",
            "Grupos funcionales",
            "Reacciones orgánicas básicas",
            "Estereoquímica introductoria",
        ],
        "modulos": [
            "Módulo 1: Fundamentos del carbono",
            "Módulo 2: Grupos funcionales",
            "Módulo 3: Mecanismos de reacción",
        ],
        "lecciones": [
            {"id": "enlaces-geometria", "titulo": "Enlaces y geometría molecular", "duracion": "42 min", "estado": "completado"},
            {"id": "alcanos-alquenos", "titulo": "Alcanos, alquenos y alquinos", "duracion": "48 min", "estado": "completado"},
            {"id": "alcoholes-eteres", "titulo": "Alcoholes y éteres", "duracion": "45 min", "estado": "en_progreso"},
            {"id": "acidos-carboxilicos", "titulo": "Ácidos carboxílicos y ésteres", "duracion": "50 min", "estado": "pendiente"},
        ],
    },
    "probabilidad-estadistica": {
        "id_curso": 5,
        "slug": "probabilidad-estadistica",
        "titulo": "Probabilidad y estadística",
        "nivel": "Principiante",
        "porcentaje": 10,
        "duracion_total": "22 h estimadas",
        "descripcion": "Aprenda a interpretar datos, comprender distribuciones y dominar el análisis predictivo.",
        "imagen": "https://lh3.googleusercontent.com/aida-public/AB6AXuA5pFThclnKc6zR8EfeaMy4hhba39HRFKgrX3SBKTzdH3iRV2uXGbn_HNm3Sb30xdu_LRmTjt6l16lTyx-ZqY0gt6K95_5tQdbg2gy1OBsv9WZJoNr7JqkTTddEWPgUYDAkwtTCY99MQuil9aZbJ1n2x3_Hd00qS_U8f8jUCCBQXUY5lU879_5JVTmpVrLz7QxNoxR5CnD0hNhu8wTebsvbVhLmt97OEnyHeCH16mE-rwhpN5It6dXW8rAxvosJbPghccHCh-DvtsE",
        "temas": [
            "Probabilidad básica",
            "Distribuciones",
            "Muestreo y inferencia",
            "Análisis predictivo",
        ],
        "modulos": [
            "Módulo 1: Fundamentos de probabilidad",
            "Módulo 2: Estadística descriptiva",
            "Módulo 3: Inferencia estadística",
        ],
        "lecciones": [
            {"id": "eventos-espacios", "titulo": "Eventos y espacios muestrales", "duracion": "38 min", "estado": "en_progreso"},
            {"id": "variables-aleatorias", "titulo": "Variables aleatorias", "duracion": "45 min", "estado": "pendiente"},
            {"id": "media-mediana-desviacion", "titulo": "Media, mediana y desviación", "duracion": "40 min", "estado": "pendiente"},
            {"id": "regresion-lineal", "titulo": "Regresión lineal introductoria", "duracion": "52 min", "estado": "pendiente"},
        ],
    },
    "algoritmos-logica": {
        "id_curso": 6,
        "slug": "algoritmos-logica",
        "titulo": "Algoritmos y lógica",
        "nivel": "Intermedio",
        "porcentaje": 95,
        "duracion_total": "30 h estimadas",
        "descripcion": "Domine técnicas de resolución de problemas y la lógica central del pensamiento computacional.",
        "imagen": "https://lh3.googleusercontent.com/aida-public/AB6AXuDi882re3abGI3lK6Y0XSqpK75bFv-c-4DBPhsJtufz1flJ9b3qgpAe8F1XkONlGiAg70uUCsRjmCZS-CoHDFRgqH139EZwNtEhYiNjM7pT8bS7fVH3CsFLfGk2GNuWXNdqLBVGGAYQyt8d0Uh17OYIJFRNVeeBw7zoKrk7UU34J8slglGhFtPNpz_WeM57_xrk5aM0rRRYn_i23jcr1L0thfYn_EbsMzweIv2rhv7GVwVYtf8DaF4Ux_1y_IbWQ8FEgd9IXm_oDt4",
        "temas": [
            "Pensamiento algorítmico",
            "Estructuras de control",
            "Complejidad introductoria",
            "Resolución de problemas",
        ],
        "modulos": [
            "Módulo 1: Lógica y pseudocódigo",
            "Módulo 2: Algoritmos clásicos",
            "Módulo 3: Optimización básica",
        ],
        "lecciones": [
            {"id": "diagramas-flujo", "titulo": "Diagramas de flujo", "duracion": "35 min", "estado": "completado"},
            {"id": "busqueda-ordenamiento", "titulo": "Búsqueda y ordenamiento", "duracion": "55 min", "estado": "completado"},
            {"id": "recursion-intro", "titulo": "Recursión introductoria", "duracion": "48 min", "estado": "completado"},
            {"id": "complejidad-on", "titulo": "Análisis de complejidad O(n)", "duracion": "50 min", "estado": "en_progreso"},
        ],
    },
}


def obtener_curso_catalogo(slug):
    curso = CURSOS_CATALOGO.get(slug)
    if not curso:
        return None
    try:
        from catalog_service import curso_activo

        if not curso_activo(slug):
            return None
    except Exception:
        pass
    return curso


def obtener_slugs_cursos_asignados(id_usuario):
    asignaciones = cargar_datos("cursos_asignados")
    return [
        item["slug"]
        for item in asignaciones
        if item.get("id_usuario") == id_usuario and item.get("slug") in CURSOS_CATALOGO
    ]


def usuario_tiene_curso_asignado(id_usuario, slug):
    return slug in obtener_slugs_cursos_asignados(id_usuario)


def asignar_curso_a_usuario(id_usuario, slug):
    if not obtener_curso_catalogo(slug):
        return False

    asignaciones = cargar_datos("cursos_asignados")
    if usuario_tiene_curso_asignado(id_usuario, slug):
        return True

    asignaciones.append(
        {
            "id_asignacion": generar_id(asignaciones, "id_asignacion"),
            "id_usuario": id_usuario,
            "slug": slug,
            "fecha_asignacion": datetime.now().strftime("%Y-%m-%d"),
        }
    )
    guardar_datos("cursos_asignados", asignaciones)
    curso = obtener_curso_catalogo(slug)
    titulo = curso["titulo"] if curso else slug
    registrar_actividad_sistema(
        "curso_anadido",
        id_usuario,
        "Curso añadido",
        f"{session.get('nombre', 'Estudiante')} añadió el curso {titulo}",
    )
    return True


def serializar_curso_activo(curso: dict) -> dict:
    """Payload JSON para selector CURSO / MATERIA y APIs de cursos activos."""
    slug = (curso.get("slug") or "").strip()
    return {
        "slug": slug,
        "titulo": curso.get("titulo") or slug,
        "materia": curso.get("materia") or MATERIA_POR_SLUG.get(slug, "todas"),
        "nivel": curso.get("nivel") or "",
        "imagen": curso.get("imagen") or "",
        "url": url_for("detalle_curso", slug=slug) if slug else "",
    }


def listar_cursos_activos_serializados(id_usuario: int) -> list[dict]:
    return [serializar_curso_activo(c) for c in listar_cursos_catalogo_usuario(id_usuario)]


def listar_cursos_catalogo_usuario(id_usuario):
    cursos = []
    slugs_asignados = obtener_slugs_cursos_asignados(id_usuario)
    diagnosticos_map = obtener_mapa_diagnosticos_usuario(id_usuario)
    for slug in ORDEN_CURSOS_CATALOGO:
        if slug not in slugs_asignados:
            continue
        base = CURSOS_CATALOGO.get(slug)
        if not base:
            continue
        curso = preparar_curso_para_tarjeta(base, id_usuario)
        curso["diagnostico_completado"] = slug in diagnosticos_map
        if slug in diagnosticos_map:
            d = diagnosticos_map[slug]
            curso["diagnostico_nivel"] = d.get("nivel")
            curso["diagnostico_titulo_nivel"] = d.get("titulo_nivel", "")
        cursos.append(curso)
    return cursos


def obtener_diagnostico_usuario(id_usuario, slug):
    registros = cargar_datos("diagnosticos_catalogo")
    for registro in registros:
        if registro.get("id_usuario") == id_usuario and registro.get("slug") == slug:
            return registro
    return None


def usuario_completo_diagnostico(id_usuario, slug):
    return obtener_diagnostico_usuario(id_usuario, slug) is not None


def guardar_diagnostico_usuario(id_usuario, slug, resultado_evaluacion):
    registros = cargar_datos("diagnosticos_catalogo")
    existente = obtener_diagnostico_usuario(id_usuario, slug)

    payload = {
        "id_usuario": id_usuario,
        "slug": slug,
        "nivel": resultado_evaluacion["nivel"],
        "titulo_nivel": TITULOS_NIVEL.get(resultado_evaluacion["nivel"], ""),
        "porcentaje": resultado_evaluacion["porcentaje"],
        "correctas": resultado_evaluacion["correctas"],
        "total": resultado_evaluacion["total"],
        "errores_por_leccion": resultado_evaluacion["errores_por_leccion"],
        "detalle": resultado_evaluacion["detalle"],
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    if existente:
        payload["id_diagnostico"] = existente["id_diagnostico"]
        for i, reg in enumerate(registros):
            if reg.get("id_diagnostico") == existente["id_diagnostico"]:
                registros[i] = payload
                break
    else:
        payload["id_diagnostico"] = generar_id(registros, "id_diagnostico")
        registros.append(payload)

    guardar_datos("diagnosticos_catalogo", registros)

    curso = obtener_curso_catalogo(slug)
    titulo_curso = curso["titulo"] if curso else slug
    registrar_actividad_sistema(
        "diagnostico_completado",
        id_usuario,
        "Diagnóstico completado",
        f"{session.get('nombre', 'Estudiante')} completó el diagnóstico de {titulo_curso} ({payload.get('titulo_nivel', '')})",
    )
    registrar_actividad_automatica(
        id_usuario,
        "evaluacion",
        {"slug": slug, "nivel": payload.get("nivel"), "porcentaje": payload.get("porcentaje")},
    )
    from progreso_service import sincronizar_progreso_materias_usuario

    sincronizar_progreso_materias_usuario(id_usuario)
    return payload


def obtener_mapa_diagnosticos_usuario(id_usuario):
    registros = cargar_datos("diagnosticos_catalogo")
    return {
        r["slug"]: r
        for r in registros
        if r.get("id_usuario") == id_usuario
    }


def preparar_curso_para_tarjeta(curso_base, id_usuario):
    curso = aplicar_progreso_a_curso(copy.deepcopy(curso_base), id_usuario)
    slug = curso.get("slug")
    curso["materia"] = MATERIA_POR_SLUG.get(slug, "todas")
    porcentaje = curso.get("porcentaje", 0)
    curso["stroke_dashoffset"] = max(0, min(100, 100 - porcentaje))
    return curso


def listar_catalogo_general():
    catalogo = []
    for slug in ORDEN_CURSOS_CATALOGO:
        base = obtener_curso_catalogo(slug)
        if base:
            catalogo.append(copy.deepcopy(base))
    return catalogo


def obtener_actividades_usuario(id_usuario, tipo=None):
    actividades = cargar_datos("actividades")
    resultado = [
        actividad
        for actividad in actividades
        if actividad.get("id_usuario") == id_usuario
    ]
    if tipo:
        resultado = [a for a in resultado if a.get("tipo") == tipo]
    return resultado


def obtener_usuario_por_id(id_usuario):
    for usuario in cargar_datos("usuarios"):
        if usuario.get("id_usuario") == id_usuario:
            return usuario
    return None


def _cursos_calendario_para_usuario(id_usuario):
    return [
        {"slug": c["slug"], "titulo": c.get("titulo") or c["slug"]}
        for c in listar_cursos_catalogo_usuario(id_usuario)
    ]


def _slugs_cursos_asignados_set(id_usuario):
    return set(obtener_slugs_cursos_asignados(id_usuario))


def _resolver_leccion_evento(id_usuario, slug, curso_base):
    curso = preparar_curso_para_tarjeta(curso_base, id_usuario)
    if not curso:
        return None
    leccion = resolver_leccion_actual(curso)
    return leccion.get("id") if leccion else None


def _json_destino_evento(id_usuario, evento):
    from calendario_service import enriquecer_eventos_con_cursos, resolver_destino_curso

    slugs = _slugs_cursos_asignados_set(id_usuario)
    catalogo = {s: CURSOS_CATALOGO[s] for s in slugs if s in CURSOS_CATALOGO}
    enriquecer_eventos_con_cursos([evento], {s: {"titulo": catalogo[s].get("titulo")} for s in catalogo})
    destino = resolver_destino_curso(
        evento,
        slugs,
        catalogo,
        lambda slug, curso: _resolver_leccion_evento(id_usuario, slug, curso),
    )
    if not destino.get("disponible"):
        return {
            "ok": True,
            "disponible": False,
            "mensaje": destino.get("mensaje") or "Curso no disponible",
            "evento": evento,
        }
    slug = destino["curso_slug"]
    leccion_id = destino.get("leccion_id")
    fragment = destino.get("fragment") or ""
    query = destino.get("query") or {}
    if leccion_id:
        url = url_for("ver_leccion", slug=slug, leccion_id=leccion_id)
    else:
        url = url_for("detalle_curso", slug=slug)
    if query:
        url += "?" + urlencode(query)
    url += fragment
    return {
        "ok": True,
        "disponible": True,
        "url": url,
        "curso_slug": slug,
        "curso_titulo": destino.get("curso_titulo"),
        "leccion_id": leccion_id,
        "evento": evento,
        "mensaje": None,
    }


def obtener_datos_dashboard(id_usuario):
    from calendario_service import (
        enriquecer_eventos_con_cursos,
        eventos_proximos_evaluaciones,
        listar_eventos_usuario,
    )
    from progreso_service import obtener_resumen_progreso_usuario

    resumen_prog = obtener_resumen_progreso_usuario(id_usuario)
    cursos = listar_cursos_catalogo_usuario(id_usuario)
    clases_activas = resumen_prog.get("clases_activas") or []
    cursos_cal = _cursos_calendario_para_usuario(id_usuario)
    cursos_map = {c["slug"]: c for c in cursos_cal}
    actividades = cargar_datos("actividades")
    eventos_cal = listar_eventos_usuario(actividades, id_usuario)
    enriquecer_eventos_con_cursos(eventos_cal, cursos_map)
    evaluaciones = obtener_actividades_usuario(id_usuario, "evaluacion")
    eval_cal = eventos_proximos_evaluaciones(eventos_cal)
    if eval_cal:
        evaluaciones = eval_cal + [
            e for e in evaluaciones
            if not any(x.get("titulo") == e.get("titulo") for x in eval_cal)
        ]
    for ev in evaluaciones:
        if isinstance(ev, dict) and ev.get("fecha"):
            from calendario_service import etiqueta_countdown, etiqueta_tipo_evento

            ev.setdefault("countdown", etiqueta_countdown(ev.get("fecha")))
            ev.setdefault(
                "tipo_label",
                etiqueta_tipo_evento(ev.get("categoria") or "evaluacion"),
            )
    materias_calendario = cursos_cal
    return {
        "clases_activas": clases_activas,
        "evaluaciones": evaluaciones[:6],
        "tiene_cursos": len(cursos) > 0,
        "eventos_calendario": eventos_cal,
        "materias_calendario": materias_calendario,
        "cursos_calendario": cursos_cal,
        "progreso_resumen": resumen_prog,
    }


def obtener_datos_progreso_usuario(id_usuario):
    from progreso_service import obtener_resumen_progreso_usuario

    resumen = obtener_resumen_progreso_usuario(id_usuario)
    cursos = listar_cursos_catalogo_usuario(id_usuario)
    return {
        "cursos": cursos,
        "lecciones_completadas": resumen.get("lecciones_completadas", 0),
        "tiene_cursos": len(cursos) > 0,
        "promedio_general": resumen.get("promedio_general", 0),
        "cursos_completados": resumen.get("cursos_completados", 0),
        "tendencia": resumen.get("tendencia", []),
    }


def obtener_items_busqueda_progreso(id_usuario):
    """Filas de evaluaciones y lecciones del usuario para el buscador de Progreso."""
    items = []
    for curso in listar_cursos_catalogo_usuario(id_usuario):
        items.append(
            {
                "tipo": "curso",
                "titulo": curso.get("titulo", ""),
                "detalle": f"{curso.get('nivel', '')} · {curso.get('porcentaje', 0)}% avance",
                "texto": f"{curso.get('descripcion', '')} {curso.get('materia', '')}",
            }
        )
        for lec in curso.get("lecciones") or []:
            estado = lec.get("estado", "pendiente")
            items.append(
                {
                    "tipo": "leccion",
                    "titulo": lec.get("titulo", lec.get("id", "")),
                    "detalle": curso.get("titulo", ""),
                    "texto": f"leccion {estado} {lec.get('duracion', '')}",
                }
            )
    for reg in cargar_datos("resultados_quiz"):
        if reg.get("id_usuario") != id_usuario:
            continue
        aprob = reg.get("aprobado")
        items.append(
            {
                "tipo": "evaluacion",
                "titulo": reg.get("titulo_leccion") or reg.get("leccion_id", "Evaluación"),
                "detalle": f"{reg.get('slug', '')} · {reg.get('porcentaje', 0)}%",
                "texto": "aprobado" if aprob else "no aprobado",
            }
        )
    return items


def obtener_leccion_curso(curso, leccion_id):
    for leccion in curso.get("lecciones", []):
        if leccion.get("id") == leccion_id:
            return leccion
    return None


def resolver_leccion_actual(curso):
    for leccion in curso["lecciones"]:
        if leccion["estado"] == "en_progreso":
            return leccion
    for leccion in curso["lecciones"]:
        if leccion["estado"] == "pendiente":
            return leccion
    if curso["lecciones"]:
        return curso["lecciones"][0]
    return None


def obtener_registro_progreso_catalogo(id_usuario, slug, registros=None):
    if registros is None:
        registros = cargar_datos("progreso_catalogo")
    for registro in registros:
        if registro.get("id_usuario") == id_usuario and registro.get("slug") == slug:
            return registro
    return None


def obtener_lecciones_completadas_usuario(id_usuario, slug):
    registro = obtener_registro_progreso_catalogo(id_usuario, slug)
    if not registro:
        return set()
    return set(registro.get("lecciones_completadas", []))


def aplicar_progreso_a_curso(curso, id_usuario):
    from progreso_service import aplicar_progreso_calculado

    return aplicar_progreso_calculado(curso, id_usuario)


def obtener_siguiente_leccion(curso, leccion_id):
    lecciones = curso.get("lecciones", [])
    for indice, leccion in enumerate(lecciones):
        if leccion.get("id") == leccion_id and indice + 1 < len(lecciones):
            return lecciones[indice + 1]
    return None


def marcar_leccion_catalogo_completada(id_usuario, slug, leccion_id):
    if not usuario_tiene_curso_asignado(id_usuario, slug):
        return None

    curso = obtener_curso_catalogo(slug)
    if not curso or not obtener_leccion_curso(curso, leccion_id):
        return None

    registros = cargar_datos("progreso_catalogo")
    registro = obtener_registro_progreso_catalogo(id_usuario, slug, registros)

    if registro:
        completadas = set(registro.get("lecciones_completadas", []))
        completadas.add(leccion_id)
        registro["lecciones_completadas"] = list(completadas)
        registro["fecha_actualizacion"] = datetime.now().strftime("%Y-%m-%d")
    else:
        registro = {
            "id_progreso_catalogo": generar_id(registros, "id_progreso_catalogo"),
            "id_usuario": id_usuario,
            "slug": slug,
            "lecciones_completadas": [leccion_id],
            "fecha_actualizacion": datetime.now().strftime("%Y-%m-%d"),
        }
        registros.append(registro)

    guardar_datos("progreso_catalogo", registros)

    from progreso_service import persistir_fecha_progreso, sincronizar_progreso_materias_usuario

    persistir_fecha_progreso(id_usuario, slug)
    sincronizar_progreso_materias_usuario(id_usuario)

    leccion = obtener_leccion_curso(curso, leccion_id)
    registrar_actividad_sistema(
        "leccion_completada",
        id_usuario,
        "Lección completada",
        f"{session.get('nombre', 'Estudiante')} completó {(leccion or {}).get('titulo', leccion_id)}",
    )
    registrar_actividad_automatica(
        id_usuario,
        "leccion",
        {"slug": slug, "leccion_id": leccion_id},
    )

    curso_actualizado = aplicar_progreso_a_curso(curso, id_usuario)
    if curso_actualizado.get("porcentaje", 0) >= 100:
        try:
            from notificaciones_admin_service import crear_notificacion_admin

            crear_notificacion_admin(
                "curso_completado",
                f"{_nombre_usuario_notif(id_usuario)} completó el curso {curso_actualizado.get('titulo', slug)}",
                titulo="Curso completado",
                id_usuario=id_usuario,
            )
        except Exception:
            pass
    siguiente = obtener_siguiente_leccion(curso_actualizado, leccion_id)
    from progreso_service import calcular_progreso_curso

    stats = calcular_progreso_curso(curso_actualizado, id_usuario)
    return {
        "curso": curso_actualizado,
        "siguiente_leccion": siguiente,
        "progreso": stats,
    }


def _nombre_usuario_notif(id_usuario):
    u = obtener_usuario_por_id(id_usuario)
    return (u or {}).get("nombre_completo", "Un estudiante")


@app.route("/")
def inicio():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Gestiona el inicio de sesión: valida credenciales, crea la sesión Flask
    y redirige al panel de administrador (rol 1) o al dashboard del estudiante (rol 2).
    """
    if request.method == "POST":

        correo = request.form["correo"]
        password = request.form["password"]

        from auth_service import autenticar_por_correo

        usuario = autenticar_por_correo(correo, password)
        if usuario:
            from session_auth import sync_session_roles

            session["id_usuario"] = usuario["id_usuario"]
            session["nombre"] = usuario["nombre_completo"]
            session["username"] = usuario.get("username", "")
            sync_session_roles(int(usuario["id_rol"]))

            if usuario["id_rol"] == 1:
                return redirect(url_for("admin"))
            return redirect(url_for("dashboard"))

        return "Correo o contraseña incorrectos"

    return render_template("login.html")

@app.route("/crear_cuenta", methods=["GET", "POST"])
def crear_cuenta():

    if request.method == "POST":
        usuarios = cargar_datos("usuarios")
        grado = resolver_grado_registro(request.form.get("grado"))
        if not grado:
            return render_template("crear_cuenta.html"), 400

        from password_security import hash_password

        nuevo_usuario = {
            "id_usuario": generar_id(usuarios, "id_usuario"),
            "nombre_completo": request.form["nombre_completo"],
            "correo": request.form["correo"],
            "username": request.form["username"],
            "password": hash_password(request.form["password"]),
            "grado": grado,
            "nivel_academico": etiqueta_grado(grado),
            "id_rol": 2,
            "activo": True,
            "fecha_registro": datetime.now().strftime("%Y-%m-%d"),
            "foto_perfil": "",
            "progreso_materias": {},
        }

        usuarios.append(nuevo_usuario)
        guardar_datos("usuarios", usuarios)

        registrar_actividad_sistema(
            "registro_usuario",
            nuevo_usuario["id_usuario"],
            "Nuevo usuario registrado",
            f"{nuevo_usuario['nombre_completo']} se registró en la plataforma",
        )

        return redirect(url_for("login"))

    return render_template("crear_cuenta.html")

@app.route("/dashboard")
def dashboard():

    if "id_usuario" not in session:
        return redirect(url_for("login"))

    id_usuario = session["id_usuario"]
    try:
        datos_dashboard = obtener_datos_dashboard(id_usuario)
        resumen_racha = obtener_resumen_racha(id_usuario)
    except Exception:
        app.logger.exception("Error en /dashboard (id_usuario=%s)", id_usuario)
        raise

    usuario = obtener_usuario_por_id(id_usuario)
    try:
        from tutor_ai_service import es_usuario_pro
        from nebula_data import plan_de_usuario_dict

        es_pro = es_usuario_pro(usuario)
        plan_actual = plan_de_usuario_dict(usuario)
    except Exception:
        app.logger.exception("plan flags dashboard id=%s", id_usuario)
        es_pro = False
        plan_actual = "free"

    return render_template(
        "dashboard.html",
        nombre=session["nombre"],
        clases_activas=datos_dashboard["clases_activas"],
        evaluaciones=datos_dashboard["evaluaciones"],
        tiene_cursos=datos_dashboard["tiene_cursos"],
        eventos_calendario=datos_dashboard["eventos_calendario"],
        materias_calendario=datos_dashboard["materias_calendario"],
        cursos_calendario=datos_dashboard.get("cursos_calendario")
        or datos_dashboard["materias_calendario"],
        racha_actual=resumen_racha.get("racha_actual", 0),
        racha_actividad_hoy=resumen_racha.get("actividad_hoy", False),
        es_plan_pro=es_pro,
        plan_usuario=plan_actual,
    )


@app.route("/api/calendario/eventos", methods=["GET", "POST"])
def api_calendario_eventos():
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401

    from calendario_service import guardar_evento, listar_eventos_usuario

    id_usuario = session["id_usuario"]
    actividades = cargar_datos("actividades")

    if request.method == "GET":
        from calendario_service import enriquecer_eventos_con_cursos

        eventos = listar_eventos_usuario(actividades, id_usuario)
        cursos_map = {c["slug"]: c for c in _cursos_calendario_para_usuario(id_usuario)}
        enriquecer_eventos_con_cursos(eventos, cursos_map)
        return jsonify({"ok": True, "eventos": eventos})

    payload = request.get_json(silent=True) or request.form.to_dict()
    slugs = _slugs_cursos_asignados_set(id_usuario)
    try:
        evento = guardar_evento(
            actividades,
            id_usuario,
            payload,
            lambda arr, k: generar_id(arr, k),
            slugs_asignados=slugs,
        )
        guardar_datos("actividades", actividades)
        if not (payload.get("id_actividad") or payload.get("id")):
            registrar_actividad_sistema(
                "evento_creado",
                id_usuario,
                "Evento en calendario",
                f"{session.get('nombre', 'Estudiante')} creó el evento «{evento.get('titulo', 'Sin título')}»",
            )
        return jsonify({"ok": True, "evento": evento, "mensaje": "Actividad guardada."})
    except ValueError as exc:
        return jsonify({"ok": False, "mensaje": str(exc)}), 400


@app.route("/evento/<int:id_actividad>/curso")
@app.route("/api/calendario/eventos/<int:id_actividad>/curso")
def evento_curso_destino(id_actividad):
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401

    from calendario_service import obtener_evento_usuario

    id_usuario = session["id_usuario"]
    actividades = cargar_datos("actividades")
    evento = obtener_evento_usuario(actividades, id_usuario, id_actividad)
    if not evento:
        return jsonify({"ok": False, "mensaje": "Evento no encontrado."}), 404
    return jsonify(_json_destino_evento(id_usuario, evento))


@app.route("/api/calendario/eventos/<int:id_actividad>", methods=["PUT", "DELETE"])
def api_calendario_evento(id_actividad):
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401

    from calendario_service import eliminar_evento, guardar_evento, listar_eventos_usuario

    id_usuario = session["id_usuario"]
    actividades = cargar_datos("actividades")
    slugs = _slugs_cursos_asignados_set(id_usuario)

    if request.method == "DELETE":
        if not eliminar_evento(actividades, id_usuario, id_actividad):
            return jsonify({"ok": False, "mensaje": "Evento no encontrado."}), 404
        guardar_datos("actividades", actividades)
        return jsonify({"ok": True, "mensaje": "Evento eliminado."})

    payload = request.get_json(silent=True) or {}
    payload["id_actividad"] = id_actividad
    try:
        evento = guardar_evento(
            actividades,
            id_usuario,
            payload,
            lambda arr, k: generar_id(arr, k),
            slugs_asignados=slugs,
        )
        guardar_datos("actividades", actividades)
        return jsonify({"ok": True, "evento": evento, "mensaje": "Actividad actualizada."})
    except ValueError as exc:
        return jsonify({"ok": False, "mensaje": str(exc)}), 400


@app.route("/crear_curso", methods=["POST"])
def crear_curso():
    from session_auth import is_admin_session

    if "id_usuario" not in session or not is_admin_session():
        return redirect(url_for("login"))

    cursos = cargar_datos("cursos")

    nuevo_curso = {
        "id_curso": generar_id(cursos, "id_curso"),
        "titulo": request.form["titulo"],
        "descripcion": request.form["descripcion"],
        "categoria": request.form["categoria"],
        "imagen": request.form.get("imagen", ""),
        "activo": True,
        "fecha_creacion": datetime.now().strftime("%Y-%m-%d")
    }

    cursos.append(nuevo_curso)
    guardar_datos("cursos", cursos)

    try:
        from notificaciones_admin_service import crear_notificacion_admin

        crear_notificacion_admin(
            "curso_creado",
            f"Se creó el curso «{nuevo_curso['titulo']}» en el catálogo",
            titulo="Curso nuevo",
            id_usuario=session.get("id_usuario"),
        )
    except Exception:
        pass

    return redirect(url_for("dashboard"))


@app.route("/crear_leccion", methods=["POST"])
def crear_leccion():
    from session_auth import is_admin_session

    if "id_usuario" not in session or not is_admin_session():
        return redirect(url_for("login"))

    lecciones = cargar_datos("lecciones")

    nueva_leccion = {
        "id_leccion": generar_id(lecciones, "id_leccion"),
        "id_curso": int(request.form["id_curso"]),
        "titulo": request.form["titulo"],
        "descripcion": request.form["descripcion"],
        "contenido": request.form["contenido"],
        "video_url": request.form.get("video_url", ""),
        "orden": int(request.form["orden"]),
        "activo": True
    }

    lecciones.append(nueva_leccion)
    guardar_datos("lecciones", lecciones)

    try:
        from notificaciones_admin_service import crear_notificacion_admin

        crear_notificacion_admin(
            "leccion_creada",
            f"Nueva lección «{nueva_leccion['titulo']}» publicada",
            titulo="Lección creada",
            id_usuario=session.get("id_usuario"),
        )
    except Exception:
        pass

    return redirect(url_for("dashboard"))


@app.route("/mis_cursos")
def mis_cursos():
    if "id_usuario" not in session:
        return redirect(url_for("login"))

    id_usuario = session["id_usuario"]
    cursos_catalogo = listar_cursos_catalogo_usuario(id_usuario)

    return render_template(
        "mis_cursos.html",
        nombre=session["nombre"],
        cursos_catalogo=cursos_catalogo,
        cursos_activos=listar_cursos_activos_serializados(id_usuario),
        id_usuario=id_usuario,
    )


@app.route("/explorar-cursos")
def explorar_cursos():
    if "id_usuario" not in session:
        return redirect(url_for("login"))

    id_usuario = session["id_usuario"]
    slugs_asignados = set(obtener_slugs_cursos_asignados(id_usuario))
    catalogo = []
    for curso in listar_catalogo_general():
        curso["asignado"] = curso["slug"] in slugs_asignados
        catalogo.append(curso)

    return render_template(
        "explorar_cursos.html",
        nombre=session["nombre"],
        catalogo=catalogo,
    )


@app.route("/asignar-curso/<slug>", methods=["POST"])
def asignar_curso(slug):
    if "id_usuario" not in session:
        return redirect(url_for("login"))

    asignar_curso_a_usuario(session["id_usuario"], slug)
    return redirect(url_for("mis_cursos"))


@app.route("/api/mis-cursos/catalogo")
def api_mis_cursos_catalogo():
    if "id_usuario" not in session:
        return jsonify({"error": "No autorizado"}), 401

    id_usuario = session["id_usuario"]
    slugs_asignados = set(obtener_slugs_cursos_asignados(id_usuario))
    catalogo = []

    for slug in ORDEN_CURSOS_CATALOGO:
        base = CURSOS_CATALOGO.get(slug)
        if not base:
            continue
        catalogo.append(
            {
                "slug": slug,
                "titulo": base["titulo"],
                "descripcion": base["descripcion"],
                "nivel": base["nivel"],
                "imagen": base["imagen"],
                "materia": MATERIA_POR_SLUG.get(slug, "todas"),
                "asignado": slug in slugs_asignados,
            }
        )

    return jsonify({"catalogo": catalogo})


@app.route("/api/mis-cursos/activos")
def api_mis_cursos_activos():
    if "id_usuario" not in session:
        return jsonify({"error": "No autorizado"}), 401

    id_usuario = session["id_usuario"]
    cursos = listar_cursos_activos_serializados(id_usuario)
    return jsonify({"ok": True, "cursos": cursos, "total": len(cursos)})


@app.route("/api/asignar-curso/<slug>", methods=["POST"])
def api_asignar_curso(slug):
    if "id_usuario" not in session:
        return jsonify({"error": "No autorizado"}), 401

    id_usuario = session["id_usuario"]
    base = CURSOS_CATALOGO.get(slug)
    if not base:
        return jsonify({"error": "Curso no encontrado"}), 404

    asignar_curso_a_usuario(id_usuario, slug)
    curso = preparar_curso_para_tarjeta(base, id_usuario)
    html_tarjeta = render_template("partials/mis_cursos_tarjeta.html", curso=curso)

    curso_activo = serializar_curso_activo(curso)
    return jsonify(
        {
            "ok": True,
            "curso": {
                "slug": curso["slug"],
                "materia": curso["materia"],
                "nivel": curso["nivel"],
                "porcentaje": curso.get("porcentaje", 0),
            },
            "curso_activo": curso_activo,
            "html": html_tarjeta,
            "total": len(listar_cursos_catalogo_usuario(id_usuario)),
        }
    )


@app.route("/api/curso/<slug>/diagnostico", methods=["POST"])
def api_guardar_diagnostico(slug):
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401

    id_usuario = session["id_usuario"]
    if not usuario_tiene_curso_asignado(id_usuario, slug):
        return jsonify({"ok": False, "mensaje": "Curso no asignado."}), 403

    if not obtener_diagnostico_curso(slug):
        return jsonify({"ok": False, "mensaje": "Diagnóstico no disponible."}), 404

    data = request.get_json(silent=True) or {}
    respuestas = data.get("respuestas", [])
    resultado = evaluar_respuestas_diagnostico(slug, respuestas)
    if not resultado:
        return jsonify({"ok": False, "mensaje": "No se pudo evaluar."}), 400

    registro = guardar_diagnostico_usuario(id_usuario, slug, resultado)
    from progreso_service import calcular_progreso_curso

    curso = obtener_curso_catalogo(slug)
    progreso = calcular_progreso_curso(curso, id_usuario) if curso else None

    return jsonify(
        {
            "ok": True,
            "nivel": registro["nivel"],
            "titulo_nivel": registro["titulo_nivel"],
            "porcentaje": registro["porcentaje"],
            "mensaje": MENSAJES_NIVEL.get(registro["nivel"], ""),
            "progreso_curso": (progreso or {}).get("porcentaje"),
            "progreso": progreso,
        }
    )


@app.route("/curso/<slug>")
def detalle_curso(slug):
    if "id_usuario" not in session:
        return redirect(url_for("login"))

    id_usuario = session["id_usuario"]
    if not usuario_tiene_curso_asignado(id_usuario, slug):
        return redirect(url_for("mis_cursos"))

    curso = obtener_curso_catalogo(slug)
    if not curso:
        return redirect(url_for("mis_cursos"))

    curso = aplicar_progreso_a_curso(curso, id_usuario)
    diagnostico = obtener_diagnostico_usuario(id_usuario, slug)
    quiz_diagnostico = obtener_diagnostico_curso(slug)

    if diagnostico:
        curso = aplicar_ruta_diagnostico_a_curso(curso, diagnostico)
        leccion_actual = resolver_leccion_actual_con_ruta(curso)
    else:
        leccion_actual = None

    registrar_actividad_automatica(
        id_usuario, "curso", {"slug": slug, "origen": "detalle_curso"}
    )

    return render_template(
        "detalle_curso.html",
        nombre=session["nombre"],
        curso=curso,
        leccion_actual=leccion_actual,
        diagnostico=diagnostico,
        quiz_diagnostico=quiz_diagnostico,
        diagnostico_completado=diagnostico is not None,
        id_usuario=id_usuario,
    )


@app.route("/curso/<slug>/leccion/<leccion_id>")
def ver_leccion(slug, leccion_id):
    if "id_usuario" not in session:
        return redirect(url_for("login"))

    id_usuario = session["id_usuario"]
    if not usuario_tiene_curso_asignado(id_usuario, slug):
        return redirect(url_for("mis_cursos"))

    curso = obtener_curso_catalogo(slug)
    if not curso:
        return redirect(url_for("mis_cursos"))

    if not usuario_completo_diagnostico(id_usuario, slug):
        return redirect(url_for("detalle_curso", slug=slug) + "#diagnostico")

    curso = aplicar_progreso_a_curso(curso, id_usuario)
    diagnostico = obtener_diagnostico_usuario(id_usuario, slug)
    if diagnostico:
        curso = aplicar_ruta_diagnostico_a_curso(curso, diagnostico)

    leccion = obtener_leccion_curso(curso, leccion_id)
    if not leccion:
        leccion_actual = resolver_leccion_actual(curso)
        if leccion_actual:
            return redirect(
                url_for("ver_leccion", slug=slug, leccion_id=leccion_actual["id"])
            )
        return redirect(url_for("detalle_curso", slug=slug))

    if leccion.get("bloqueada"):
        return redirect(url_for("detalle_curso", slug=slug) + "#lecciones")

    actividades = cargar_datos("actividad_sistema")
    ya_registrado = any(
        a.get("tipo") == "leccion_iniciada"
        and a.get("id_usuario") == id_usuario
        and a.get("slug") == slug
        and a.get("leccion_id") == leccion_id
        for a in actividades
    )
    if not ya_registrado and leccion.get("estado") != "completado":
        actividades.append(
            {
                "id_actividad": generar_id(actividades, "id_actividad"),
                "tipo": "leccion_iniciada",
                "id_usuario": id_usuario,
                "slug": slug,
                "leccion_id": leccion_id,
                "titulo": "Lección iniciada",
                "descripcion": f"{session.get('nombre', 'Estudiante')} inició {leccion.get('titulo', leccion_id)}",
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
        )
        guardar_datos("actividad_sistema", actividades[-120:])

    registrar_actividad_automatica(
        id_usuario,
        "curso",
        {"slug": slug, "leccion_id": leccion_id, "origen": "ver_leccion"},
    )

    contenido = obtener_contenido_leccion(slug, leccion_id, curso, leccion)
    siguiente = obtener_siguiente_leccion(curso, leccion_id)
    if siguiente:
        continuar_url = url_for("ver_leccion", slug=slug, leccion_id=siguiente["id"])
    else:
        continuar_url = url_for("detalle_curso", slug=slug)

    return render_template(
        "leccion.html",
        nombre=session["nombre"],
        curso=curso,
        leccion=leccion,
        contenido=contenido,
        continuar_url=continuar_url,
        marcar_url=url_for(
            "completar_leccion_catalogo", slug=slug, leccion_id=leccion_id
        ),
        guardar_quiz_url=url_for(
            "api_guardar_quiz_leccion", slug=slug, leccion_id=leccion_id
        ),
    )


@app.route("/curso/<slug>/leccion/<leccion_id>/quiz", methods=["POST"])
def api_guardar_quiz_leccion(slug, leccion_id):
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401

    id_usuario = session["id_usuario"]
    if not usuario_tiene_curso_asignado(id_usuario, slug):
        return jsonify({"ok": False, "mensaje": "Curso no asignado."}), 403

    data = request.get_json(silent=True) or {}
    porcentaje = int(data.get("porcentaje", 0))
    correctas = int(data.get("correctas", 0))
    total = int(data.get("total", 0))
    from catalog_service import umbral_aprobacion_quiz

    umbral = umbral_aprobacion_quiz(slug, leccion_id)
    aprobado = bool(data.get("aprobado", porcentaje >= umbral))

    registro = guardar_resultado_quiz(
        id_usuario, slug, leccion_id, porcentaje, correctas, total, aprobado
    )
    progreso = None
    if aprobado:
        from progreso_service import calcular_progreso_curso

        curso = obtener_curso_catalogo(slug)
        if curso:
            progreso = calcular_progreso_curso(curso, id_usuario)
    return jsonify(
        {
            "ok": True,
            "intento": registro["intento"],
            "aprobado": aprobado,
            "progreso": progreso,
            "porcentaje_curso": (progreso or {}).get("porcentaje"),
        }
    )


@app.route("/curso/<slug>/leccion/<leccion_id>/completar", methods=["POST"])
def completar_leccion_catalogo(slug, leccion_id):
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401

    resultado = marcar_leccion_catalogo_completada(
        session["id_usuario"], slug, leccion_id
    )
    if not resultado:
        return jsonify({"ok": False, "mensaje": "Lección no encontrada."}), 404

    siguiente = resultado["siguiente_leccion"]
    if siguiente:
        continuar_url = url_for(
            "ver_leccion", slug=slug, leccion_id=siguiente["id"]
        )
    else:
        continuar_url = url_for("detalle_curso", slug=slug)

    progreso = resultado.get("progreso") or {}
    return jsonify(
        {
            "ok": True,
            "mensaje": "Lección marcada como completada",
            "continuar_url": continuar_url,
            "siguiente_leccion_id": siguiente["id"] if siguiente else None,
            "porcentaje_curso": resultado["curso"]["porcentaje"],
            "progreso": progreso,
            "curso_completado": progreso.get("completado", False),
        }
    )


@app.route("/api/progreso/resumen", methods=["GET"])
def api_progreso_resumen():
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401
    from progreso_service import obtener_resumen_progreso_usuario

    return jsonify({"ok": True, **obtener_resumen_progreso_usuario(session["id_usuario"])})


@app.route("/api/progreso/curso/<slug>", methods=["GET"])
def api_progreso_curso(slug):
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401
    id_usuario = session["id_usuario"]
    if not usuario_tiene_curso_asignado(id_usuario, slug):
        return jsonify({"ok": False, "mensaje": "Curso no asignado."}), 403
    base = obtener_curso_catalogo(slug)
    if not base:
        return jsonify({"ok": False, "mensaje": "Curso no encontrado."}), 404
    from progreso_service import calcular_progreso_curso, aplicar_progreso_calculado

    curso = aplicar_progreso_calculado(base, id_usuario)
    stats = calcular_progreso_curso(curso, id_usuario)
    return jsonify({"ok": True, "curso": curso, "progreso": stats})


@app.route("/plan_estudios")
def plan_estudios():
    if "id_usuario" not in session:
        return redirect(url_for("login"))

    from calendario_service import enriquecer_eventos_con_cursos, listar_eventos_usuario
    from metas_service import listar_metas_usuario

    id_usuario = session["id_usuario"]
    actividades = cargar_datos("actividades")
    eventos_calendario = listar_eventos_usuario(actividades, id_usuario)
    cursos_cal = _cursos_calendario_para_usuario(id_usuario)
    enriquecer_eventos_con_cursos(
        eventos_calendario, {c["slug"]: c for c in cursos_cal}
    )
    cursos = listar_cursos_catalogo_usuario(id_usuario)
    estado_racha = preparar_racha_plan_estudios(id_usuario)
    metas_personales = listar_metas_usuario(actividades, id_usuario)

    return render_template(
        "plan_estudios.html",
        nombre=session["nombre"],
        eventos_calendario=eventos_calendario,
        cursos_calendario=cursos_cal,
        metas_personales=metas_personales,
        tiene_cursos=len(cursos) > 0,
        estado_racha=estado_racha,
    )


@app.route("/progreso")
def progreso():
    if "id_usuario" not in session:
        return redirect(url_for("login"))

    id_usuario = session["id_usuario"]
    datos = obtener_datos_progreso_usuario(id_usuario)
    resumen_racha = obtener_resumen_racha(id_usuario)

    return render_template(
        "progreso.html",
        nombre=session["nombre"],
        tiene_cursos=datos["tiene_cursos"],
        lecciones_completadas=datos["lecciones_completadas"],
        cursos=datos["cursos"],
        promedio_general=datos.get("promedio_general", 0),
        cursos_completados=datos.get("cursos_completados", 0),
        tendencia=datos.get("tendencia", []),
        items_busqueda_progreso=obtener_items_busqueda_progreso(id_usuario),
        racha_actual=resumen_racha.get("racha_actual", 0),
        racha_mejor=resumen_racha.get("mejor_racha", 0),
        racha_nivel=resumen_racha.get("nivel", "Explorador"),
    )

@app.route("/tutor_ai")
def tutor_ai():
    if "id_usuario" not in session:
        return redirect(url_for("login"))

    from tutor_ai_service import (
        TEMA_DEFAULT,
        construir_contexto_academico,
        crear_sesion,
        estado_limites_ui,
        etiqueta_materia,
        listar_sesiones_recientes,
        mensaje_error_amigable,
        openai_disponible,
    )

    usuario = obtener_usuario_sesion()
    try:
        contexto = construir_contexto_academico(session["id_usuario"])
        sesion_chat = crear_sesion(session["id_usuario"], contexto)
        tutor_session_id = sesion_chat["session_id"]
        tutor_mensajes = sesion_chat.get("mensajes", [])
        tutor_recientes = listar_sesiones_recientes(session["id_usuario"])
    except Exception as exc:
        app.logger.exception("Error al cargar Tutor IA")
        contexto = TEMA_DEFAULT.copy()
        tutor_session_id = ""
        tutor_mensajes = [
            {
                "role": "assistant",
                "content": mensaje_error_amigable(exc),
                "created_at": datetime.now().isoformat(),
            }
        ]
        tutor_recientes = []

    return render_template(
        "tutor_ai.html",
        nombre=session["nombre"],
        tutor_session_id=tutor_session_id,
        tutor_contexto=contexto,
        tutor_mensajes=tutor_mensajes,
        tutor_recientes=tutor_recientes,
        tutor_limites=estado_limites_ui(session["id_usuario"], usuario),
        tutor_ia_configurada=openai_disponible(),
        tutor_materia_etiqueta=etiqueta_materia(contexto.get("materia", "matematicas")),
    )


# ——— API Tutor IA ———
@app.route("/api/tutor_ai/session", methods=["POST"])
def api_tutor_nueva_sesion():
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401
    from tutor_ai_service import (
        TutorAIError,
        construir_contexto_academico,
        crear_sesion,
        mensaje_error_amigable,
    )

    try:
        data = request.get_json(silent=True) or {}
        contexto = construir_contexto_academico(session["id_usuario"], data.get("contexto"))
        s = crear_sesion(session["id_usuario"], contexto)
        return jsonify(
            {
                "ok": True,
                "session_id": s["session_id"],
                "titulo": s.get("titulo"),
                "mensajes": s.get("mensajes", []),
                "contexto": s.get("contexto"),
            }
        )
    except TutorAIError as exc:
        return jsonify({"ok": False, "mensaje": str(exc)}), 503
    except Exception as exc:
        app.logger.exception("api_tutor_nueva_sesion")
        return jsonify({"ok": False, "mensaje": mensaje_error_amigable(exc)}), 500


@app.route("/api/tutor_ai/session/<session_id>", methods=["GET"])
def api_tutor_obtener_sesion(session_id):
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401
    from tutor_ai_service import TutorAIError, mensaje_error_amigable, obtener_sesion

    try:
        s = obtener_sesion(session_id, session["id_usuario"])
        if not s:
            return jsonify({"ok": False, "mensaje": "Sesión no encontrada."}), 404
        return jsonify({"ok": True, "sesion": s})
    except TutorAIError as exc:
        return jsonify({"ok": False, "mensaje": str(exc)}), 503
    except Exception as exc:
        app.logger.exception("api_tutor_obtener_sesion")
        return jsonify({"ok": False, "mensaje": mensaje_error_amigable(exc)}), 500


@app.route("/api/tutor_ai/chat", methods=["POST"])
@app.route("/api/chat", methods=["POST"])
def api_tutor_chat():
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401
    from tutor_ai_service import TutorAIError, mensaje_error_amigable, procesar_mensaje

    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    mensaje = data.get("mensaje", "")
    if not session_id:
        return jsonify({"ok": False, "mensaje": "session_id requerido."}), 400
    usuario = obtener_usuario_sesion()
    try:
        resultado = procesar_mensaje(session_id, session["id_usuario"], usuario, mensaje)
        if not resultado.get("ok"):
            status = 503 if "configurado" in resultado.get("mensaje", "").lower() else 400
            return jsonify(resultado), status
        return jsonify(resultado)
    except TutorAIError as exc:
        return jsonify({"ok": False, "mensaje": str(exc)}), 503
    except Exception as exc:
        app.logger.exception("api_tutor_chat")
        return jsonify({"ok": False, "mensaje": mensaje_error_amigable(exc)}), 500


@app.route("/api/tutor_ai/chat/stream", methods=["POST"])
@app.route("/api/chat/stream", methods=["POST"])
def api_tutor_chat_stream():
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401
    from tutor_ai_service import (
        TutorAIError,
        agregar_mensaje_sesion,
        asegurar_openai,
        obtener_sesion,
        registrar_uso_mensaje,
        sanitizar_entrada,
        stream_respuesta_ia,
        verificar_limites,
    )

    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    mensaje = sanitizar_entrada(data.get("mensaje", ""))
    if not session_id:
        return jsonify({"ok": False, "mensaje": "session_id requerido."}), 400
    if len(mensaje) < 1:
        return jsonify({"ok": False, "mensaje": "Escribe un mensaje válido."}), 400
    usuario = obtener_usuario_sesion()
    error = verificar_limites(session["id_usuario"], usuario)
    if error:
        return jsonify({"ok": False, **error}), 400

    try:
        asegurar_openai()
    except TutorAIError as exc:
        return jsonify({"ok": False, "mensaje": str(exc)}), 503

    sesion_chat = obtener_sesion(session_id, session["id_usuario"])
    if not sesion_chat:
        return jsonify({"ok": False, "mensaje": "Sesión no encontrada."}), 404

    agregar_mensaje_sesion(session_id, session["id_usuario"], "user", mensaje)
    sesion_actualizada = obtener_sesion(session_id, session["id_usuario"])

    def generar():
        partes = []
        status_pendientes = []

        def on_status(kind: str, msg: str) -> None:
            status_pendientes.append((kind, msg))

        try:
            yield f"data: {json.dumps({'status': 'processing', 'mensaje': 'La IA está procesando tu solicitud…'}, ensure_ascii=False)}\n\n"

            for chunk in stream_respuesta_ia(
                sesion_actualizada, mensaje, usuario, on_status=on_status
            ):
                while status_pendientes:
                    k, m = status_pendientes.pop(0)
                    yield f"data: {json.dumps({'status': k, 'mensaje': m}, ensure_ascii=False)}\n\n"
                partes.append(chunk)
                yield f"data: {json.dumps({'delta': chunk}, ensure_ascii=False)}\n\n"

            texto = "".join(partes).strip()
            if not texto:
                raise TutorAIError(
                    "La IA no generó una respuesta.",
                    codigo="empty",
                    retryable=True,
                )
            agregar_mensaje_sesion(session_id, session["id_usuario"], "assistant", texto)
            registrar_uso_mensaje(session["id_usuario"])
            yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
        except TutorAIError as exc:
            yield f"data: {json.dumps({'error': True, 'mensaje': str(exc), 'codigo': exc.codigo, 'retryable': exc.retryable}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            from tutor_ai_service import error_respuesta_dict

            payload = error_respuesta_dict(exc)
            payload["error"] = True
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return Response(
        stream_with_context(generar()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/tutor_ai/quick-action", methods=["POST"])
def api_tutor_quick_action():
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401
    from tutor_ai_service import TutorAIError, accion_rapida, mensaje_error_amigable

    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    accion = data.get("accion", "")
    if not session_id:
        return jsonify({"ok": False, "mensaje": "session_id requerido."}), 400
    usuario = obtener_usuario_sesion()
    try:
        resultado = accion_rapida(session_id, session["id_usuario"], usuario, accion)
        if not resultado.get("ok"):
            status = 503 if "configurado" in resultado.get("mensaje", "").lower() else 400
            return jsonify(resultado), status
        return jsonify(resultado)
    except TutorAIError as exc:
        return jsonify({"ok": False, "mensaje": str(exc)}), 503
    except Exception as exc:
        app.logger.exception("api_tutor_quick_action")
        return jsonify({"ok": False, "mensaje": mensaje_error_amigable(exc)}), 500


@app.route("/api/tutor_ai/health", methods=["GET"])
def api_tutor_health():
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401
    from tutor_ai_service import diagnosticar_tutor_ia

    diag = diagnosticar_tutor_ia()
    status = 200 if diag.get("ok") else 503
    return jsonify({"ok": diag.get("ok", False), "diagnostico": diag}), status


@app.route("/api/tutor_ai/limites", methods=["GET"])
def api_tutor_limites():
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401
    from tutor_ai_service import TutorAIError, estado_limites_ui, mensaje_error_amigable

    usuario = obtener_usuario_sesion()
    try:
        return jsonify({"ok": True, **estado_limites_ui(session["id_usuario"], usuario)})
    except TutorAIError as exc:
        return jsonify({"ok": False, "mensaje": str(exc)}), 503
    except Exception as exc:
        app.logger.exception("api_tutor_limites")
        return jsonify({"ok": False, "mensaje": mensaje_error_amigable(exc)}), 500


@app.route("/api/usuario/plan/mejorar", methods=["POST"])
def api_mejorar_plan_pro():
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401
    from session_auth import is_estudiante_session

    if not is_estudiante_session():
        return jsonify({"ok": False, "mensaje": "Esta acción es solo para estudiantes."}), 403

    try:
        from nebula_data import activar_plan_pro_usuario

        resultado = activar_plan_pro_usuario(session["id_usuario"])
        return jsonify(
            {
                "ok": resultado.get("ok", True),
                "ya_activo": resultado.get("ya_activo", False),
                "plan": resultado.get("plan", "pro"),
                "mensaje": resultado.get("mensaje", "Plan Pro activado."),
            }
        )
    except ValueError as exc:
        return jsonify({"ok": False, "mensaje": str(exc)}), 400
    except Exception as exc:
        app.logger.exception("api_mejorar_plan_pro")
        return jsonify(
            {"ok": False, "mensaje": "No se pudo activar el plan. Intenta de nuevo."}
        ), 500


def _avatar_url_usuario(usuario: dict, *, default: str = "") -> str:
    from perfil_service import resolve_avatar_url

    rol = usuario.get("id_rol")
    fallback = default or (
        AVATAR_ADMIN_DEFAULT if rol == 1 else AVATAR_ESTUDIANTE_DEFAULT
    )
    return resolve_avatar_url(
        usuario.get("foto_perfil"),
        usuario.get("foto_actualizada_en"),
        lambda rel: url_for("static", filename=rel),
        fallback,
    )


def avatar_url_estudiante(usuario: dict) -> str:
    """URL de avatar para un estudiante (vistas admin y reportes)."""
    return _avatar_url_usuario(usuario, default=AVATAR_ESTUDIANTE_DEFAULT)


def _serializar_usuario_perfil_api(usuario: dict) -> dict:
    usuario = usuario or {}
    prefs = usuario.get("preferencias_aprendizaje") or {}
    return {
        "id_usuario": usuario.get("id_usuario"),
        "nombre_completo": usuario.get("nombre_completo", ""),
        "username": usuario.get("username", ""),
        "correo": usuario.get("correo", ""),
        "sobre_mi": usuario.get("sobre_mi", ""),
        "nivel_academico": usuario.get("nivel_academico", ""),
        "grado": usuario.get("grado", ""),
        "foto_perfil": usuario.get("foto_perfil") or usuario.get("profile_image", ""),
        "profile_image": usuario.get("profile_image") or usuario.get("foto_perfil", ""),
        "foto_actualizada_en": usuario.get("foto_actualizada_en", ""),
        "updated_at": usuario.get("updated_at", ""),
        "preferencias_aprendizaje": prefs,
        "preferencia_dominante": prefs.get("dominante", "visual"),
        "avatar_url": _avatar_url_usuario(usuario) or AVATAR_ESTUDIANTE_DEFAULT,
        "activo": usuario.get("activo", True),
    }


@app.route("/perfil", methods=["GET"], endpoint="perfil")
def perfil():
    if "id_usuario" not in session:
        return redirect(url_for("login"))

    usuario = obtener_usuario_sesion()

    if not usuario:
        return redirect(url_for("login"))

    from perfil_service import normalizar_usuario_perfil

    usuario = normalizar_usuario_perfil(usuario)
    avatar_url = _avatar_url_usuario(usuario)
    id_usuario = session["id_usuario"]
    cursos_activos = listar_cursos_catalogo_usuario(id_usuario)
    datos_progreso = obtener_datos_progreso_usuario(id_usuario)
    resumen_racha = obtener_resumen_racha(id_usuario)

    progreso_promedio = 0
    if cursos_activos:
        progreso_promedio = round(
            sum(c.get("porcentaje", 0) for c in cursos_activos) / len(cursos_activos)
        )

    return render_template(
        "perfil.html",
        nombre=usuario.get("nombre_completo", session.get("nombre", "")),
        usuario=usuario,
        avatar_url=avatar_url,
        cursos_activos=cursos_activos,
        datos_progreso=datos_progreso,
        resumen_racha=resumen_racha,
        progreso_promedio=progreso_promedio,
    )


@app.route("/api/perfil", methods=["POST"])
def api_perfil_actualizar():
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401

    from perfil_service import (
        actualizar_usuario_en_lista,
        guardar_foto_perfil,
        normalizar_usuario_perfil,
        validar_datos_perfil,
    )

    usuario_actual = obtener_usuario_sesion()
    if not usuario_actual:
        return jsonify({"ok": False, "mensaje": "Usuario no encontrado."}), 404

    id_usuario = session["id_usuario"]
    usuarios = cargar_datos("usuarios")

    payload = {
        "nombre_completo": request.form.get("nombre_completo"),
        "username": request.form.get("username"),
        "correo": request.form.get("correo"),
        "sobre_mi": request.form.get("sobre_mi"),
        "nivel_academico": request.form.get("nivel_academico"),
        "preferencia_dominante": request.form.get("preferencia_dominante"),
    }
    if request.is_json:
        payload = {**payload, **(request.get_json(silent=True) or {})}

    datos_validos, error = validar_datos_perfil(payload, id_usuario, usuarios)
    if error:
        return jsonify({"ok": False, "mensaje": error}), 400

    cambios = dict(datos_validos)
    archivo = request.files.get("foto")
    if archivo and archivo.filename:
        ruta_foto, err_foto = guardar_foto_perfil(
            archivo,
            id_usuario,
            usuario_actual.get("foto_perfil"),
        )
        if err_foto:
            return jsonify({"ok": False, "mensaje": err_foto}), 400
        from perfil_service import marca_foto_actualizada

        cambios = marca_foto_actualizada({**cambios, "foto_perfil": ruta_foto})

    usuario = actualizar_usuario_en_lista(usuarios, id_usuario, cambios)
    if not usuario:
        return jsonify({"ok": False, "mensaje": "No se pudo actualizar el perfil."}), 500

    guardar_datos("usuarios", usuarios)
    usuario = normalizar_usuario_perfil(usuario)
    session["nombre"] = usuario.get("nombre_completo", session.get("nombre"))

    from session_auth import is_estudiante_session

    if is_estudiante_session():
        try:
            from notificaciones_admin_service import crear_notificacion_admin

            crear_notificacion_admin(
                "perfil_completado",
                f"{usuario.get('nombre_completo', 'Estudiante')} actualizó su perfil académico",
                titulo="Perfil actualizado",
                id_usuario=id_usuario,
            )
        except Exception:
            pass

    return jsonify(
        {
            "ok": True,
            "mensaje": "Perfil actualizado correctamente.",
            "usuario": _serializar_usuario_perfil_api(usuario),
        }
    )


@app.route("/upload-profile-image", methods=["POST"])
@app.route("/api/perfil/foto", methods=["POST"])
def api_perfil_foto():
    """Sube solo la foto de perfil (vista previa + guardar)."""
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401

    from perfil_service import (
        asegurar_carpeta_fotos,
        guardar_foto_perfil,
        normalizar_usuario_perfil,
    )

    try:
        asegurar_carpeta_fotos()
        usuario_actual = obtener_usuario_sesion()
        if not usuario_actual:
            return jsonify({"ok": False, "mensaje": "Usuario no encontrado."}), 404

        archivo = request.files.get("foto") or request.files.get("file")
        if archivo is None:
            return jsonify({"ok": False, "mensaje": "No se recibió ninguna imagen."}), 400

        ruta_foto, err = guardar_foto_perfil(
            archivo,
            session["id_usuario"],
            usuario_actual.get("foto_perfil"),
        )
        if err:
            return jsonify({"ok": False, "mensaje": err}), 400

        from nebula_data import actualizar_campos_usuario
        from perfil_service import marca_foto_actualizada

        try:
            usuario = actualizar_campos_usuario(
                session["id_usuario"],
                marca_foto_actualizada({"foto_perfil": ruta_foto}),
            )
        except ValueError:
            return jsonify({"ok": False, "mensaje": "No se pudo actualizar el usuario."}), 500

        usuario = normalizar_usuario_perfil(usuario)
        foto_ts = usuario.get("foto_actualizada_en", "")

        from session_auth import is_estudiante_session

        if is_estudiante_session():
            try:
                from notificaciones_admin_service import crear_notificacion_admin

                crear_notificacion_admin(
                    "foto_perfil",
                    f"{usuario.get('nombre_completo', 'Un estudiante')} actualizó su foto de perfil",
                    titulo="Foto de perfil actualizada",
                    id_usuario=session["id_usuario"],
                    avatar=_avatar_url_usuario(usuario),
                )
            except Exception:
                pass

        return jsonify(
            {
                "ok": True,
                "mensaje": "Imagen subida correctamente.",
                "usuario": _serializar_usuario_perfil_api(usuario),
                "avatar_url": _avatar_url_usuario(usuario),
                "foto_perfil": ruta_foto,
                "foto_actualizada_en": foto_ts,
            }
        )
    except Exception:
        app.logger.exception("api_perfil_foto")
        return jsonify({"ok": False, "mensaje": "Error al subir la imagen."}), 500


@app.route("/api/profile-image", methods=["GET"])
@app.route("/api/perfil/imagen", methods=["GET"])
def api_profile_image():
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401

    usuario = obtener_usuario_sesion()
    if not usuario:
        return jsonify({"ok": False, "mensaje": "Usuario no encontrado."}), 404

    from perfil_service import normalizar_usuario_perfil

    usuario = normalizar_usuario_perfil(usuario)
    avatar_url = _avatar_url_usuario(usuario) or (
        AVATAR_ADMIN_DEFAULT if usuario.get("id_rol") == 1 else AVATAR_ESTUDIANTE_DEFAULT
    )
    return jsonify(
        {
            "ok": True,
            "avatar_url": avatar_url,
            "profile_image": usuario.get("foto_perfil", ""),
            "foto_perfil": usuario.get("foto_perfil", ""),
            "foto_actualizada_en": usuario.get("foto_actualizada_en", ""),
            "updated_at": usuario.get("updated_at", ""),
        }
    )


@app.route("/api/perfil/foto", methods=["DELETE"])
def api_perfil_foto_eliminar():
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401

    from perfil_service import eliminar_foto_perfil_usuario, normalizar_usuario_perfil

    usuarios = cargar_datos("usuarios")
    usuario, err = eliminar_foto_perfil_usuario(usuarios, session["id_usuario"])
    if err:
        return jsonify({"ok": False, "mensaje": err}), 400
    guardar_datos("usuarios", usuarios)
    usuario = normalizar_usuario_perfil(usuario)
    default = AVATAR_ESTUDIANTE_DEFAULT
    return jsonify(
        {
            "ok": True,
            "mensaje": "Foto eliminada.",
            "usuario": _serializar_usuario_perfil_api(usuario),
            "avatar_url": default,
        }
    )


@app.route("/api/perfil/password", methods=["POST"])
def api_perfil_password():
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401

    data = request.get_json(silent=True) or {}
    actual = (data.get("password_actual") or data.get("current_password") or "").strip()
    nueva = (data.get("password_nueva") or data.get("new_password") or "").strip()
    confirmar = (data.get("password_confirmar") or data.get("confirm_password") or "").strip()

    if len(nueva) < 6:
        return jsonify({"ok": False, "mensaje": "La nueva contraseña debe tener al menos 6 caracteres."}), 400
    if nueva != confirmar:
        return jsonify({"ok": False, "mensaje": "Las contraseñas no coinciden."}), 400

    usuario = obtener_usuario_sesion()
    if not usuario:
        return jsonify({"ok": False, "mensaje": "Usuario no encontrado."}), 404

    from password_security import hash_password, verify_password

    if not verify_password(actual, usuario.get("password")):
        return jsonify({"ok": False, "mensaje": "La contraseña actual no es correcta."}), 400

    usuarios = cargar_datos("usuarios")
    from perfil_service import actualizar_usuario_en_lista

    actualizado = actualizar_usuario_en_lista(
        usuarios,
        session["id_usuario"],
        {"password": hash_password(nueva)},
    )
    if not actualizado:
        return jsonify({"ok": False, "mensaje": "No se pudo actualizar la contraseña."}), 500
    guardar_datos("usuarios", usuarios)
    return jsonify({"ok": True, "mensaje": "Contraseña actualizada correctamente."})


@app.route("/api/perfil/me", methods=["GET"])
def api_perfil_me():
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401

    from perfil_service import normalizar_usuario_perfil

    usuario = obtener_usuario_sesion()
    if not usuario:
        return jsonify({"ok": False, "mensaje": "Usuario no encontrado."}), 404

    usuario = normalizar_usuario_perfil(usuario)
    return jsonify({"ok": True, "usuario": _serializar_usuario_perfil_api(usuario)})


@app.route("/marcar_completado/<int:id_curso>/<int:id_leccion>")
def marcar_completado(id_curso, id_leccion):
    if "id_usuario" not in session:
        return redirect(url_for("login"))

    progreso = cargar_datos("progreso")

    nuevo_progreso = {
        "id_progreso": generar_id(progreso, "id_progreso"),
        "id_usuario": session["id_usuario"],
        "id_curso": id_curso,
        "id_leccion": id_leccion,
        "estado": "completado",
        "porcentaje": 100,
        "fecha_actualizacion": datetime.now().strftime("%Y-%m-%d")
    }

    progreso.append(nuevo_progreso)
    guardar_datos("progreso", progreso)

    registrar_actividad_automatica(
        session["id_usuario"],
        "leccion",
        {"id_curso": id_curso, "id_leccion": id_leccion, "origen": "marcar_completado"},
    )

    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


def _requiere_admin():
    """Redirige si no hay sesión de administrador (rol 1)."""
    from session_auth import require_admin_redirect

    return require_admin_redirect()


@app.route("/admin")
def admin():
    redir = _requiere_admin()
    if redir:
        return redir

    from admin_servicio import obtener_datos_admin_completos

    admin_usuario = obtener_usuario_sesion()
    datos = obtener_datos_admin_completos()

    return render_template(
        "dashboardadmin.html",
        admin_nav="gestion",
        admin_usuario=admin_usuario,
        resumen=datos["resumen"],
        usuarios_admin=datos["usuarios"],
        cursos_admin=datos["cursos"],
        lecciones_admin=datos["lecciones"],
        evaluaciones_admin=datos["evaluaciones"],
        cursos_populares=datos["cursos_populares"],
        distribucion_roles=datos["distribucion_roles"],
        actividad_reciente=datos["actividad_reciente"],
        resumen_actividad=datos.get("resumen_actividad"),
    )


@app.route("/analytics")
def analytics():
    redir = _requiere_admin()
    if redir:
        return redir

    from admin_servicio import obtener_datos_analytics

    return render_template(
        "analytics.html",
        admin_nav="analytics",
        admin_usuario=obtener_usuario_sesion(),
        header_buscar="Buscar métricas...",
        analytics=obtener_datos_analytics(),
    )


@app.route("/analytics/export")
def analytics_export():
    redir = _requiere_admin()
    if redir:
        return redir

    from admin_servicio import obtener_datos_analytics

    payload = obtener_datos_analytics()
    return Response(
        json.dumps(payload, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={
            "Content-Disposition": "attachment; filename=nebula-analytics.json",
        },
    )


@app.route("/admin/profile")
def admin_profile():
    redir = _requiere_admin()
    if redir:
        return redir

    from admin_servicio import obtener_perfil_admin

    usuario = obtener_usuario_sesion()
    return render_template(
        "perfiladmin.html",
        admin_nav="perfil",
        admin_usuario=usuario,
        perfil=obtener_perfil_admin(session["id_usuario"]),
        avatar_url=_avatar_url_usuario(usuario) or AVATAR_ADMIN_DEFAULT,
    )


def _requiere_admin_json():
    from session_auth import is_admin_session, repair_session_role_keys

    repair_session_role_keys()
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401
    if not is_admin_session():
        return jsonify({"ok": False, "mensaje": "Acceso denegado."}), 403
    return None


@app.route("/api/admin/catalogo/cursos", methods=["GET", "POST"])
def api_admin_catalogo_cursos():
    err = _requiere_admin_json()
    if err:
        return err
    from catalog_service import crear_curso, listar_cursos_admin_db

    if request.method == "GET":
        return jsonify({"ok": True, "cursos": listar_cursos_admin_db()})

    data = request.get_json(silent=True) or {}
    try:
        return jsonify(crear_curso(data))
    except ValueError as exc:
        return jsonify({"ok": False, "mensaje": str(exc)}), 400


@app.route("/api/admin/catalogo/cursos/<slug>", methods=["GET", "PUT", "DELETE"])
def api_admin_catalogo_curso(slug):
    err = _requiere_admin_json()
    if err:
        return err
    from catalog_service import (
        actualizar_curso,
        eliminar_curso,
        obtener_curso_admin,
    )

    if request.method == "GET":
        curso = obtener_curso_admin(slug)
        if not curso:
            return jsonify({"ok": False, "mensaje": "Curso no encontrado."}), 404
        return jsonify({"ok": True, "curso": curso})

    if request.method == "DELETE":
        try:
            return jsonify(eliminar_curso(slug))
        except ValueError as exc:
            return jsonify({"ok": False, "mensaje": str(exc)}), 400

    data = request.get_json(silent=True) or {}
    try:
        return jsonify(actualizar_curso(slug, data))
    except ValueError as exc:
        return jsonify({"ok": False, "mensaje": str(exc)}), 400


@app.route("/api/admin/catalogo/lecciones", methods=["GET", "POST"])
def api_admin_catalogo_lecciones():
    err = _requiere_admin_json()
    if err:
        return err
    from catalog_service import crear_leccion, listar_lecciones_db

    if request.method == "GET":
        return jsonify({"ok": True, "lecciones": listar_lecciones_db()})

    data = request.get_json(silent=True) or {}
    try:
        return jsonify(crear_leccion(data))
    except ValueError as exc:
        return jsonify({"ok": False, "mensaje": str(exc)}), 400


@app.route("/api/admin/catalogo/lecciones/<int:lesson_id>", methods=["GET", "PUT", "DELETE"])
def api_admin_catalogo_leccion(lesson_id):
    err = _requiere_admin_json()
    if err:
        return err
    from catalog_service import (
        actualizar_leccion,
        eliminar_leccion,
        obtener_leccion_admin,
    )

    if request.method == "GET":
        lec = obtener_leccion_admin(lesson_id)
        if not lec:
            return jsonify({"ok": False, "mensaje": "Lección no encontrada."}), 404
        return jsonify({"ok": True, "leccion": lec})

    if request.method == "DELETE":
        try:
            return jsonify(eliminar_leccion(lesson_id))
        except ValueError as exc:
            return jsonify({"ok": False, "mensaje": str(exc)}), 400

    data = request.get_json(silent=True) or {}
    try:
        return jsonify(actualizar_leccion(lesson_id, data))
    except ValueError as exc:
        return jsonify({"ok": False, "mensaje": str(exc)}), 400


@app.route("/api/admin/catalogo/evaluaciones", methods=["GET", "POST"])
def api_admin_catalogo_evaluaciones():
    err = _requiere_admin_json()
    if err:
        return err
    from catalog_service import crear_evaluacion, listar_evaluaciones_catalogo

    if request.method == "GET":
        return jsonify({"ok": True, "evaluaciones": listar_evaluaciones_catalogo()})

    data = request.get_json(silent=True) or {}
    try:
        return jsonify(crear_evaluacion(data))
    except ValueError as exc:
        return jsonify({"ok": False, "mensaje": str(exc)}), 400


@app.route("/api/admin/catalogo/evaluaciones/<int:ev_id>", methods=["GET", "PUT", "DELETE"])
def api_admin_catalogo_evaluacion(ev_id):
    err = _requiere_admin_json()
    if err:
        return err
    from catalog_service import (
        actualizar_evaluacion,
        eliminar_evaluacion,
        obtener_evaluacion_completa,
    )

    if request.method == "GET":
        ev = obtener_evaluacion_completa(ev_id)
        if not ev:
            return jsonify({"ok": False, "mensaje": "Evaluación no encontrada."}), 404
        return jsonify({"ok": True, "evaluacion": ev})

    if request.method == "DELETE":
        try:
            return jsonify(eliminar_evaluacion(ev_id))
        except ValueError as exc:
            return jsonify({"ok": False, "mensaje": str(exc)}), 400

    data = request.get_json(silent=True) or {}
    try:
        return jsonify(actualizar_evaluacion(ev_id, data))
    except ValueError as exc:
        return jsonify({"ok": False, "mensaje": str(exc)}), 400


@app.route("/api/admin/catalogo/evaluaciones/<int:ev_id>/preguntas", methods=["POST"])
def api_admin_catalogo_preguntas(ev_id):
    err = _requiere_admin_json()
    if err:
        return err
    from catalog_service import crear_pregunta

    data = request.get_json(silent=True) or {}
    try:
        return jsonify(crear_pregunta(ev_id, data))
    except ValueError as exc:
        return jsonify({"ok": False, "mensaje": str(exc)}), 400


@app.route("/api/admin/catalogo/preguntas/<int:pregunta_id>", methods=["PUT", "DELETE"])
def api_admin_catalogo_pregunta(pregunta_id):
    err = _requiere_admin_json()
    if err:
        return err
    from catalog_service import actualizar_pregunta, eliminar_pregunta

    if request.method == "DELETE":
        try:
            return jsonify(eliminar_pregunta(pregunta_id))
        except ValueError as exc:
            return jsonify({"ok": False, "mensaje": str(exc)}), 400

    data = request.get_json(silent=True) or {}
    try:
        return jsonify(actualizar_pregunta(pregunta_id, data))
    except ValueError as exc:
        return jsonify({"ok": False, "mensaje": str(exc)}), 400


@app.route("/api/admin/resumen-actividad", methods=["GET"])
def api_admin_resumen_actividad():
    err = _requiere_admin_json()
    if err:
        return err
    from admin_servicio import obtener_resumen_actividad_dashboard

    periodo = request.args.get("periodo", "30")
    if request.args.get("dias") == "7":
        periodo = "7"
    data = obtener_resumen_actividad_dashboard(periodo)
    return jsonify({"ok": True, "resumen": data})


@app.route("/api/admin/analytics", methods=["GET"])
def api_admin_analytics():
    err = _requiere_admin_json()
    if err:
        return err
    from admin_servicio import obtener_datos_analytics

    dias = request.args.get("dias", 30, type=int)
    data = obtener_datos_analytics(dias)
    data.pop("metricas_sqlite", None)
    data.pop("estado_bd", None)
    return jsonify({"ok": True, "analytics": data})


@app.route("/api/admin/estudiantes", methods=["GET"])
def api_admin_estudiantes():
    err = _requiere_admin_json()
    if err:
        return err
    from admin_servicio import listar_estudiantes_export

    return jsonify({"ok": True, "estudiantes": listar_estudiantes_export()})


@app.route("/api/admin/estudiantes/<int:id_usuario>/reporte", methods=["GET"])
def api_admin_reporte_estudiante(id_usuario):
    err = _requiere_admin_json()
    if err:
        return err
    from admin_servicio import obtener_reporte_estudiante

    tipo = request.args.get("tipo", "completo")
    desde = request.args.get("desde", "")
    hasta = request.args.get("hasta", "")
    try:
        reporte = obtener_reporte_estudiante(id_usuario, tipo, desde, hasta)
        return jsonify({"ok": True, "reporte": reporte})
    except ValueError as exc:
        return jsonify({"ok": False, "mensaje": str(exc)}), 400


@app.route("/api/admin/estudiantes/<int:id_usuario>", methods=["DELETE"])
def api_admin_eliminar_estudiante(id_usuario):
    err = _requiere_admin_json()
    if err:
        return err

    id_admin = session["id_usuario"]
    if id_usuario == id_admin:
        return jsonify({"ok": False, "mensaje": "No puedes eliminar tu propia cuenta."}), 400

    from extensions import db
    from models import User
    from nebula_data import eliminar_usuario_completo

    estudiante = db.session.get(User, id_usuario)
    if estudiante is None:
        return jsonify({"ok": False, "mensaje": "Estudiante no encontrado."}), 400
    if estudiante.id_rol != 2:
        return jsonify(
            {"ok": False, "mensaje": "Solo se pueden eliminar cuentas de estudiante."}
        ), 400

    try:
        eliminar_usuario_completo(id_usuario)
        app.logger.info(
            "Estudiante id=%s eliminado por admin id=%s", id_usuario, id_admin
        )
        return jsonify(
            {"ok": True, "mensaje": "Estudiante eliminado correctamente.", "id_usuario": id_usuario}
        )
    except ValueError as exc:
        app.logger.warning(
            "api_admin_eliminar_estudiante id=%s: %s", id_usuario, exc
        )
        return jsonify({"ok": False, "mensaje": str(exc)}), 400
    except RuntimeError as exc:
        if "usuarios" in str(exc).lower():
            app.logger.error(
                "api_admin_eliminar_estudiante: código antiguo (guardar_datos usuarios). "
                "Redespliega la última versión en Render."
            )
            return jsonify(
                {
                    "ok": False,
                    "mensaje": "El servidor usa una versión antigua. Redespliega el proyecto en Render.",
                }
            ), 500
        raise
    except Exception as exc:
        app.logger.exception("api_admin_eliminar_estudiante id=%s", id_usuario)
        detalle = str(exc).strip()
        mensaje = (
            f"No se pudo eliminar el estudiante: {detalle}"
            if detalle
            else "No se pudo eliminar el estudiante. Revisa los logs del servidor."
        )
        return jsonify({"ok": False, "mensaje": mensaje}), 500


@app.route("/api/admin/notificaciones", methods=["GET"])
def api_admin_notificaciones():
    err = _requiere_admin_json()
    if err:
        return err
    from notificaciones_admin_service import (
        listar_notificaciones_admin,
        sincronizar_desde_actividad_sistema,
    )

    sincronizar_desde_actividad_sistema()
    desde_id = request.args.get("desde_id", type=int)
    payload = listar_notificaciones_admin(
        limite=50,
        desde_id=desde_id if desde_id else None,
    )
    return jsonify({"ok": True, **payload})


@app.route("/api/admin/notificaciones/<int:id_notificacion>/leer", methods=["POST"])
def api_admin_notificacion_leer(id_notificacion):
    err = _requiere_admin_json()
    if err:
        return err
    from notificaciones_admin_service import listar_notificaciones_admin, marcar_leida

    if not marcar_leida(id_notificacion):
        return jsonify({"ok": False, "mensaje": "Notificación no encontrada."}), 404
    resumen = listar_notificaciones_admin(limite=50)
    return jsonify({"ok": True, "no_leidas": resumen["no_leidas"]})


@app.route("/api/admin/notificaciones/leer-todas", methods=["POST"])
def api_admin_notificaciones_leer_todas():
    err = _requiere_admin_json()
    if err:
        return err
    from notificaciones_admin_service import marcar_todas_leidas

    count = marcar_todas_leidas()
    return jsonify({"ok": True, "marcadas": count, "no_leidas": 0})


@app.route("/api/admin/estudiantes/<int:id_usuario>/suspender", methods=["POST"])
def api_admin_suspender_estudiante(id_usuario):
    err = _requiere_admin_json()
    if err:
        return err
    from admin_servicio import suspender_estudiante

    activo = request.get_json(silent=True) or {}
    nuevo_estado = activo.get("activo", False)
    try:
        usuario = suspender_estudiante(id_usuario, session["id_usuario"], bool(nuevo_estado))
        return jsonify({"ok": True, "usuario": usuario, "mensaje": "Estado actualizado."})
    except ValueError as exc:
        return jsonify({"ok": False, "mensaje": str(exc)}), 400


# ——— API Recursos académicos (PDFs por materia) ———
RECURSOS_MATERIAS_CARPETAS = frozenset({"matematicas", "ciencia", "historia", "lenguaje"})


def _carpeta_recursos_pdf(materia):
    """Ruta absoluta: static/resources/{materia}/ (equivalente a /public/resources en Next)."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "resources", materia)


def _asegurar_pdfs_recursos():
    """Crea PDFs de ejemplo si faltan (evita error 'no disponible' en instalaciones nuevas)."""
    try:
        from generar_pdfs_recursos import RECURSOS, pdf_minimo

        for carpeta, archivo, titulo in RECURSOS:
            dir_path = _carpeta_recursos_pdf(carpeta)
            os.makedirs(dir_path, exist_ok=True)
            ruta = os.path.join(dir_path, archivo)
            if not os.path.isfile(ruta):
                with open(ruta, "wb") as f:
                    f.write(pdf_minimo(titulo))
                app.logger.info("PDF recurso creado: %s", ruta)
    except Exception as exc:
        app.logger.warning("No se pudieron asegurar PDFs de recursos: %s", exc)


_asegurar_pdfs_recursos()

try:
    from perfil_service import asegurar_carpeta_fotos

    asegurar_carpeta_fotos()
except Exception:
    pass


@app.route("/api/recursos/descargar/<materia>/<path:archivo>", methods=["GET", "HEAD"])
def api_descargar_recurso_pdf(materia, archivo):
    """Sirve PDF con Content-Disposition; HEAD valida existencia sin transferir cuerpo."""
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401

    if materia not in RECURSOS_MATERIAS_CARPETAS:
        return jsonify({"ok": False, "mensaje": "Materia no válida."}), 400

    if ".." in archivo or "\\" in archivo:
        return jsonify({"ok": False, "mensaje": "Nombre de archivo no válido."}), 400

    if not archivo.lower().endswith(".pdf"):
        return jsonify({"ok": False, "mensaje": "Solo se permiten archivos PDF."}), 400

    carpeta = _carpeta_recursos_pdf(materia)
    ruta_completa = os.path.join(carpeta, archivo)

    if not os.path.isfile(ruta_completa):
        return jsonify(
            {"ok": False, "mensaje": "El PDF de este recurso no está disponible."}
        ), 404

    if request.method == "HEAD":
        return "", 200

    return send_from_directory(
        carpeta,
        archivo,
        as_attachment=True,
        download_name=archivo,
        mimetype="application/pdf",
    )


@app.route("/api/recursos/estadistica", methods=["POST"])
def api_recurso_estadistica():
    """Registro ligero de descargas (futuro: analytics / Storage remoto)."""
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401

    data = request.get_json(silent=True) or {}
    registro = {
        "id_usuario": session["id_usuario"],
        "recurso_id": data.get("recurso_id"),
        "titulo": data.get("titulo"),
        "materia": data.get("materia"),
        "category": data.get("category"),
        "type": data.get("type"),
        "url": data.get("url"),
        "accion": data.get("accion"),
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    historial = cargar_datos("recursos_descargas")
    registro["id"] = generar_id(historial, "id")
    historial.append(registro)
    guardar_datos("recursos_descargas", historial[-500:])

    return jsonify({"ok": True})


# Dominios permitidos para proxy de PDF (evita abuso del endpoint)
RECURSOS_DOMINIOS_PERMITIDOS = frozenset(
    {
        "edwebcontent.ed.ac.uk",
        "phet.colorado.edu",
        "www.britannica.com",
        "quizlet.com",
        "www.khanacademy.org",
        "education.nationalgeographic.org",
        "www.bbc.co.uk",
    }
)


@app.route("/api/recursos/proxy")
def api_recurso_proxy():
    """
    Descarga PDF externo en el servidor y lo entrega al cliente (sin CORS).
    Solo HTTPS y dominios en lista blanca.
    """
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401

    url = (request.args.get("url") or "").strip()
    nombre = (request.args.get("nombre") or "recurso.pdf").replace('"', "")

    if not url.startswith("https://"):
        return jsonify({"ok": False, "mensaje": "URL no válida (solo HTTPS)."}), 400

    host = urlparse(url).netloc.lower()
    if host not in RECURSOS_DOMINIOS_PERMITIDOS:
        return jsonify({"ok": False, "mensaje": "Dominio del recurso no autorizado."}), 403

    try:
        peticion = urllib.request.Request(
            url,
            headers={"User-Agent": "NebulaAI-Estudiante/1.0"},
        )
        with urllib.request.urlopen(peticion, timeout=45) as respuesta:
            datos = respuesta.read()
            content_type = respuesta.headers.get("Content-Type", "application/pdf")
    except urllib.error.HTTPError as exc:
        app.logger.warning("Proxy recurso HTTP %s: %s", url, exc)
        return jsonify({"ok": False, "mensaje": "El recurso remoto no está disponible."}), 502
    except Exception as exc:
        app.logger.warning("Proxy recurso error %s: %s", url, exc)
        return jsonify({"ok": False, "mensaje": "No se pudo descargar el recurso."}), 502

    if not datos:
        return jsonify({"ok": False, "mensaje": "El archivo está vacío."}), 502

    return Response(
        datos,
        mimetype=content_type.split(";")[0].strip() or "application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{nombre}"',
            "Cache-Control": "private, max-age=3600",
        },
    )


# ——— API Racha diaria ———
@app.route("/api/plan_estudios/metas", methods=["GET", "POST"])
def api_plan_metas():
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401

    from metas_service import guardar_meta, listar_metas_usuario

    id_usuario = session["id_usuario"]
    actividades = cargar_datos("actividades")

    if request.method == "GET":
        return jsonify({"ok": True, "metas": listar_metas_usuario(actividades, id_usuario)})

    payload = request.get_json(silent=True) or request.form.to_dict()
    try:
        meta = guardar_meta(
            actividades,
            id_usuario,
            payload,
            lambda arr, k: generar_id(arr, k),
        )
        guardar_datos("actividades", actividades)
        if not (payload.get("id_actividad") or payload.get("id")):
            registrar_actividad_sistema(
                "meta_creada",
                id_usuario,
                "Meta personalizada creada",
                f"{session.get('nombre', 'Estudiante')} creó la meta «{meta.get('titulo', 'Sin título')}»",
            )
        return jsonify({"ok": True, "meta": meta, "mensaje": "Meta guardada."})
    except ValueError as exc:
        return jsonify({"ok": False, "mensaje": str(exc)}), 400


@app.route("/api/plan_estudios/metas/<int:id_actividad>", methods=["PUT", "DELETE"])
def api_plan_meta(id_actividad):
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401

    from metas_service import eliminar_meta, guardar_meta, listar_metas_usuario

    id_usuario = session["id_usuario"]
    actividades = cargar_datos("actividades")

    if request.method == "DELETE":
        if not eliminar_meta(actividades, id_usuario, id_actividad):
            return jsonify({"ok": False, "mensaje": "Meta no encontrada."}), 404
        guardar_datos("actividades", actividades)
        return jsonify({"ok": True, "mensaje": "Meta eliminada."})

    payload = request.get_json(silent=True) or {}
    payload["id_actividad"] = id_actividad
    try:
        meta = guardar_meta(
            actividades,
            id_usuario,
            payload,
            lambda arr, k: generar_id(arr, k),
        )
        guardar_datos("actividades", actividades)
        return jsonify({"ok": True, "meta": meta, "mensaje": "Meta actualizada."})
    except ValueError as exc:
        return jsonify({"ok": False, "mensaje": str(exc)}), 400


@app.route("/api/plan_estudios/racha", methods=["GET"])
def api_racha_estado():
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401
    sincronizar = request.args.get("sincronizar", "1") != "0"
    estado = obtener_estado_racha(session["id_usuario"], sincronizar_sistema=sincronizar)
    return jsonify(estado)


@app.route("/api/plan_estudios/racha/sincronizar", methods=["POST"])
def api_racha_sincronizar():
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401
    resultado = sincronizar_y_validar_hoy(session["id_usuario"])
    status = 200 if resultado.get("ok") else 200
    return jsonify(resultado), status


@app.route("/api/plan_estudios/racha/actividad", methods=["POST"])
def api_racha_actividad():
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401
    data = request.get_json(silent=True) or {}
    tipo = data.get("tipo", "").strip()
    metadata = data.get("metadata") or {}
    minutos = int(data.get("minutos_estudio") or 0)
    resultado = registrar_actividad_racha(
        session["id_usuario"], tipo, metadata, minutos_estudio=minutos
    )
    if not resultado.get("ok"):
        return jsonify(resultado), 400
    return jsonify(resultado)


@app.route("/api/plan_estudios/racha/resumen", methods=["GET"])
def api_racha_resumen():
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401
    return jsonify(obtener_resumen_racha(session["id_usuario"]))


@app.route("/api/plan_estudios/racha/registrar", methods=["POST"])
def api_racha_registrar_legacy():
    """Compatibilidad: delega en sincronizar + validar actividad real."""
    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Debes iniciar sesión."}), 401
    return jsonify(sincronizar_y_validar_hoy(session["id_usuario"]))


@app.errorhandler(500)
def manejar_error_interno(error):
    app.logger.exception(
        "Error 500 %s %s: %s",
        request.method,
        request.path,
        error,
    )
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "mensaje": "Error interno del servidor."}), 500
    return (
        "Error interno. Revisa los logs en Render o contacta al administrador.",
        500,
    )


@app.errorhandler(404)
def manejar_no_encontrado(error):
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "mensaje": "Recurso no encontrado."}), 404
    return redirect(url_for("login"))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    log_estado_openai()
    print(
        "API KEY:",
        "CONFIGURADA" if openai_configurado() else "NO CONFIGURADA",
        f"(archivo: {nebula_config.ENV_PATH})",
    )

    app.run(debug=True)