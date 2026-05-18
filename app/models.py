"""Modelos SQLAlchemy 2.0 declarativos para TRAZA."""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Float, Integer, Boolean, TIMESTAMP, ForeignKey

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Proyecto(Base):
    __tablename__ = "Proyecto"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    codigo: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    tipo_proyecto: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ref_comuna: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ref_zona_sismica: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ref_tipo_suelo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ref_Ao: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    estado: Mapped[Optional[str]] = mapped_column(Text, default="ACTIVO")
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, default=datetime.utcnow)


class Documento(Base):
    __tablename__ = "Documento"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    proyecto_id: Mapped[str] = mapped_column(Text, ForeignKey("Proyecto.id", ondelete="CASCADE"), nullable=False)
    modulo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tipo_documento: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    nombre_archivo: Mapped[str] = mapped_column(Text, nullable=False)
    ruta_local: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hash_sha256: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extraccion_estado: Mapped[Optional[str]] = mapped_column(Text, default="PENDIENTE")
    extraccion_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, default=datetime.utcnow)


class Evidencia(Base):
    __tablename__ = "Evidencia"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    documento_id: Mapped[str] = mapped_column(Text, ForeignKey("Documento.id", ondelete="CASCADE"), nullable=False)
    campo: Mapped[str] = mapped_column(Text, nullable=False)
    valor: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    valor_tipo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unidad: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    extractor: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, default=1.0)
    validada_manual: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    observacion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, default=datetime.utcnow)


class Verificacion(Base):
    __tablename__ = "Verificacion"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    evidencia_id: Mapped[Optional[str]] = mapped_column(Text, ForeignKey("Evidencia.id", ondelete="CASCADE"), nullable=True)
    regla_codigo: Mapped[str] = mapped_column(Text, nullable=False)
    resultado: Mapped[str] = mapped_column(Text, nullable=False)
    mensaje: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payload_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ejecutada_en: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, default=datetime.utcnow)


class Dictamen(Base):
    __tablename__ = "Dictamen"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    proyecto_id: Mapped[str] = mapped_column(Text, ForeignKey("Proyecto.id", ondelete="CASCADE"), nullable=False, unique=True)
    estado: Mapped[Optional[str]] = mapped_column(Text, default="EN_PROCESO")
    total_verificaciones: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    total_cumplen: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    total_no_cumplen: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    justificacion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hab_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dictamen_texto: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    editable: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)
    session_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generado_en: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, default=datetime.utcnow)


class LogAuditoria(Base):
    __tablename__ = "LogAuditoria"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    entidad_tipo: Mapped[str] = mapped_column(Text, nullable=False)
    entidad_id: Mapped[str] = mapped_column(Text, nullable=False)
    accion: Mapped[str] = mapped_column(Text, nullable=False)
    detalle_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, default=datetime.utcnow)