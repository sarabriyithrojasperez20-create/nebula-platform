# -*- coding: utf-8 -*-
"""Suscripción Plan Pro — reexporta desde nebula_data (compatibilidad)."""

from __future__ import annotations

from nebula_data import activar_plan_pro_usuario as activar_plan_pro
from nebula_data import plan_de_usuario_dict as plan_de_usuario

PLANES_PRO = frozenset({"pro", "premium"})


def es_plan_pro(usuario) -> bool:
    return plan_de_usuario(usuario) in PLANES_PRO
