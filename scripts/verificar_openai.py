#!/usr/bin/env python3
"""Verifica que OPENAI_API_KEY esté cargada (sin mostrar la clave)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import nebula_config  # noqa: E402
from nebula_config import estado_openai, openai_configurado  # noqa: E402

if __name__ == "__main__":
    estado = estado_openai()
    print("API KEY:", "CONFIGURADA" if openai_configurado() else "NO CONFIGURADA")
    print("Archivo .env:", estado["env_file"], "| existe:", estado["env_exists"])
    print("Modelo:", estado["modelo"])
    if not openai_configurado():
        print(
            "\nEdita .env y reemplaza pegar_aqui_la_api_key_real por tu clave sk-...\n"
            "Luego reinicia Flask."
        )
        sys.exit(1)
    sys.exit(0)
