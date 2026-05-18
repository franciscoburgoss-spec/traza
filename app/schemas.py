"""Pydantic v2 schemas para request/response de todas las entidades TRAZA."""
from datetime import datetime
from typing import Optional, List, Generic, TypeVar
from pydantic import BaseModel, ConfigDict


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Respuesta paginada generica."""
    items: List[T]
    total: int
    page: int = 1
    page_size: int = 50


# ──────────────────────────────────────────────
# Proyecto
# ──────────────────────────────────────────────
class ProyectoCreate(BaseModel):
    codigo: str
    nombre: str
    tipo_proyecto: Optional[str] = None
    ref_comuna: Optional[str] = None
    ref_zona_sismica: Optional[int] = None
    ref_tipo_suelo: Optional[str] = None
    ref_Ao: Optional[float] = None
    estado: Optional[str] = "ACTIVO"


class ProyectoUpdate(BaseModel):
    nombre: Optional[str] = None
    tipo_proyecto: Optional[str] = None
    ref_comuna: Optional[str] = None
    ref_zona_sismica: Optional[int] = None
    ref_tipo_suelo: Optional[str] = None
    ref_Ao: Optional[float] = None
    estado: Optional[str] = None


class ProyectoEstadoPatch(BaseModel):
    estado: str


class ProyectoRead(BaseModel):
    id: str
    codigo: str
    nombre: str
    tipo_proyecto: Optional[str] = None
    ref_comuna: Optional[str] = None
    ref_zona_sismica: Optional[int] = None
    ref_tipo_suelo: Optional[str] = None
    ref_Ao: Optional[float] = None
    estado: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Alias para compatibilidad con routers
ProyectoOut = ProyectoRead


class ProyectoWithDocumentos(ProyectoRead):
    documentos: List[dict] = []


# ──────────────────────────────────────────────
# Documento
# ──────────────────────────────────────────────
class DocumentoCreate(BaseModel):
    proyecto_id: str
    modulo: Optional[str] = None
    tipo_documento: Optional[str] = None
    nombre_archivo: str
    ruta_local: Optional[str] = None
    hash_sha256: Optional[str] = None
    extraccion_estado: Optional[str] = "PENDIENTE"
    extraccion_json: Optional[str] = None


class DocumentoRead(BaseModel):
    id: str
    proyecto_id: str
    modulo: Optional[str] = None
    tipo_documento: Optional[str] = None
    nombre_archivo: str
    ruta_local: Optional[str] = None
    hash_sha256: Optional[str] = None
    extraccion_estado: Optional[str] = None
    extraccion_json: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Alias para compatibilidad con routers
DocumentoOut = DocumentoRead


class DocumentoConEvidencias(DocumentoRead):
    """Documento con sus evidencias anidadas."""
    evidencias: List["EvidenciaRead"] = []


# ──────────────────────────────────────────────
# Evidencia
# ──────────────────────────────────────────────
class EvidenciaCreate(BaseModel):
    documento_id: str
    campo: str
    valor: Optional[str] = None
    valor_tipo: Optional[str] = None
    unidad: Optional[str] = None
    source_page: Optional[int] = None
    extractor: Optional[str] = None
    confidence: Optional[float] = 1.0
    validada_manual: Optional[bool] = False
    observacion: Optional[str] = None


class EvidenciaRead(BaseModel):
    id: str
    documento_id: str
    campo: str
    valor: Optional[str] = None
    valor_tipo: Optional[str] = None
    unidad: Optional[str] = None
    source_page: Optional[int] = None
    extractor: Optional[str] = None
    confidence: Optional[float] = None
    validada_manual: Optional[bool] = None
    observacion: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Alias para compatibilidad con routers
EvidenciaOut = EvidenciaRead


class EvidenciaUpdate(BaseModel):
    campo: Optional[str] = None
    valor: Optional[str] = None
    valor_tipo: Optional[str] = None
    unidad: Optional[str] = None
    observacion: Optional[str] = None


class EvidenciaValidarPatch(BaseModel):
    validada_manual: bool


# ──────────────────────────────────────────────
# Verificacion
# ──────────────────────────────────────────────
class VerificacionCreate(BaseModel):
    evidencia_id: Optional[str] = None
    regla_codigo: str
    resultado: str
    mensaje: Optional[str] = None
    payload_json: Optional[str] = None
    session_id: Optional[str] = None


class VerificacionRead(BaseModel):
    id: str
    evidencia_id: str
    regla_codigo: str
    resultado: str
    mensaje: Optional[str] = None
    payload_json: Optional[str] = None
    session_id: Optional[str] = None
    ejecutada_en: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Alias para compatibilidad con routers
VerificacionOut = VerificacionRead


class VerificacionPayload(BaseModel):
    """Payload para ejecutar verificaciones sobre un proyecto."""
    session_id: Optional[str] = None
    solo_pendientes: bool = False


# ──────────────────────────────────────────────
# Dictamen
# ──────────────────────────────────────────────
class DictamenRead(BaseModel):
    id: str
    proyecto_id: str
    estado: Optional[str] = None
    total_verificaciones: Optional[int] = None
    total_cumplen: Optional[int] = None
    total_no_cumplen: Optional[int] = None
    justificacion: Optional[str] = None
    score: Optional[float] = None
    hab_html: Optional[str] = None
    dictamen_texto: Optional[str] = None
    editable: Optional[bool] = None
    session_id: Optional[str] = None
    generado_en: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Alias para compatibilidad con routers
DictamenOut = DictamenRead


class DictamenUpdate(BaseModel):
    estado: Optional[str] = None
    score: Optional[float] = None
    justificacion: Optional[str] = None
    hab_html: Optional[str] = None
    dictamen_texto: Optional[str] = None
    editable: Optional[bool] = None


class DictamenEstadoPatch(BaseModel):
    estado: str


# ──────────────────────────────────────────────
# LogAuditoria
# ──────────────────────────────────────────────
class LogAuditoriaRead(BaseModel):
    id: str
    entidad_tipo: str
    entidad_id: str
    accion: str
    detalle_json: Optional[str] = None
    session_id: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Alias para compatibilidad con routers
LogAuditoriaOut = LogAuditoriaRead
