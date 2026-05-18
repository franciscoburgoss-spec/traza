"""Modelos SQLAlchemy 2.0 para el Modulo ING (Ingreso al Banco de Proyectos)."""
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Float, Integer, Boolean, TIMESTAMP, ForeignKey

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class SolicitudIng(Base):
    """Solicitud de ingreso al banco de proyectos (ING #1, #2, #3...)."""
    __tablename__ = "solicitud_ing"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    # El proyecto se crea automaticamente al aceptar la solicitud
    proyecto_id: Mapped[Optional[str]] = mapped_column(Text, ForeignKey("Proyecto.id", ondelete="SET NULL"), nullable=True)
    acronimo_proyecto: Mapped[Optional[str]] = mapped_column(Text, nullable=True, index=True)
    numero_iteracion: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    solicitud_anterior_id: Mapped[Optional[str]] = mapped_column(Text, ForeignKey("solicitud_ing.id", ondelete="RESTRICT"), nullable=True)
    estado: Mapped[str] = mapped_column(Text, nullable=False, default="recibida")
    nombre_proyecto: Mapped[str] = mapped_column(Text, nullable=False)
    empresa: Mapped[str] = mapped_column(Text, nullable=False)
    tipo_proyecto: Mapped[str] = mapped_column(Text, nullable=False, default="HAB")
    comuna: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    comuna_codigo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    modulos: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    fecha_solicitud: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fecha_limite: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    link_descarga: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    zona_sismica: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    superficie_terreno: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cantidad_calicatas: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tipologias: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ruta_carpeta: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    email_generado: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fecha_envio_email: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    session_id: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, default=datetime.utcnow)

    # Relaciones
    documentos: Mapped[List["DocumentoIng"]] = relationship("DocumentoIng", back_populates="solicitud", cascade="all, delete-orphan", lazy="selectin")
    revisiones: Mapped[List["RevisionCruzada"]] = relationship("RevisionCruzada", back_populates="solicitud", cascade="all, delete-orphan", lazy="selectin")

    # Helpers JSON
    def get_modulos(self) -> List[str]:
        try:
            return json.loads(self.modulos)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_modulos(self, modulos: List[str]) -> None:
        self.modulos = json.dumps(modulos)

    def get_tipologias(self) -> List[str]:
        try:
            return json.loads(self.tipologias or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    def set_tipologias(self, tipologias: List[str]) -> None:
        self.tipologias = json.dumps(tipologias)

    # Business logic helpers
    def puede_pasar_a_r01(self) -> bool:
        """R5: Solo si estado es 'aceptada'."""
        return self.estado == "aceptada"

    def recalcular_estado(self) -> str:
        """R4: Si todos los documentos estan aceptados/no_aplica -> aceptada."""
        if not self.documentos:
            return self.estado

        for doc in self.documentos:
            if doc.estado not in ("aceptado", "no_aplica"):
                return "observada"
        return "aceptada"

    def conteo_documentos(self) -> Dict[str, int]:
        """Retorna conteo por estado de documentos."""
        conteo = {"pendiente": 0, "aceptado": 0, "observado": 0, "faltante": 0, "no_aplica": 0, "total": 0}
        for doc in self.documentos:
            conteo[doc.estado] = conteo.get(doc.estado, 0) + 1
            conteo["total"] += 1
        return conteo

    def progreso_revisiones(self) -> Dict[str, Any]:
        """Retorna progreso del checklist de revisiones cruzadas."""
        if not self.revisiones:
            return {"total": 0, "revisadas": 0, "aceptadas": 0, "observadas": 0, "faltantes": 0}

        result = {"total": len(self.revisiones), "revisadas": 0, "aceptadas": 0, "observadas": 0, "faltantes": 0}
        for rev in self.revisiones:
            if rev.fran_marco:
                result["revisadas"] += 1
            if rev.estado == "aceptado":
                result["aceptadas"] += 1
            elif rev.estado == "observado":
                result["observadas"] += 1
            elif rev.estado == "faltante":
                result["faltantes"] += 1
        return result


class DocumentoIng(Base):
    """Documento registrado en una solicitud ING."""
    __tablename__ = "documento_ing"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    solicitud_ing_id: Mapped[str] = mapped_column(Text, ForeignKey("solicitud_ing.id", ondelete="CASCADE"), nullable=False)
    nombre_archivo: Mapped[str] = mapped_column(Text, nullable=False)
    tipo_documento: Mapped[str] = mapped_column(Text, nullable=False)
    modulo: Mapped[str] = mapped_column(Text, nullable=False)
    tipologia: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(Text, nullable=False, default="pendiente")
    observacion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hash_sha256: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ruta_local: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    iteracion_aceptada_en: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, default=datetime.utcnow)

    # Relaciones
    solicitud: Mapped["SolicitudIng"] = relationship("SolicitudIng", back_populates="documentos")


class RevisionCruzada(Base):
    """Checklist de revisiones cruzadas (3.1 MDS_TOPO, 3.2 EST_ARQ, 3.3 HAB_PRES)."""
    __tablename__ = "revision_cruzada"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    solicitud_ing_id: Mapped[str] = mapped_column(Text, ForeignKey("solicitud_ing.id", ondelete="CASCADE"), nullable=False)
    tipo_revision: Mapped[str] = mapped_column(Text, nullable=False)
    numero_revision: Mapped[str] = mapped_column(Text, nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    fuente_1: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    valor_1: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fuente_2: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    valor_2: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(Text, nullable=False, default="pendiente")
    observacion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fran_marco: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    session_id: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, default=datetime.utcnow)

    # Relaciones
    solicitud: Mapped["SolicitudIng"] = relationship("SolicitudIng", back_populates="revisiones")


class TablaCalicatasMinimas(Base):
    """Tabla normativa: calicatas minimas segun superficie del terreno."""
    __tablename__ = "tabla_calicatas_minimas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    superficie_min: Mapped[int] = mapped_column(Integer, nullable=False)
    superficie_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    calicatas_minimas: Mapped[int] = mapped_column(Integer, nullable=False)
    observacion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    @classmethod
    def calicatas_para_superficie(cls, superficie_m2: float) -> int:
        """Retorna el numero minimo de calicatas para una superficie dada."""
        if superficie_m2 < 2000:
            return 2
        elif superficie_m2 < 5000:
            return 3
        elif superficie_m2 < 10000:
            return 4
        else:
            # 5 + 1 por cada 5000 m2 adicional
            adicional = max(0, int((superficie_m2 - 10000) / 5000))
            return 5 + adicional
