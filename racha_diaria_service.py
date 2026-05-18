"""
Servicio de racha diaria académica — Nébula AI
Persistencia en JSON (misma capa que el resto del proyecto).
Preparado para gamificación futura (niveles, recompensas, badges).
"""

from __future__ import annotations

import importlib.util
import json
import logging
import os
import sys
from datetime import date, datetime, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

logger = logging.getLogger(__name__)

# Zona IANA del estudiante (futuro: leer desde perfil de usuario)
TZ_NAME_DEFAULT = "America/Mexico_City"

# Carga diferida: evita fallar al importar app si falta tzdata en Windows
_tz_cache: ZoneInfo | None = None


def _paquete_tzdata_instalado() -> bool:
    """
    zoneinfo en Windows usa importlib.resources.files('tzdata') internamente.
    Sin el paquete PyPI `tzdata`, aparece ModuleNotFoundError bajo resources.files().
    """
    return importlib.util.find_spec("tzdata") is not None


def obtener_zona_horaria(nombre: str | None = None) -> ZoneInfo:
    """Resuelve ZoneInfo con mensajes claros si falta tzdata o la clave IANA."""
    global _tz_cache
    nombre = nombre or TZ_NAME_DEFAULT

    if _tz_cache is not None and str(_tz_cache) == nombre:
        return _tz_cache

    try:
        tz = ZoneInfo(nombre)
        _tz_cache = tz
        return tz
    except ZoneInfoNotFoundError as exc:
        if sys.platform == "win32" and not _paquete_tzdata_instalado():
            mensaje = (
                f"No se pudo cargar la zona horaria '{nombre}'. "
                "En Windows con Python 3.9+ ejecuta: pip install tzdata "
                "(stdlib zoneinfo → importlib.resources → paquete 'tzdata')."
            )
        else:
            mensaje = f"Zona horaria IANA no disponible: '{nombre}'."
        logger.error(mensaje)
        raise RuntimeError(mensaje) from exc


def get_tz_default() -> ZoneInfo:
    """Zona horaria por defecto del servicio de racha."""
    return obtener_zona_horaria(TZ_NAME_DEFAULT)

DATA_DIR = "data"
ARCHIVO_RACHA = "racha_diaria.json"
ARCHIVO_LOGS = "racha_logs.json"

# Actividades que mantienen o inician la racha (hooks automáticos en app.py)
TIPOS_ACTIVIDAD_VALIDOS = frozenset(
    {
        "tarea",
        "quiz",
        "leccion",
        "meta",
        "estudio_tiempo",
        "evaluacion",  # diagnóstico / evaluación de curso
        "curso",  # ingreso o interacción con un curso
        "plan_estudios",  # módulo plan de estudios
    }
)

VENTANA_SIN_ACTIVIDAD_HORAS = 24
MINUTOS_ESTUDIO_MINIMOS = 15
META_HORAS_SEMANALES = 20
MAX_LOGS_POR_USUARIO = 500

# Niveles según días consecutivos (racha_actual)
NIVELES_RACHA = (
    (31, "Maestro del hábito"),
    (16, "Maestro del hábito"),
    (8, "Dedicado"),
    (4, "Constante"),
    (0, "Explorador"),
)


def _ahora(tz: ZoneInfo | None = None) -> datetime:
    return datetime.now(tz or get_tz_default())


def _fecha_local_str(dt: datetime | None = None, tz: ZoneInfo | None = None) -> str:
    return (dt or _ahora(tz)).strftime("%Y-%m-%d")


