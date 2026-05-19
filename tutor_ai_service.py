"""
Servicio Tutor IA — Nébula AI
Chat conversacional, límites por plan, contexto académico, OpenAI (opcional).
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import uuid
from datetime import date, datetime
from typing import Callable, Generator, Optional

import nebula_config
from tutor_ai_openai import (
    TutorOpenAIClientError,
    completar_chat_con_reintentos,
    stream_chat_con_reintentos,
    verificar_conectividad_openai,
)

logger = logging.getLogger("nebula.tutor_ai")

DATA_DIR = "data"
ARCHIVO_SESIONES = "tutor_sesiones.json"
ARCHIVO_USO = "tutor_uso_diario.json"
ARCHIVO_LOGS = "tutor_logs.json"

# Límites plan gratuito (estudiante)
LIMITES_FREE = {
    "mensajes_dia": 40,
    "quizzes_dia": 5,
    "cooldown_segundos": 2,
    "max_tokens_respuesta": 1200,
    "memoria_mensajes": 16,
}

# Plan premium / admin
LIMITES_PRO = {
    "mensajes_dia": 500,
    "quizzes_dia": 50,
    "cooldown_segundos": 0,
    "max_tokens_respuesta": 4096,
    "memoria_mensajes": 40,
}

TEMA_DEFAULT = {
    "titulo": "Cálculo II: Series de Taylor",
    "materia": "matematicas",
    "descripcion": "Series de Taylor y Maclaurin, convergencia y aplicaciones",
}

MATERIA_ETIQUETAS = {
    "matematicas": "Matemáticas",
    "ciencia": "Ciencias",
    "historia": "Historia",
    "lenguaje": "Lenguaje",
}

SYSTEM_PROMPT_BASE = """Eres Nébula, tutor académico de la plataforma Nébula AI.
Responde en español, de forma clara, motivadora y pedagógica.
Puedes explicar matemáticas, ciencias, historia y lenguaje.
Usa Markdown ligero y LaTeX entre $...$ o $$...$$ para fórmulas.
Da pasos numerados cuando resuelvas problemas.
Adapta la dificultad al nivel del estudiante.
Tema actual del curso: {tema_titulo} — {tema_descripcion}.
Materia: {materia}.
Progreso del estudiante: {progreso_resumen}.
"""

class TutorAIError(Exception):
    """Error de configuración o de la API de OpenAI."""

    def __init__(self, mensaje: str, codigo: str = "error", retryable: bool = False):
        self.codigo = codigo
        self.retryable = retryable
        super().__init__(mensaje)


_ARCHIVO_LOCKS: dict[str, threading.Lock] = {}
_OPENAI_SEM = threading.Semaphore(8)


def openai_disponible() -> bool:
    return nebula_config.openai_configurado()


def asegurar_openai() -> None:
    if not openai_disponible():
        env_file = getattr(nebula_config, "ENV_PATH", ".env")
        raise TutorAIError(
            "El tutor IA no está configurado. Edita el archivo .env en la raíz del proyecto, "
            f"define OPENAI_API_KEY=sk-... (sin espacios) en {env_file}, "
            "guarda los cambios y reinicia el servidor Flask."
        )


QUICK_PROMPTS = {
    "explain": "Explica de forma clara y simplificada el concepto central del tema actual ({tema}). Incluye un ejemplo y una analogía.",
    "quiz": "Genera un mini cuestionario de exactamente 5 preguntas sobre el tema actual ({tema}), con opciones A-D y al final las respuestas correctas brevemente.",
    "summary": "Genera un resumen del día de estudio sobre el tema ({tema}): puntos clave, fórmulas importantes si aplican, y 3 ideas para repasar mañana.",
}


def _asegurar_data_dir() -> None:
    """Crea data/ si no existe (evita fallos al guardar JSON)."""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except OSError as exc:
        logger.exception("No se pudo crear el directorio %s: %s", DATA_DIR, exc)
        raise TutorAIError(
            "No se pudo inicializar el almacenamiento del tutor. Contacta al administrador."
        ) from exc


def _ruta(nombre: str) -> str:
    _asegurar_data_dir()
    return os.path.join(DATA_DIR, nombre)


def _lock_archivo(nombre: str) -> threading.RLock:
    if nombre not in _ARCHIVO_LOCKS:
        _ARCHIVO_LOCKS[nombre] = threading.RLock()
    return _ARCHIVO_LOCKS[nombre]


def _coleccion_tutor(nombre_archivo: str) -> str:
    mapping = {
        ARCHIVO_SESIONES: "tutor_sesiones",
        ARCHIVO_USO: "tutor_uso_diario",
        ARCHIVO_LOGS: "tutor_logs",
    }
    col = mapping.get(nombre_archivo)
    if not col:
        raise ValueError(f"Archivo tutor desconocido: {nombre_archivo}")
    return col


def _cargar_lista(nombre: str) -> list:
    from nebula_data import cargar_datos

    with _lock_archivo(nombre):
        try:
            datos = cargar_datos(_coleccion_tutor(nombre))
            return datos if isinstance(datos, list) else []
        except Exception as exc:
            logger.exception("Error leyendo tutor %s", nombre)
            raise TutorAIError(
                "No se pudo leer el historial del tutor. Intenta de nuevo.",
                codigo="storage",
            ) from exc


def _guardar_lista(nombre: str, datos: list) -> None:
    from nebula_data import guardar_datos

    with _lock_archivo(nombre):
        try:
            guardar_datos(_coleccion_tutor(nombre), datos)
        except Exception as exc:
            logger.exception("Error guardando tutor %s", nombre)
            raise TutorAIError(
                "No se pudo guardar la conversación. Intenta de nuevo.",
                codigo="storage",
            ) from exc


def etiqueta_materia(slug: str) -> str:
    if not slug:
        return "General"
    return MATERIA_ETIQUETAS.get(slug.lower(), slug.replace("_", " ").capitalize())


def mensaje_error_amigable(exc: Exception) -> str:
    """Mensaje para el cliente; detalle técnico solo en logs."""
    if isinstance(exc, TutorAIError):
        return str(exc)
    if isinstance(exc, TutorOpenAIClientError):
        return exc.info.mensaje
    logger.exception("Error interno Tutor IA: %s", exc)
    from tutor_ai_openai import clasificar_error_openai

    return clasificar_error_openai(exc).mensaje


def error_respuesta_dict(exc: Exception) -> dict:
    if isinstance(exc, TutorAIError):
        return {
            "ok": False,
            "mensaje": str(exc),
            "codigo": exc.codigo,
            "retryable": exc.retryable,
        }
    if isinstance(exc, TutorOpenAIClientError):
        return {"ok": False, **exc.info.a_dict()}
    from tutor_ai_openai import clasificar_error_openai

    info = clasificar_error_openai(exc)
    return {"ok": False, **info.a_dict()}


def respuesta_error_api(exc: Exception) -> dict:
    return error_respuesta_dict(exc)


def diagnosticar_tutor_ia() -> dict:
    return verificar_conectividad_openai()


def es_usuario_pro(usuario: Optional[dict]) -> bool:
    if not usuario:
        return False
    if usuario.get("id_rol") == 1:
        return True
    plan = usuario.get("plan")
    if not plan:
        plan = (usuario.get("preferencias_aprendizaje") or {}).get("plan")
    return str(plan or "").strip().lower() in ("pro", "premium")


def obtener_limites(usuario: Optional[dict]) -> dict:
    return LIMITES_PRO if es_usuario_pro(usuario) else LIMITES_FREE


def sanitizar_entrada(texto: str, max_len: int = 4000) -> str:
    """Limpia prompt del usuario (sin escapar HTML; el frontend sanitiza al renderizar)."""
    if not texto:
        return ""
    texto = texto.strip()[:max_len]
    texto = re.sub(r"<script[^>]*>.*?</script>", "", texto, flags=re.I | re.S)
    return texto


def _hoy() -> str:
    return date.today().isoformat()


def _obtener_uso_hoy(id_usuario: int) -> dict:
    registros = _cargar_lista(ARCHIVO_USO)
    hoy = _hoy()
    for r in registros:
        if r.get("id_usuario") == id_usuario and r.get("fecha") == hoy:
            return r
    nuevo = {
        "id_usuario": id_usuario,
        "fecha": hoy,
        "mensajes": 0,
        "quizzes": 0,
        "ultimo_mensaje_at": None,
    }
    registros.append(nuevo)
    _guardar_lista(ARCHIVO_USO, registros)
    return nuevo


def _guardar_uso(uso: dict) -> None:
    registros = _cargar_lista(ARCHIVO_USO)
    for i, r in enumerate(registros):
        if r.get("id_usuario") == uso.get("id_usuario") and r.get("fecha") == uso.get("fecha"):
            registros[i] = uso
            _guardar_lista(ARCHIVO_USO, registros)
            return
    registros.append(uso)
    _guardar_lista(ARCHIVO_USO, registros)


def verificar_limites(id_usuario: int, usuario: dict, es_quiz: bool = False) -> Optional[dict]:
    """Retorna dict de error con codigo si aplica; None si OK."""
    limites = obtener_limites(usuario)
    uso = _obtener_uso_hoy(id_usuario)

    if es_quiz and uso.get("quizzes", 0) >= limites["quizzes_dia"]:
        return {
            "codigo": "limite_quiz",
            "mensaje": f"Has alcanzado el límite de {limites['quizzes_dia']} cuestionarios hoy.",
            "retryable": False,
        }

    if uso.get("mensajes", 0) >= limites["mensajes_dia"]:
        return {
            "codigo": "limite_diario",
            "mensaje": f"Has alcanzado el límite de {limites['mensajes_dia']} mensajes diarios.",
            "retryable": False,
        }

    cooldown = limites.get("cooldown_segundos", 0)
    if cooldown > 0:
        ultimo = uso.get("ultimo_mensaje_at")
        if ultimo:
            try:
                t0 = datetime.fromisoformat(ultimo)
                delta = (datetime.now() - t0).total_seconds()
                if delta < cooldown:
                    espera = max(1, int(cooldown - delta) + 1)
                    return {
                        "codigo": "cooldown",
                        "mensaje": f"Espera {espera}s antes de enviar otra pregunta.",
                        "retryable": True,
                        "retry_after": float(espera),
                    }
            except (TypeError, ValueError):
                pass
    return None


def registrar_uso_mensaje(id_usuario: int, es_quiz: bool = False) -> None:
    uso = _obtener_uso_hoy(id_usuario)
    uso["mensajes"] = uso.get("mensajes", 0) + 1
    if es_quiz:
        uso["quizzes"] = uso.get("quizzes", 0) + 1
    uso["ultimo_mensaje_at"] = datetime.now().isoformat()
    _guardar_uso(uso)


def _log_evento(id_usuario: int, tipo: str, detalle: str) -> None:
    logs = _cargar_lista(ARCHIVO_LOGS)
    logs.append(
        {
            "id": str(uuid.uuid4()),
            "id_usuario": id_usuario,
            "tipo": tipo,
            "detalle": detalle[:500],
            "fecha": datetime.now().isoformat(),
        }
    )
    _guardar_lista(ARCHIVO_LOGS, logs[-300:])


def construir_contexto_academico(id_usuario: int, tema: Optional[dict] = None) -> dict:
    tema = tema or TEMA_DEFAULT.copy()
    progreso_resumen = "Estudiante activo en la plataforma."
    try:
        from app import listar_cursos_catalogo_usuario, obtener_datos_progreso_usuario

        cursos = listar_cursos_catalogo_usuario(id_usuario)
        datos = obtener_datos_progreso_usuario(id_usuario)
        if cursos:
            curso = cursos[0]
            tema["titulo"] = tema.get("titulo") or curso.get("titulo", TEMA_DEFAULT["titulo"])
            progreso_resumen = (
                f"{datos.get('lecciones_completadas', 0)} lecciones completadas; "
                f"curso destacado: {curso.get('titulo')} ({curso.get('porcentaje', 0)}%)."
            )
    except Exception:
        pass
    return {**tema, "progreso_resumen": progreso_resumen}


def _system_prompt(contexto: dict) -> str:
    return SYSTEM_PROMPT_BASE.format(
        tema_titulo=contexto.get("titulo", TEMA_DEFAULT["titulo"]),
        tema_descripcion=contexto.get("descripcion", ""),
        materia=contexto.get("materia", "general"),
        progreso_resumen=contexto.get("progreso_resumen", ""),
    )


def obtener_sesion(session_id: str, id_usuario: int) -> Optional[dict]:
    for s in _cargar_lista(ARCHIVO_SESIONES):
        if s.get("session_id") == session_id and s.get("id_usuario") == id_usuario:
            return s
    return None


def crear_sesion(id_usuario: int, contexto: Optional[dict] = None) -> dict:
    contexto = construir_contexto_academico(id_usuario, contexto)
    sesion = {
        "session_id": str(uuid.uuid4()),
        "id_usuario": id_usuario,
        "titulo": contexto.get("titulo", TEMA_DEFAULT["titulo"]),
        "contexto": contexto,
        "mensajes": [
            {
                "role": "assistant",
                "content": _mensaje_bienvenida(contexto),
                "created_at": datetime.now().isoformat(),
            }
        ],
        "creada_at": datetime.now().isoformat(),
        "actualizada_at": datetime.now().isoformat(),
    }
    sesiones = _cargar_lista(ARCHIVO_SESIONES)
    sesiones.append(sesion)
    _guardar_lista(ARCHIVO_SESIONES, sesiones[-200:])
    return sesion


def listar_sesiones_recientes(id_usuario: int, limite: int = 10) -> list:
    sesiones = [s for s in _cargar_lista(ARCHIVO_SESIONES) if s.get("id_usuario") == id_usuario]
    sesiones.sort(key=lambda x: x.get("actualizada_at", ""), reverse=True)
    return [
        {
            "session_id": s["session_id"],
            "titulo": s.get("titulo", "Chat"),
            "actualizada_at": s.get("actualizada_at"),
        }
        for s in sesiones[:limite]
    ]


def _mensaje_bienvenida(contexto: dict) -> str:
    titulo = contexto.get("titulo", TEMA_DEFAULT["titulo"])
    return (
        f"¡Hola! Soy **Nébula**, tu tutor de {titulo}. "
        "Puedo explicar conceptos, resolver dudas paso a paso, generar ejemplos, "
        "mini cuestionarios y resúmenes. ¿En qué te ayudo hoy?"
    )


def _historial_para_modelo(sesion: dict, limites: dict) -> list[dict]:
    mensajes = sesion.get("mensajes", [])
    max_msgs = limites.get("memoria_mensajes", 16)
    recientes = mensajes[-max_msgs:]
    return [
        {"role": m["role"], "content": m["content"]}
        for m in recientes
        if m.get("role") in ("user", "assistant") and m.get("content")
    ]


def _construir_mensajes_openai(
    sesion: dict,
    usuario: dict,
    mensaje_usuario: Optional[str] = None,
) -> tuple[list[dict], dict]:
    """Arma el payload para Chat Completions sin duplicar el último mensaje del usuario."""
    limites = obtener_limites(usuario)
    contexto = sesion.get("contexto", TEMA_DEFAULT)
    messages: list[dict] = [{"role": "system", "content": _system_prompt(contexto)}]
    historial = _historial_para_modelo(sesion, limites)

    if mensaje_usuario:
        if (
            historial
            and historial[-1].get("role") == "user"
            and historial[-1].get("content") == mensaje_usuario
        ):
            messages.extend(historial)
        else:
            messages.extend(historial)
            messages.append({"role": "user", "content": mensaje_usuario})
    else:
        messages.extend(historial)

    return messages, limites


def generar_respuesta_ia(
    sesion: dict,
    mensaje_usuario: str,
    usuario: dict,
    es_quiz: bool = False,
) -> str:
    asegurar_openai()
    messages, limites = _construir_mensajes_openai(sesion, usuario, mensaje_usuario)
    id_u = sesion.get("id_usuario", 0)

    try:
        with _OPENAI_SEM:
            return completar_chat_con_reintentos(
                messages,
                max_tokens=limites["max_tokens_respuesta"],
            )
    except TutorOpenAIClientError as exc:
        _log_evento(id_u, "openai_error", f"{exc.info.codigo}: {exc.info.tecnico[:200]}")
        raise TutorAIError(exc.info.mensaje, codigo=exc.info.codigo, retryable=exc.info.retryable) from exc
    except ImportError as exc:
        raise TutorAIError(
            "Falta el paquete openai. Ejecuta: pip install -r requirements.txt",
            codigo="config",
        ) from exc


def stream_respuesta_ia(
    sesion: dict,
    mensaje_usuario: str,
    usuario: dict,
    on_status: Optional[Callable[[str, str], None]] = None,
) -> Generator[str, None, None]:
    """Fragmentos de texto para SSE."""
    asegurar_openai()
    messages, limites = _construir_mensajes_openai(sesion, usuario, mensaje_usuario)
    id_u = sesion.get("id_usuario", 0)

    try:
        with _OPENAI_SEM:
            yield from stream_chat_con_reintentos(
                messages,
                max_tokens=limites["max_tokens_respuesta"],
                on_status=on_status,
            )
    except TutorOpenAIClientError as exc:
        _log_evento(id_u, "openai_stream_error", f"{exc.info.codigo}: {exc.info.tecnico[:200]}")
        raise TutorAIError(exc.info.mensaje, codigo=exc.info.codigo, retryable=exc.info.retryable) from exc
    except ImportError as exc:
        raise TutorAIError(
            "Falta el paquete openai. Ejecuta: pip install -r requirements.txt",
            codigo="config",
        ) from exc


def agregar_mensaje_sesion(
    session_id: str,
    id_usuario: int,
    role: str,
    content: str,
) -> Optional[dict]:
    sesiones = _cargar_lista(ARCHIVO_SESIONES)
    for i, s in enumerate(sesiones):
        if s.get("session_id") == session_id and s.get("id_usuario") == id_usuario:
            s.setdefault("mensajes", []).append(
                {
                    "role": role,
                    "content": content,
                    "created_at": datetime.now().isoformat(),
                }
            )
            s["actualizada_at"] = datetime.now().isoformat()
            sesiones[i] = s
            _guardar_lista(ARCHIVO_SESIONES, sesiones)
            return s
    return None


def procesar_mensaje(
    session_id: str,
    id_usuario: int,
    usuario: dict,
    texto: str,
    es_quiz: bool = False,
) -> dict:
    error = verificar_limites(id_usuario, usuario, es_quiz=es_quiz)
    if error:
        return {"ok": False, **error}

    texto = sanitizar_entrada(texto)
    if len(texto) < 1:
        return {"ok": False, "mensaje": "Escribe un mensaje válido."}

    sesion = obtener_sesion(session_id, id_usuario)
    if not sesion:
        return {"ok": False, "mensaje": "Sesión no encontrada."}

    agregar_mensaje_sesion(session_id, id_usuario, "user", texto)
    sesion = obtener_sesion(session_id, id_usuario)
    try:
        respuesta = generar_respuesta_ia(sesion, texto, usuario, es_quiz=es_quiz)
    except TutorAIError as exc:
        return {
            "ok": False,
            "mensaje": str(exc),
            "codigo": exc.codigo,
            "retryable": exc.retryable,
        }
    agregar_mensaje_sesion(session_id, id_usuario, "assistant", respuesta)
    registrar_uso_mensaje(id_usuario, es_quiz=es_quiz)
    _log_evento(id_usuario, "mensaje", f"session={session_id}")

    uso = _obtener_uso_hoy(id_usuario)
    limites = obtener_limites(usuario)
    return {
        "ok": True,
        "respuesta": respuesta,
        "session_id": session_id,
        "limites": {
            "mensajes_usados": uso.get("mensajes", 0),
            "mensajes_max": limites["mensajes_dia"],
            "es_pro": es_usuario_pro(usuario),
        },
    }


def accion_rapida(
    session_id: str,
    id_usuario: int,
    usuario: dict,
    accion: str,
) -> dict:
    prompts = {"explain": "explain", "quiz": "quiz", "summary": "summary"}
    key = prompts.get(accion)
    if not key:
        return {"ok": False, "mensaje": "Acción no válida."}

    sesion = obtener_sesion(session_id, id_usuario)
    if not sesion:
        return {"ok": False, "mensaje": "Sesión no encontrada."}

    tema = sesion.get("contexto", {}).get("titulo", TEMA_DEFAULT["titulo"])
    plantilla = QUICK_PROMPTS[key]
    prompt = plantilla.format(tema=tema)
    es_quiz = key == "quiz"
    return procesar_mensaje(session_id, id_usuario, usuario, prompt, es_quiz=es_quiz)


def estado_limites_ui(id_usuario: int, usuario: dict) -> dict:
    uso = _obtener_uso_hoy(id_usuario)
    limites = obtener_limites(usuario)
    return {
        "es_pro": es_usuario_pro(usuario),
        "mensajes_usados": uso.get("mensajes", 0),
        "mensajes_max": limites["mensajes_dia"],
        "quizzes_usados": uso.get("quizzes", 0),
        "quizzes_max": limites["quizzes_dia"],
        "cooldown_segundos": limites["cooldown_segundos"],
    }
