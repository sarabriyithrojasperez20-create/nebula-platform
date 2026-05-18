"""Carga de variables de entorno (desarrollo y producción)."""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger("nebula.config")

ROOT_DIR = Path(__file__).resolve().parent
ENV_PATH = ROOT_DIR / ".env"
ENV_EXAMPLE_PATH = ROOT_DIR / ".env.example"

_ENV_PLACEHOLDER_MARKERS = (
    "pegar_aqui",
    "tu-clave",
    "your_api_key",
    "changeme",
    "xxxxxxxx",
)


def _asegurar_archivo_env() -> Path:
    """Crea `.env` desde `.env.example` si no existe."""
    if ENV_PATH.exists():
        return ENV_PATH
    if ENV_EXAMPLE_PATH.exists():
        shutil.copy(ENV_EXAMPLE_PATH, ENV_PATH)
        logger.info("Archivo .env creado desde .env.example — completa OPENAI_API_KEY.")
    else:
        ENV_PATH.write_text(
            "OPENAI_API_KEY=pegar_aqui_la_api_key_real\n"
            "OPENAI_MODEL=gpt-4o-mini\n",
            encoding="utf-8",
        )
        logger.info("Archivo .env creado — completa OPENAI_API_KEY.")
    return ENV_PATH


def _cargar_dotenv() -> None:
    _asegurar_archivo_env()
    try:
        from dotenv import load_dotenv

        # override=False: variables del sistema (producción) tienen prioridad
        load_dotenv(ENV_PATH, override=False)
        load_dotenv(override=False)
    except ImportError:
        logger.warning(
            "python-dotenv no instalado. Usa: pip install python-dotenv "
            "o define OPENAI_API_KEY en el entorno del sistema."
        )


_cargar_dotenv()


def _normalizar_valor(valor: str | None) -> str:
    if not valor:
        return ""
    texto = valor.strip()
    if len(texto) >= 2 and texto[0] == texto[-1] and texto[0] in "\"'":
        texto = texto[1:-1].strip()
    return texto.replace(" ", "")


def openai_api_key() -> str:
    raw = os.getenv("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    return _normalizar_valor(raw)


def openai_model() -> str:
    return _normalizar_valor(os.getenv("OPENAI_MODEL") or os.environ.get("OPENAI_MODEL")) or "gpt-4o-mini"


def _es_placeholder(key: str) -> bool:
    lower = key.lower()
    return any(marker in lower for marker in _ENV_PLACEHOLDER_MARKERS)


def openai_configurado() -> bool:
    key = openai_api_key()
    if not key or _es_placeholder(key):
        return False
    return len(key) >= 20


def estado_openai() -> dict:
    """Diagnóstico sin exponer la clave."""
    key = openai_api_key()
    return {
        "configurada": openai_configurado(),
        "env_file": str(ENV_PATH),
        "env_exists": ENV_PATH.exists(),
        "longitud_key": len(key) if key else 0,
        "modelo": openai_model(),
    }


def log_estado_openai() -> None:
    estado = estado_openai()
    if estado["configurada"]:
        logger.info(
            "OpenAI API KEY: CONFIGURADA (modelo=%s, .env=%s)",
            estado["modelo"],
            estado["env_exists"],
        )
    else:
        logger.warning(
            "OpenAI API KEY: NO CONFIGURADA — edita %s y define OPENAI_API_KEY=sk-...",
            estado["env_file"],
        )
