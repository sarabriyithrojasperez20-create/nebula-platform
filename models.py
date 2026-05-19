# -*- coding: utf-8 -*-
"""Modelos SQLAlchemy — Nébula (PostgreSQL)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from extensions import db


def _resolve_json_type():
    """JSONB en PostgreSQL; JSON estándar en SQLite (desarrollo local)."""
    from db import is_sqlite_url, resolve_database_url

    url = resolve_database_url()
    return JSON if is_sqlite_url(url) else JSONB


JsonType = _resolve_json_type()


class Role(db.Model):
    __tablename__ = "roles"

    id_rol: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre_rol: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    descripcion: Mapped[str | None] = mapped_column(Text)

    usuarios: Mapped[list["User"]] = relationship(back_populates="rol")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id_rol": self.id_rol,
            "nombre_rol": self.nombre_rol,
            "descripcion": self.descripcion or "",
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Role:
        return cls(
            id_rol=int(data["id_rol"]),
            nombre_rol=data.get("nombre_rol", ""),
            descripcion=data.get("descripcion"),
        )


class User(db.Model):
    __tablename__ = "usuarios"

    id_usuario: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre_completo: Mapped[str] = mapped_column(String(255), nullable=False)
    correo: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    password: Mapped[str] = mapped_column(String(512), nullable=False)
    id_rol: Mapped[int] = mapped_column(ForeignKey("roles.id_rol"), nullable=False, index=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    foto_perfil: Mapped[str | None] = mapped_column(String(512))
    foto_actualizada_en: Mapped[str | None] = mapped_column(String(32))
    fecha_registro: Mapped[str | None] = mapped_column(String(16))
    sobre_mi: Mapped[str | None] = mapped_column(Text)
    nivel_academico: Mapped[str | None] = mapped_column(String(64))
    grado: Mapped[str | None] = mapped_column(String(64))
    preferencias_aprendizaje: Mapped[dict | None] = mapped_column(JsonType)
    progreso_materias: Mapped[dict | None] = mapped_column(JsonType)

    rol: Mapped[Role] = relationship(back_populates="usuarios")

    def plan_suscripcion(self) -> str:
        prefs = self.preferencias_aprendizaje or {}
        plan = prefs.get("plan") or "free"
        return str(plan).strip().lower() or "free"

    def to_dict(self, *, include_password: bool = False) -> dict[str, Any]:
        out: dict[str, Any] = {
            "id_usuario": self.id_usuario,
            "nombre_completo": self.nombre_completo,
            "correo": self.correo,
            "username": self.username,
            "id_rol": self.id_rol,
            "activo": self.activo,
            "plan": self.plan_suscripcion(),
        }
        if include_password:
            out["password"] = self.password
        if self.foto_perfil:
            out["foto_perfil"] = self.foto_perfil
        if self.foto_actualizada_en:
            out["foto_actualizada_en"] = self.foto_actualizada_en
        if self.fecha_registro:
            out["fecha_registro"] = self.fecha_registro
        if self.sobre_mi is not None:
            out["sobre_mi"] = self.sobre_mi
        if self.nivel_academico:
            out["nivel_academico"] = self.nivel_academico
        if self.grado:
            out["grado"] = self.grado
        if self.preferencias_aprendizaje:
            out["preferencias_aprendizaje"] = self.preferencias_aprendizaje
        if self.progreso_materias is not None:
            out["progreso_materias"] = self.progreso_materias
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> User:
        from password_security import normalize_password_for_storage

        prefs = dict(data.get("preferencias_aprendizaje") or {})
        plan_raw = data.get("plan")
        if plan_raw:
            prefs["plan"] = str(plan_raw).strip().lower()

        raw_pwd = data.get("password")
        if raw_pwd is None or str(raw_pwd).strip() == "":
            raise ValueError("password es obligatorio al crear un usuario.")
        stored_pwd = normalize_password_for_storage(str(raw_pwd))

        return cls(
            id_usuario=int(data["id_usuario"]),
            nombre_completo=data.get("nombre_completo", ""),
            correo=data.get("correo", ""),
            username=data.get("username", ""),
            password=stored_pwd,
            id_rol=int(data.get("id_rol", 2)),
            activo=bool(data.get("activo", True)),
            foto_perfil=data.get("foto_perfil") or None,
            foto_actualizada_en=data.get("foto_actualizada_en") or None,
            fecha_registro=data.get("fecha_registro") or None,
            sobre_mi=data.get("sobre_mi"),
            nivel_academico=data.get("nivel_academico") or None,
            grado=data.get("grado") or None,
            preferencias_aprendizaje=prefs or None,
            progreso_materias=data.get("progreso_materias"),
        )


class LegacyCourse(db.Model):
    """Cursos legacy (cursos.json) — compatibilidad."""

    __tablename__ = "cursos_legacy"

    id_curso: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload: Mapped[dict] = mapped_column(JsonType, nullable=False)

    def to_dict(self) -> dict[str, Any]:
        out = dict(self.payload)
        out.setdefault("id_curso", self.id_curso)
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LegacyCourse:
        pk = int(data.get("id_curso", 0))
        payload = {k: v for k, v in data.items() if k != "id_curso"}
        return cls(id_curso=pk, payload=payload)


class LegacyLesson(db.Model):
    __tablename__ = "lecciones_legacy"

    id_leccion: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload: Mapped[dict] = mapped_column(JsonType, nullable=False)

    def to_dict(self) -> dict[str, Any]:
        out = dict(self.payload)
        out.setdefault("id_leccion", self.id_leccion)
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LegacyLesson:
        pk = int(data.get("id_leccion", 0))
        payload = {k: v for k, v in data.items() if k != "id_leccion"}
        return cls(id_leccion=pk, payload=payload)


class LegacyProgress(db.Model):
    __tablename__ = "progreso_legacy"

    id_progreso: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload: Mapped[dict] = mapped_column(JsonType, nullable=False)

    def to_dict(self) -> dict[str, Any]:
        out = dict(self.payload)
        out.setdefault("id_progreso", self.id_progreso)
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LegacyProgress:
        pk = int(data.get("id_progreso", 0))
        payload = {k: v for k, v in data.items() if k != "id_progreso"}
        return cls(id_progreso=pk, payload=payload)


class CourseAssignment(db.Model):
    __tablename__ = "cursos_asignados"

    id_asignacion: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id_usuario", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    fecha_asignacion: Mapped[str | None] = mapped_column(String(16))

    __table_args__ = (
        Index("ix_cursos_asignados_usuario_slug", "id_usuario", "slug"),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id_asignacion": self.id_asignacion,
            "id_usuario": self.id_usuario,
            "slug": self.slug,
            "fecha_asignacion": self.fecha_asignacion or "",
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CourseAssignment:
        return cls(
            id_asignacion=int(data["id_asignacion"]),
            id_usuario=int(data["id_usuario"]),
            slug=data.get("slug", ""),
            fecha_asignacion=data.get("fecha_asignacion"),
        )


class CatalogProgress(db.Model):
    __tablename__ = "progreso_catalogo"

    id_progreso_catalogo: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id_usuario", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    lecciones_completadas: Mapped[list] = mapped_column(JsonType, default=list)
    fecha_actualizacion: Mapped[str | None] = mapped_column(String(16))

    __table_args__ = (
        UniqueConstraint("id_usuario", "slug", name="uq_progreso_catalogo_usuario_slug"),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id_progreso_catalogo": self.id_progreso_catalogo,
            "id_usuario": self.id_usuario,
            "slug": self.slug,
            "lecciones_completadas": self.lecciones_completadas or [],
            "fecha_actualizacion": self.fecha_actualizacion or "",
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CatalogProgress:
        return cls(
            id_progreso_catalogo=int(data["id_progreso_catalogo"]),
            id_usuario=int(data["id_usuario"]),
            slug=data.get("slug", ""),
            lecciones_completadas=data.get("lecciones_completadas") or [],
            fecha_actualizacion=data.get("fecha_actualizacion"),
        )


class DiagnosticRecord(db.Model):
    __tablename__ = "diagnosticos_catalogo"

    id_diagnostico: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id_usuario", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    nivel: Mapped[str | None] = mapped_column(String(32))
    titulo_nivel: Mapped[str | None] = mapped_column(String(128))
    porcentaje: Mapped[int | None] = mapped_column(Integer)
    correctas: Mapped[int | None] = mapped_column(Integer)
    total: Mapped[int | None] = mapped_column(Integer)
    errores_por_leccion: Mapped[dict | None] = mapped_column(JsonType)
    detalle: Mapped[list | None] = mapped_column(JsonType)
    fecha: Mapped[str | None] = mapped_column(String(32))

    __table_args__ = (
        Index("ix_diagnosticos_usuario_slug", "id_usuario", "slug"),
    )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "id_usuario": self.id_usuario,
            "slug": self.slug,
        }
        if self.id_diagnostico is not None:
            out["id_diagnostico"] = self.id_diagnostico
        for key in (
            "nivel",
            "titulo_nivel",
            "porcentaje",
            "correctas",
            "total",
            "errores_por_leccion",
            "detalle",
            "fecha",
        ):
            val = getattr(self, key)
            if val is not None:
                out[key] = val
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DiagnosticRecord:
        pk = data.get("id_diagnostico")
        if pk is None:
            raise ValueError("id_diagnostico requerido para diagnosticos_catalogo")
        return cls(
            id_diagnostico=int(pk),
            id_usuario=int(data["id_usuario"]),
            slug=data.get("slug", ""),
            nivel=data.get("nivel"),
            titulo_nivel=data.get("titulo_nivel"),
            porcentaje=data.get("porcentaje"),
            correctas=data.get("correctas"),
            total=data.get("total"),
            errores_por_leccion=data.get("errores_por_leccion"),
            detalle=data.get("detalle"),
            fecha=data.get("fecha"),
        )


class QuizResult(db.Model):
    __tablename__ = "resultados_quiz"

    id_resultado: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id_usuario", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    leccion_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    titulo_curso: Mapped[str | None] = mapped_column(String(255))
    titulo_leccion: Mapped[str | None] = mapped_column(String(255))
    porcentaje: Mapped[int] = mapped_column(Integer, default=0)
    correctas: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    aprobado: Mapped[bool] = mapped_column(Boolean, default=False)
    intento: Mapped[int] = mapped_column(Integer, default=1)
    fecha: Mapped[str | None] = mapped_column(String(32))

    __table_args__ = (
        Index("ix_quiz_usuario_slug_leccion", "id_usuario", "slug", "leccion_id"),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id_resultado": self.id_resultado,
            "id_usuario": self.id_usuario,
            "slug": self.slug,
            "leccion_id": self.leccion_id,
            "titulo_curso": self.titulo_curso or "",
            "titulo_leccion": self.titulo_leccion or "",
            "porcentaje": self.porcentaje,
            "correctas": self.correctas,
            "total": self.total,
            "aprobado": self.aprobado,
            "intento": self.intento,
            "fecha": self.fecha or "",
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QuizResult:
        return cls(
            id_resultado=int(data["id_resultado"]),
            id_usuario=int(data["id_usuario"]),
            slug=data.get("slug", ""),
            leccion_id=data.get("leccion_id", ""),
            titulo_curso=data.get("titulo_curso"),
            titulo_leccion=data.get("titulo_leccion"),
            porcentaje=int(data.get("porcentaje", 0)),
            correctas=int(data.get("correctas", 0)),
            total=int(data.get("total", 0)),
            aprobado=bool(data.get("aprobado", False)),
            intento=int(data.get("intento", 1)),
            fecha=data.get("fecha"),
        )


class Activity(db.Model):
    """Calendario / actividades del estudiante."""

    __tablename__ = "actividades"

    id_actividad: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload: Mapped[dict] = mapped_column(JsonType, nullable=False)

    def to_dict(self) -> dict[str, Any]:
        out = dict(self.payload)
        out.setdefault("id_actividad", self.id_actividad)
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Activity:
        pk = int(data.get("id_actividad", 0))
        return cls(id_actividad=pk, payload={k: v for k, v in data.items()})


class Comment(db.Model):
    __tablename__ = "comentarios"

    id_comentario: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload: Mapped[dict] = mapped_column(JsonType, nullable=False)

    def to_dict(self) -> dict[str, Any]:
        out = dict(self.payload)
        out.setdefault("id_comentario", self.id_comentario)
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Comment:
        pk = int(data.get("id_comentario", 0))
        return cls(id_comentario=pk, payload={k: v for k, v in data.items()})


class SystemActivity(db.Model):
    __tablename__ = "actividad_sistema"

    id_actividad: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    id_usuario: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), index=True
    )
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    fecha: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    slug: Mapped[str | None] = mapped_column(String(128))
    leccion_id: Mapped[str | None] = mapped_column(String(128))
    extra: Mapped[dict | None] = mapped_column(JsonType)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "id_actividad": self.id_actividad,
            "tipo": self.tipo,
            "titulo": self.titulo,
            "descripcion": self.descripcion,
            "fecha": self.fecha,
        }
        if self.id_usuario is not None:
            out["id_usuario"] = self.id_usuario
        if self.slug:
            out["slug"] = self.slug
        if self.leccion_id:
            out["leccion_id"] = self.leccion_id
        if self.extra:
            out.update(self.extra)
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SystemActivity:
        known = {
            "id_actividad",
            "tipo",
            "id_usuario",
            "titulo",
            "descripcion",
            "fecha",
            "slug",
            "leccion_id",
        }
        extra = {k: v for k, v in data.items() if k not in known}
        return cls(
            id_actividad=int(data["id_actividad"]),
            tipo=data.get("tipo", ""),
            id_usuario=data.get("id_usuario"),
            titulo=data.get("titulo", ""),
            descripcion=data.get("descripcion", ""),
            fecha=data.get("fecha", ""),
            slug=data.get("slug"),
            leccion_id=data.get("leccion_id"),
            extra=extra or None,
        )


class StreakRecord(db.Model):
    __tablename__ = "racha_diaria"

    id_racha: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id_usuario", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    racha_actual: Mapped[int] = mapped_column(Integer, default=0)
    mejor_racha: Mapped[int] = mapped_column(Integer, default=0)
    ultima_fecha_actividad: Mapped[str | None] = mapped_column(String(16))
    ultima_actividad_at: Mapped[str | None] = mapped_column(String(64))
    dias_activos: Mapped[list] = mapped_column(JsonType, default=list)
    estudio_minutos_por_dia: Mapped[dict] = mapped_column(JsonType, default=dict)
    actividades_por_dia: Mapped[dict] = mapped_column(JsonType, default=dict)
    puntos_gamificacion: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id_racha": self.id_racha,
            "id_usuario": self.id_usuario,
            "racha_actual": self.racha_actual,
            "mejor_racha": self.mejor_racha,
            "ultima_fecha_actividad": self.ultima_fecha_actividad,
            "ultima_actividad_at": self.ultima_actividad_at,
            "dias_activos": self.dias_activos or [],
            "estudio_minutos_por_dia": self.estudio_minutos_por_dia or {},
            "actividades_por_dia": self.actividades_por_dia or {},
            "puntos_gamificacion": self.puntos_gamificacion,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StreakRecord:
        return cls(
            id_racha=int(data["id_racha"]),
            id_usuario=int(data["id_usuario"]),
            racha_actual=int(data.get("racha_actual", 0)),
            mejor_racha=int(data.get("mejor_racha", 0)),
            ultima_fecha_actividad=data.get("ultima_fecha_actividad"),
            ultima_actividad_at=data.get("ultima_actividad_at"),
            dias_activos=data.get("dias_activos") or [],
            estudio_minutos_por_dia=data.get("estudio_minutos_por_dia") or {},
            actividades_por_dia=data.get("actividades_por_dia") or {},
            puntos_gamificacion=int(data.get("puntos_gamificacion", 0)),
            version=int(data.get("version", 1)),
        )


class StreakLog(db.Model):
    __tablename__ = "racha_logs"

    id_log: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id_usuario", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payload: Mapped[dict] = mapped_column(JsonType, nullable=False)

    __table_args__ = (Index("ix_racha_logs_usuario_id", "id_usuario", "id_log"),)

    def to_dict(self) -> dict[str, Any]:
        out = dict(self.payload)
        out.setdefault("id_log", self.id_log)
        out.setdefault("id_usuario", self.id_usuario)
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StreakLog:
        pk = int(data.get("id_log", 0))
        uid = int(data.get("id_usuario", 0))
        return cls(id_log=pk, id_usuario=uid, payload={k: v for k, v in data.items()})


class TutorSession(db.Model):
    __tablename__ = "tutor_sesiones"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id_usuario", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    contexto: Mapped[dict] = mapped_column(JsonType, default=dict)
    mensajes: Mapped[list] = mapped_column(JsonType, default=list)
    creada_at: Mapped[str | None] = mapped_column(String(64))
    actualizada_at: Mapped[str | None] = mapped_column(String(64))

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "id_usuario": self.id_usuario,
            "titulo": self.titulo,
            "contexto": self.contexto or {},
            "mensajes": self.mensajes or [],
            "creada_at": self.creada_at,
            "actualizada_at": self.actualizada_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TutorSession:
        return cls(
            session_id=data["session_id"],
            id_usuario=int(data["id_usuario"]),
            titulo=data.get("titulo", ""),
            contexto=data.get("contexto") or {},
            mensajes=data.get("mensajes") or [],
            creada_at=data.get("creada_at"),
            actualizada_at=data.get("actualizada_at"),
        )


class TutorDailyUsage(db.Model):
    __tablename__ = "tutor_uso_diario"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id_usuario", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fecha: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JsonType, nullable=False)

    __table_args__ = (
        UniqueConstraint("id_usuario", "fecha", name="uq_tutor_uso_usuario_fecha"),
    )

    def to_dict(self) -> dict[str, Any]:
        return dict(self.payload)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TutorDailyUsage:
        uid = int(data.get("id_usuario", 0))
        fecha = data.get("fecha", "")
        return cls(id_usuario=uid, fecha=fecha, payload={k: v for k, v in data.items()})


class TutorLog(db.Model):
    __tablename__ = "tutor_logs"

    id_log: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload: Mapped[dict] = mapped_column(JsonType, nullable=False)

    def to_dict(self) -> dict[str, Any]:
        out = dict(self.payload)
        out.setdefault("id_log", self.id_log)
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TutorLog:
        pk = int(data.get("id_log", 0))
        return cls(id_log=pk, payload={k: v for k, v in data.items()})


class AdminNotification(db.Model):
    __tablename__ = "notificaciones_admin"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[int | None] = mapped_column(Integer, index=True)
    user: Mapped[str | None] = mapped_column(String(255))
    avatar: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    meta: Mapped[dict | None] = mapped_column(JsonType)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "message": self.message,
            "user_id": self.user_id,
            "user": self.user,
            "avatar": self.avatar,
            "icon": self.icon,
            "created_at": self.created_at,
            "read": self.read,
            "meta": self.meta or {},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AdminNotification:
        return cls(
            id=int(data["id"]),
            type=data.get("type", ""),
            title=data.get("title", ""),
            message=data.get("message", ""),
            user_id=data.get("user_id"),
            user=data.get("user"),
            avatar=data.get("avatar"),
            icon=data.get("icon"),
            created_at=data.get("created_at", ""),
            read=bool(data.get("read", False)),
            meta=data.get("meta"),
        )


class ResourceDownload(db.Model):
    __tablename__ = "recursos_descargas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload: Mapped[dict] = mapped_column(JsonType, nullable=False)

    def to_dict(self) -> dict[str, Any]:
        out = dict(self.payload)
        if "id" not in out:
            out["id"] = self.id
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResourceDownload:
        pk = int(data.get("id", data.get("id_descarga", 0)))
        return cls(id=pk, payload={k: v for k, v in data.items()})


class SystemConfig(db.Model):
    __tablename__ = "config_sistema"

    clave: Mapped[str] = mapped_column(String(128), primary_key=True)
    valor: Mapped[str] = mapped_column(Text, nullable=False)
    actualizado_en: Mapped[str | None] = mapped_column(String(32))


class StatisticsSnapshot(db.Model):
    __tablename__ = "estadisticas_snapshot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    metrica: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    valor: Mapped[int] = mapped_column(Integer, nullable=False)
    capturado_en: Mapped[str | None] = mapped_column(String(32))

    __table_args__ = (
        Index("ix_estadisticas_metrica_id", "metrica", "id"),
    )


class CatalogCourse(db.Model):
    """Catálogo académico administrable (cursos visibles para estudiantes)."""

    __tablename__ = "catalogo_cursos"

    slug: Mapped[str] = mapped_column(String(128), primary_key=True)
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    nivel: Mapped[str] = mapped_column(String(64), default="Intermedio", nullable=False)
    categoria: Mapped[str] = mapped_column(String(64), default="matematicas", nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, default="")
    imagen: Mapped[str] = mapped_column(String(512), default="")
    duracion_total: Mapped[str] = mapped_column(String(64), default="")
    temas: Mapped[list | None] = mapped_column(JsonType)
    modulos: Mapped[list | None] = mapped_column(JsonType)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    orden: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    lecciones: Mapped[list["CatalogLesson"]] = relationship(
        back_populates="curso", cascade="all, delete-orphan"
    )
    evaluaciones: Mapped[list["CatalogEvaluation"]] = relationship(
        back_populates="curso", cascade="all, delete-orphan"
    )


class CatalogLesson(db.Model):
    __tablename__ = "catalogo_lecciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    curso_slug: Mapped[str] = mapped_column(
        ForeignKey("catalogo_cursos.slug", ondelete="CASCADE"), nullable=False, index=True
    )
    leccion_id: Mapped[str] = mapped_column(String(128), nullable=False)
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    duracion: Mapped[str] = mapped_column(String(64), default="30 min")
    orden: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    contenido: Mapped[dict | None] = mapped_column(JsonType)

    curso: Mapped[CatalogCourse] = relationship(back_populates="lecciones")

    __table_args__ = (
        UniqueConstraint("curso_slug", "leccion_id", name="uq_catalogo_leccion_curso"),
    )


class CatalogEvaluation(db.Model):
    __tablename__ = "catalogo_evaluaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    curso_slug: Mapped[str] = mapped_column(
        ForeignKey("catalogo_cursos.slug", ondelete="CASCADE"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    leccion_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    titulo: Mapped[str] = mapped_column(String(255), default="")
    porcentaje_aprobacion: Mapped[int] = mapped_column(Integer, default=70, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    nivel_lecciones: Mapped[dict | None] = mapped_column(JsonType)

    curso: Mapped[CatalogCourse] = relationship(back_populates="evaluaciones")
    preguntas: Mapped[list["CatalogQuestion"]] = relationship(
        back_populates="evaluacion", cascade="all, delete-orphan", order_by="CatalogQuestion.orden"
    )


class CatalogQuestion(db.Model):
    __tablename__ = "catalogo_preguntas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evaluacion_id: Mapped[int] = mapped_column(
        ForeignKey("catalogo_evaluaciones.id", ondelete="CASCADE"), nullable=False, index=True
    )
    orden: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    enunciado: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[str] = mapped_column(String(32), default="opcion_multiple")
    opciones: Mapped[dict | None] = mapped_column(JsonType)
    respuesta_correcta: Mapped[str] = mapped_column(String(8), nullable=False)
    explicacion: Mapped[str] = mapped_column(Text, default="")
    pista: Mapped[str] = mapped_column(Text, default="")
    tema: Mapped[str] = mapped_column(String(128), default="")
    dificultad: Mapped[str] = mapped_column(String(32), default="media")
    leccion_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    evaluacion: Mapped[CatalogEvaluation] = relationship(back_populates="preguntas")
