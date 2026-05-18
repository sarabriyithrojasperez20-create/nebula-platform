"""
Cliente OpenAI del Tutor IA: clasificación de errores, reintentos y timeouts.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Generator, Optional

import nebula_config

logger = logging.getLogger("nebula.tutor_ai.openai")

OPENAI_TIMEOUT_SEC = 90.0
MAX_REINTENTOS = 3
BACKOFF_BASE_SEC = 1.2


@dataclass
class ErrorOpenAI:
    codigo: str
    mensaje: str
    retryable: bool
    retry_after: Optional[float] = None
    tecnico: str = ""

    def a_dict(self) -> dict:
        return {
            "codigo": self.codigo,
            "mensaje": self.mensaje,
            "retryable": self.retryable,
            "retry_after": self.retry_after,
        }


def _extraer_texto_error(exc: Exception) -> str:
    partes = [str(exc)]
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        err = body.get("error") or {}
        if isinstance(err, dict):
            partes.append(str(err.get("message", "")))
            partes.append(str(err.get("type", "")))
            partes.append(str(err.get("code", "")))
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            partes.append(str(getattr(response, "text", "") or ""))
        except Exception:
            pass
    return " ".join(p for p in partes if p).lower()


def clasificar_error_openai(exc: Exception) -> ErrorOpenAI:
    """Clasifica excepciones OpenAI/SDK sin confundir cuota agotada con rate limit temporal."""
    tecnico = repr(exc)[:500]
    raw = _extraer_texto_error(exc)

    try:
        from openai import (
            APIConnectionError,
            APITimeoutError,
            AuthenticationError,
            BadRequestError,
            InternalServerError,
            RateLimitError,
        )
    except ImportError:
        RateLimitError = AuthenticationError = APITimeoutError = APIConnectionError = ()
        InternalServerError = BadRequestError = ()

    if isinstance(exc, AuthenticationError):
        return ErrorOpenAI(
            codigo="auth",
            mensaje=(
                "El tutor IA no está configurado correctamente en el servidor. "
                "Contacta al administrador."
            ),
            retryable=False,
            tecnico=tecnico,
        )

    if isinstance(exc, APITimeoutError):
        return ErrorOpenAI(
            codigo="timeout",
            mensaje="La respuesta tardó más de lo esperado. Intenta de nuevo en unos segundos.",
            retryable=True,
            tecnico=tecnico,
        )

    if isinstance(exc, APIConnectionError):
        return ErrorOpenAI(
            codigo="network",
            mensaje="No pudimos conectar con el servicio de IA. Reintentando…",
            retryable=True,
            tecnico=tecnico,
        )

    if isinstance(exc, InternalServerError):
        return ErrorOpenAI(
            codigo="overloaded",
            mensaje="El servicio de IA está ocupado. Estamos reintentando automáticamente…",
            retryable=True,
            tecnico=tecnico,
        )

    if isinstance(exc, RateLimitError):
        if any(
            t in raw
            for t in (
                "insufficient_quota",
                "exceeded your current quota",
                "billing",
                "payment",
                "quota",
            )
        ):
            return ErrorOpenAI(
                codigo="quota",
                mensaje=(
                    "La cuota de la API de IA está agotada. El administrador debe revisar "
                    "la facturación de OpenAI o actualizar OPENAI_API_KEY en .env."
                ),
                retryable=False,
                tecnico=tecnico,
            )
        retry_after = getattr(exc, "retry_after", None) or _parsear_retry_after(raw)
        return ErrorOpenAI(
            codigo="rate_limit",
            mensaje="Muchas solicitudes en poco tiempo. Reintentando conexión…",
            retryable=True,
            retry_after=retry_after,
            tecnico=tecnico,
        )

    # Heurística por texto (excepciones genéricas)
    if any(t in raw for t in ("insufficient_quota", "exceeded your current quota", "billing hard limit")):
        return ErrorOpenAI(
            codigo="quota",
            mensaje=(
                "La cuota de la API de IA está agotada. Revisa la facturación en OpenAI "
                "o actualiza la clave en el servidor."
            ),
            retryable=False,
            tecnico=tecnico,
        )

    if "429" in raw or "rate_limit" in raw or "rate limit" in raw:
        return ErrorOpenAI(
            codigo="rate_limit",
            mensaje="Reintentando conexión con el tutor IA…",
            retryable=True,
            retry_after=_parsear_retry_after(raw),
            tecnico=tecnico,
        )

    if any(t in raw for t in ("timeout", "timed out")):
        return ErrorOpenAI(
            codigo="timeout",
            mensaje="La respuesta puede tardar unos segundos. Reintentando…",
            retryable=True,
            tecnico=tecnico,
        )

    if any(t in raw for t in ("503", "overloaded", "502", "504")):
        return ErrorOpenAI(
            codigo="overloaded",
            mensaje="El servicio de IA está ocupado. Reintentando automáticamente…",
            retryable=True,
            tecnico=tecnico,
        )

    if any(t in raw for t in ("401", "invalid_api_key", "incorrect api key", "authentication")):
        return ErrorOpenAI(
            codigo="auth",
            mensaje="Problema de autenticación con la API de IA. Contacta al administrador.",
            retryable=False,
            tecnico=tecnico,
        )

    return ErrorOpenAI(
        codigo="unknown",
        mensaje="No pudimos obtener una respuesta ahora. Intenta de nuevo en unos segundos.",
        retryable=True,
        tecnico=tecnico,
    )


def _parsear_retry_after(raw: str) -> Optional[float]:
    import re

    m = re.search(r"retry[- ]?after[:\s]+(\d+(?:\.\d+)?)", raw)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return None


def _espera_reintento(intento: int, info: ErrorOpenAI) -> float:
    if info.retry_after and info.retry_after > 0:
        return min(info.retry_after, 30.0)
    return BACKOFF_BASE_SEC * (2 ** (intento - 1))


def cliente_openai():
    from openai import OpenAI

    return OpenAI(
        api_key=nebula_config.openai_api_key(),
        timeout=OPENAI_TIMEOUT_SEC,
        max_retries=0,
    )


def completar_chat_con_reintentos(
    messages: list[dict],
    *,
    max_tokens: int,
    temperature: float = 0.7,
    on_reintento: Optional[Callable[[int, ErrorOpenAI], None]] = None,
) -> str:
    ultimo_error: Optional[ErrorOpenAI] = None
    client = cliente_openai()
    model = nebula_config.openai_model()

    for intento in range(1, MAX_REINTENTOS + 1):
        try:
            logger.info("OpenAI chat intento=%s model=%s msgs=%s", intento, model, len(messages))
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            texto = (resp.choices[0].message.content or "").strip()
            if not texto:
                raise ValueError("respuesta_vacia")
            return texto
        except Exception as exc:
            if str(exc) == "respuesta_vacia":
                info = ErrorOpenAI(
                    codigo="empty",
                    mensaje="La IA no generó texto. Intenta reformular tu pregunta.",
                    retryable=intento < MAX_REINTENTOS,
                    tecnico="empty_response",
                )
            else:
                info = clasificar_error_openai(exc)
            ultimo_error = info
            logger.warning(
                "OpenAI error intento=%s codigo=%s retryable=%s tecnico=%s",
                intento,
                info.codigo,
                info.retryable,
                info.tecnico[:200],
            )
            if not info.retryable or intento >= MAX_REINTENTOS:
                break
            if on_reintento:
                on_reintento(intento, info)
            time.sleep(_espera_reintento(intento, info))

    assert ultimo_error is not None
    raise TutorOpenAIClientError(ultimo_error)


def stream_chat_con_reintentos(
    messages: list[dict],
    *,
    max_tokens: int,
    temperature: float = 0.7,
    on_reintento: Optional[Callable[[int, ErrorOpenAI], None]] = None,
    on_status: Optional[Callable[[str, str], None]] = None,
) -> Generator[str, None, None]:
    """Stream con reintentos si falla antes del primer token."""
    ultimo_error: Optional[ErrorOpenAI] = None
    client = cliente_openai()
    model = nebula_config.openai_model()

    for intento in range(1, MAX_REINTENTOS + 1):
        try:
            if on_status and intento == 1:
                on_status("processing", "La IA está procesando tu solicitud…")
            elif on_status and intento > 1:
                on_status("retry", "Reintentando conexión…")

            logger.info("OpenAI stream intento=%s model=%s", intento, model)
            stream = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )
            hubo = False
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta:
                    hubo = True
                    yield delta
            if hubo:
                return
            raise ValueError("stream_vacio")
        except Exception as exc:
            if str(exc) in ("stream_vacio", "respuesta_vacia"):
                info = ErrorOpenAI(
                    codigo="empty",
                    mensaje="La IA no generó una respuesta. Intenta de nuevo.",
                    retryable=intento < MAX_REINTENTOS,
                    tecnico=str(exc),
                )
            else:
                info = clasificar_error_openai(exc)
            ultimo_error = info
            logger.warning(
                "OpenAI stream error intento=%s codigo=%s",
                intento,
                info.codigo,
            )
            if not info.retryable or intento >= MAX_REINTENTOS:
                break
            if on_reintento:
                on_reintento(intento, info)
            time.sleep(_espera_reintento(intento, info))

    assert ultimo_error is not None
    raise TutorOpenAIClientError(ultimo_error)


class TutorOpenAIClientError(Exception):
    def __init__(self, info: ErrorOpenAI):
        self.info = info
        super().__init__(info.mensaje)


def verificar_conectividad_openai() -> dict:
    """Diagnóstico ligero (sin gastar tokens de chat)."""
    estado = nebula_config.estado_openai()
    resultado = {
        **estado,
        "ok": estado.get("configurada", False),
        "timeout_sec": OPENAI_TIMEOUT_SEC,
        "max_reintentos": MAX_REINTENTOS,
    }
    if not estado.get("configurada"):
        resultado["mensaje"] = "OPENAI_API_KEY no configurada o inválida en .env"
        return resultado
    try:
        client = cliente_openai()
        client.models.list(limit=1)
        resultado["conexion"] = "ok"
        resultado["mensaje"] = "API accesible"
    except Exception as exc:
        info = clasificar_error_openai(exc)
        resultado["conexion"] = "error"
        resultado["codigo_error"] = info.codigo
        resultado["mensaje"] = info.mensaje
        resultado["ok"] = info.codigo in ("rate_limit", "overloaded")
    return resultado