def _parse_fecha(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _coleccion_racha(nombre_archivo: str) -> str:
    if nombre_archivo == "racha_diaria.json":
        return "racha_diaria"
    if nombre_archivo == "racha_logs.json":
        return "racha_logs"
    raise ValueError(f"Archivo de racha desconocido: {nombre_archivo}")


def _cargar_json(nombre: str) -> list:
    from nebula_data import cargar_datos

    return cargar_datos(_coleccion_racha(nombre))


def _guardar_json(nombre: str, datos: list) -> None:
    from nebula_data import guardar_datos

    guardar_datos(_coleccion_racha(nombre), datos)


def _generar_id(lista: list, campo: str) -> int:
    if not lista:
        return 1
    return max(item.get(campo, 0) for item in lista) + 1


def _obtener_perfil(registros: list, id_usuario: int) -> dict:
    for reg in registros:
        if reg.get("id_usuario") == id_usuario:
            return reg
    return None


def _crear_perfil(registros: list, id_usuario: int) -> dict:
    perfil = {
        "id_racha": _generar_id(registros, "id_racha"),
        "id_usuario": id_usuario,
        "racha_actual": 0,
        "mejor_racha": 0,
        "ultima_fecha_actividad": None,
        "ultima_actividad_at": None,
        "dias_activos": [],
        "estudio_minutos_por_dia": {},
        "actividades_por_dia": {},
        "puntos_gamificacion": 0,
        "version": 1,
    }
    registros.append(perfil)
    return perfil


def calcular_racha_desde_dias(dias_activos: list[str], hoy: str | None = None) -> int:
    """Cuenta días consecutivos hacia atrás desde hoy (o desde el último día activo)."""
    if not dias_activos:
        return 0
    hoy = hoy or _fecha_local_str()
    conjunto = set(dias_activos)
    # La racha visible termina en el último día con actividad (hoy o ayer como máximo)
    inicio = _parse_fecha(hoy)
    if hoy not in conjunto:
        ayer = (inicio - timedelta(days=1)).strftime("%Y-%m-%d")
        if ayer not in conjunto:
            return 0
        inicio = _parse_fecha(ayer)
    streak = 0
    d = inicio
    while d.strftime("%Y-%m-%d") in conjunto:
        streak += 1
        d -= timedelta(days=1)
    return streak


def _aplicar_regla_24_horas(perfil: dict, ahora: datetime | None = None) -> bool:
    """
    Si pasaron más de 24 h desde la última actividad y hoy no hay registro,
    la racha actual se reinicia a 0 (el historial de días se conserva para el heatmap).
    Retorna True si se reinició.
    """
    ahora = ahora or _ahora()
    ultima_at = perfil.get("ultima_actividad_at")
    hoy = _fecha_local_str(ahora)
    dias = perfil.get("dias_activos") or []

    if hoy in dias:
        return False

    if not ultima_at:
        if perfil.get("racha_actual", 0) != 0:
            perfil["racha_actual"] = 0
            return True
        return False

    try:
        ultima_dt = datetime.fromisoformat(ultima_at)
        if ultima_dt.tzinfo is None:
            ultima_dt = ultima_dt.replace(tzinfo=get_tz_default())
    except (TypeError, ValueError):
        return False

    delta = ahora - ultima_dt
    if delta.total_seconds() > VENTANA_SIN_ACTIVIDAD_HORAS * 3600:
        if perfil.get("racha_actual", 0) != 0:
            perfil["racha_actual"] = 0
            return True
    return False


def _recalcular_metricas(perfil: dict, ahora: datetime | None = None) -> dict:
    ahora = ahora or _ahora()
    hoy = _fecha_local_str(ahora)
    dias = sorted(set(perfil.get("dias_activos") or []))

    _aplicar_regla_24_horas(perfil, ahora)

    racha = calcular_racha_desde_dias(dias, hoy)
    perfil["dias_activos"] = dias
    perfil["racha_actual"] = racha
    perfil["mejor_racha"] = max(perfil.get("mejor_racha", 0), racha)

    return perfil


def _agregar_log(
    id_usuario: int,
    tipo: str,
    metadata: Optional[dict],
    fecha_dia: str,
    ahora: datetime,
) -> None:
    logs = _cargar_json(ARCHIVO_LOGS)
    entrada = {
        "id_log": _generar_id(logs, "id_log"),
        "id_usuario": id_usuario,
        "tipo": tipo,
        "fecha": ahora.isoformat(),
        "fecha_dia": fecha_dia,
        "metadata": metadata or {},
    }
    logs.append(entrada)
    # Conservar solo los últimos N del usuario + recientes globales
    por_usuario = [l for l in logs if l.get("id_usuario") == id_usuario]
    otros = [l for l in logs if l.get("id_usuario") != id_usuario]
    por_usuario = por_usuario[-MAX_LOGS_POR_USUARIO:]
    _guardar_json(ARCHIVO_LOGS, otros + por_usuario)


def _incrementar_racha_dia(perfil: dict, fecha_dia: str, ahora: datetime) -> tuple[int, bool]:
    """
    Incrementa la racha si es un nuevo día válido.
    Retorna (racha_actual, dia_nuevo_en_racha).
    """
    dias = set(perfil.get("dias_activos") or [])
    if fecha_dia in dias:
        return perfil.get("racha_actual", 0), False

    ultima_fecha = perfil.get("ultima_fecha_actividad")
    racha = perfil.get("racha_actual", 0)

    if not ultima_fecha:
        racha = 1
    else:
        ayer = (_parse_fecha(fecha_dia) - timedelta(days=1)).strftime("%Y-%m-%d")
        ultima_at = perfil.get("ultima_actividad_at")
        ventana_ok = True
        if ultima_at:
            try:
                udt = datetime.fromisoformat(ultima_at)
                if udt.tzinfo is None:
                    udt = udt.replace(tzinfo=get_tz_default())
                ventana_ok = (ahora - udt).total_seconds() <= VENTANA_SIN_ACTIVIDAD_HORAS * 3600
            except (TypeError, ValueError):
                ventana_ok = False

        if ultima_fecha == ayer and ventana_ok:
            racha += 1
        elif ultima_fecha == fecha_dia:
            pass
        else:
            # Día perdido o ventana de 24 h vencida → nueva racha desde 1
            racha = 1

    dias.add(fecha_dia)
    perfil["dias_activos"] = sorted(dias)
    perfil["ultima_fecha_actividad"] = fecha_dia
    perfil["ultima_actividad_at"] = ahora.isoformat()
    perfil["racha_actual"] = racha
    perfil["mejor_racha"] = max(perfil.get("mejor_racha", 0), racha)

    return racha, True


def _registrar_tipo_en_dia(perfil: dict, fecha_dia: str, tipo: str) -> None:
    por_dia = perfil.setdefault("actividades_por_dia", {})
    lista = por_dia.setdefault(fecha_dia, [])
    if tipo not in lista:
        lista.append(tipo)


def obtener_nivel(racha_actual: int) -> str:
    """0-3 Explorador · 4-7 Constante · 8-15 Dedicado · 16+ Maestro del hábito."""
    if racha_actual >= 16:
        return "Maestro del hábito"
    if racha_actual >= 8:
        return "Dedicado"
    if racha_actual >= 4:
        return "Constante"
    return "Explorador"


def registrar_actividad_automatica(
    id_usuario: int,
    tipo: str,
    metadata: Optional[dict] = None,
    minutos_estudio: int = 0,
) -> dict:
    """
    Punto único para hooks de la plataforma (quiz, lección, plan de estudios, etc.).
    Idempotente el mismo día: no duplica la racha.
    """
    if tipo not in TIPOS_ACTIVIDAD_VALIDOS:
        logger.warning("Tipo de racha automática no válido: %s", tipo)
        estado = obtener_estado_racha(id_usuario, sincronizar_sistema=False)
        estado["ok"] = False
        return estado
    try:
        return registrar_actividad_racha(
            id_usuario, tipo, metadata, minutos_estudio=minutos_estudio
        )
    except Exception as exc:
        logger.exception("Error registrando racha automática (%s)", tipo)
        estado = obtener_estado_racha(id_usuario, sincronizar_sistema=False)
        estado["ok"] = False
        estado["mensaje"] = str(exc)
        return estado


def preparar_racha_plan_estudios(id_usuario: int) -> dict:
    """
    Al entrar al Plan de estudios: sincroniza fuentes del sistema y registra visita.
    Usado por la ruta /plan_estudios — sin botón manual.
    """
    estado = sincronizar_desde_fuentes_sistema(id_usuario)
    visita = registrar_actividad_automatica(
        id_usuario, "plan_estudios", {"origen": "carga_modulo"}
    )
    if visita.get("ok"):
        return visita
    return estado


def dias_activos_mes(dias_activos: list[str], mes: int | None = None, anio: int | None = None) -> int:
    ahora = _ahora()
    mes = mes if mes is not None else ahora.month
    anio = anio if anio is not None else ahora.year
    return sum(
        1
        for d in dias_activos
        if _parse_fecha(d).month == mes and _parse_fecha(d).year == anio
    )


def minutos_estudio_semana(perfil: dict, ahora: datetime | None = None) -> float:
    ahora = ahora or _ahora()
    inicio_semana = ahora.date() - timedelta(days=ahora.weekday())
    total = 0
    por_dia = perfil.get("estudio_minutos_por_dia") or {}
    for i in range(7):
        d = (inicio_semana + timedelta(days=i)).strftime("%Y-%m-%d")
        total += int(por_dia.get(d, 0))
    return round(total / 60, 1)


def registrar_actividad_racha(
    id_usuario: int,
    tipo: str,
    metadata: Optional[dict] = None,
    minutos_estudio: int = 0,
) -> dict:
    """
    Registra una actividad académica válida.
    Múltiples actividades el mismo día no duplican la racha.
    """
    if tipo not in TIPOS_ACTIVIDAD_VALIDOS:
        return {"ok": False, "mensaje": f"Tipo de actividad no válido: {tipo}"}

    if tipo == "estudio_tiempo" and minutos_estudio < MINUTOS_ESTUDIO_MINIMOS:
        return {
            "ok": False,
            "mensaje": f"Mínimo {MINUTOS_ESTUDIO_MINIMOS} minutos de estudio para contar",
        }

    ahora = _ahora()
    fecha_dia = _fecha_local_str(ahora)
    registros = _cargar_json(ARCHIVO_RACHA)
    perfil = _obtener_perfil(registros, id_usuario) or _crear_perfil(registros, id_usuario)

    _aplicar_regla_24_horas(perfil, ahora)

    if tipo == "estudio_tiempo" and minutos_estudio:
        por_dia = perfil.setdefault("estudio_minutos_por_dia", {})
        por_dia[fecha_dia] = int(por_dia.get(fecha_dia, 0)) + minutos_estudio

    _registrar_tipo_en_dia(perfil, fecha_dia, tipo)
    racha, dia_nuevo = _incrementar_racha_dia(perfil, fecha_dia, ahora)

    if tipo == "estudio_tiempo":
        perfil["puntos_gamificacion"] = perfil.get("puntos_gamificacion", 0) + minutos_estudio
    else:
        perfil["puntos_gamificacion"] = perfil.get("puntos_gamificacion", 0) + 10

    _recalcular_metricas(perfil, ahora)
    _agregar_log(id_usuario, tipo, metadata, fecha_dia, ahora)
    _guardar_json(ARCHIVO_RACHA, registros)

    estado = construir_estado_respuesta(perfil, ahora)
    estado["ok"] = True
    estado["dia_nuevo"] = dia_nuevo
    estado["racha_incrementada"] = dia_nuevo
    return estado


def actividad_registrada_hoy(perfil: dict, fecha_dia: str | None = None) -> bool:
    fecha_dia = fecha_dia or _fecha_local_str()
    return fecha_dia in (perfil.get("dias_activos") or [])


def construir_estado_respuesta(perfil: dict, ahora: datetime | None = None) -> dict:
    ahora = ahora or _ahora()
    hoy = _fecha_local_str(ahora)
    dias = perfil.get("dias_activos") or []
    racha = perfil.get("racha_actual", 0)
    record = perfil.get("mejor_racha", 0)
    nivel = obtener_nivel(racha)
    activos_mes = dias_activos_mes(dias)
    horas_semana = minutos_estudio_semana(perfil, ahora)
    actividades_hoy = (perfil.get("actividades_por_dia") or {}).get(hoy, [])

    return {
        "id_usuario": perfil.get("id_usuario"),
        "racha_actual": racha,
        "mejor_racha": record,
        "record": record,
        "record_personal": record,
        "current_streak": racha,
        "best_streak": record,
        "dias_activos": dias,
        "dias_activos_mes": activos_mes,
        "active_days_month": activos_mes,
        "nivel": nivel,
        "ultima_fecha_actividad": perfil.get("ultima_fecha_actividad"),
        "last_activity_date": perfil.get("ultima_fecha_actividad"),
        "ultima_actividad_at": perfil.get("ultima_actividad_at"),
        "actividad_hoy": actividad_registrada_hoy(perfil, hoy),
        "actividades_hoy": actividades_hoy,
        "fecha_hoy": hoy,
        "horas_semanales": {
            "completadas": horas_semana,
            "meta": META_HORAS_SEMANALES,
        },
        "puntos_gamificacion": perfil.get("puntos_gamificacion", 0),
        "timezone": str(get_tz_default()),
        "modo": "automatico",
    }


def obtener_estado_racha(id_usuario: int, sincronizar_sistema: bool = True) -> dict:
    if sincronizar_sistema:
        sincronizar_desde_fuentes_sistema(id_usuario)

    registros = _cargar_json(ARCHIVO_RACHA)
    perfil = _obtener_perfil(registros, id_usuario)
    if not perfil:
        perfil = _crear_perfil(registros, id_usuario)
        _guardar_json(ARCHIVO_RACHA, registros)

    _recalcular_metricas(perfil, _ahora())
    _guardar_json(ARCHIVO_RACHA, registros)

    estado = construir_estado_respuesta(perfil)
    estado["ok"] = True
    return estado


def sincronizar_desde_fuentes_sistema(id_usuario: int) -> dict:
    """
    Detecta actividades del día en quizzes, lecciones y actividad_sistema
    y las registra sin duplicar la racha.
    """
    hoy = _fecha_local_str()
    registradas = []

    def _fecha_coincide(fecha_str: str) -> bool:
        if not fecha_str:
            return False
        return fecha_str[:10] == hoy

    resultados = _cargar_json("resultados_quiz.json")
    for r in resultados:
        if r.get("id_usuario") != id_usuario:
            continue
        if not r.get("aprobado"):
            continue
        if _fecha_coincide(r.get("fecha", "")):
            res = registrar_actividad_racha(
                id_usuario,
                "quiz",
                {"slug": r.get("slug"), "leccion_id": r.get("leccion_id")},
            )
            if res.get("ok"):
                registradas.append("quiz")

    actividades = _cargar_json("actividad_sistema.json")
    mapa_tipo = {
        "leccion_completada": "leccion",
        "quiz_aprobado": "quiz",
    }
    for a in actividades:
        if a.get("id_usuario") != id_usuario:
            continue
        if not _fecha_coincide(a.get("fecha", "")):
            continue
        tipo = mapa_tipo.get(a.get("tipo"))
        if tipo:
            res = registrar_actividad_racha(id_usuario, tipo, {"origen": "actividad_sistema"})
            if res.get("ok"):
                registradas.append(tipo)

    progreso = _cargar_json("progreso_catalogo.json")
    for p in progreso:
        if p.get("id_usuario") != id_usuario:
            continue
        if _fecha_coincide(p.get("fecha_actualizacion", "")):
            res = registrar_actividad_racha(
                id_usuario,
                "leccion",
                {"slug": p.get("slug"), "origen": "progreso_catalogo"},
            )
            if res.get("ok"):
                registradas.append("leccion")

    # Evaluaciones / diagnósticos completados hoy
    diagnosticos = _cargar_json("diagnosticos_catalogo.json")
    for d in diagnosticos:
        if d.get("id_usuario") != id_usuario:
            continue
        if _fecha_coincide(d.get("fecha", "")):
            res = registrar_actividad_racha(
                id_usuario,
                "evaluacion",
                {"slug": d.get("slug"), "origen": "diagnosticos_catalogo"},
            )
            if res.get("ok"):
                registradas.append("evaluacion")

    # Progreso legacy (cursos antiguos)
    progreso_legacy = _cargar_json("progreso.json")
    for p in progreso_legacy:
        if p.get("id_usuario") != id_usuario:
            continue
        if p.get("estado") == "completado" and _fecha_coincide(
            p.get("fecha_actualizacion", "")
        ):
            res = registrar_actividad_racha(
                id_usuario,
                "leccion",
                {
                    "id_curso": p.get("id_curso"),
                    "id_leccion": p.get("id_leccion"),
                    "origen": "progreso_legacy",
                },
            )
            if res.get("ok"):
                registradas.append("leccion")

    # Actividades de tipo evaluación en el calendario/plan
    for a in actividades:
        if a.get("id_usuario") != id_usuario:
            continue
        if a.get("tipo") == "evaluacion" and _fecha_coincide(a.get("fecha", "")):
            res = registrar_actividad_racha(
                id_usuario,
                "evaluacion",
                {"origen": "actividades", "titulo": a.get("titulo")},
            )
            if res.get("ok"):
                registradas.append("evaluacion")

    estado = obtener_estado_racha(id_usuario, sincronizar_sistema=False)
    estado["tipos_sincronizados"] = list(set(registradas))
    estado["ok"] = True
    return estado


def sincronizar_y_validar_hoy(id_usuario: int) -> dict:
    """Compatibilidad API: sincroniza y devuelve estado (racha automática, sin botón manual)."""
    estado = sincronizar_desde_fuentes_sistema(id_usuario)
    estado["codigo"] = "sincronizado"
    estado["mensaje"] = (
        "Racha actualizada automáticamente según tu actividad en la plataforma."
    )
    return estado


def obtener_resumen_racha(id_usuario: int) -> dict:
    estado = obtener_estado_racha(id_usuario)
    return {
        "ok": True,
        "racha_actual": estado.get("racha_actual", 0),
        "mejor_racha": estado.get("mejor_racha", 0),
        "nivel": estado.get("nivel"),
        "actividad_hoy": estado.get("actividad_hoy"),
        "dias_activos_mes": estado.get("dias_activos_mes"),
    }
