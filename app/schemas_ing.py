"""Pydantic v2 schemas para el Modulo ING (request/response)."""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, field_validator


# ============================================================
# Solicitud ING
# ============================================================

class SolicitudIngCreate(BaseModel):
    """Datos para crear una Solicitud ING #1. El acronimo y proyecto se generan automaticamente.
    La zona sismica se calcula automaticamente desde la comuna (INMUTABLE)."""
    nombre_proyecto: str
    empresa: str
    tipo_proyecto: str = "HAB"  # HAB / TEC / DOS / OTR
    comuna: str  # Nombre de la comuna (seleccionada de lista de 33)
    modulos: List[str] = Field(default_factory=list)
    fecha_solicitud: Optional[str] = None  # Fecha de recepcion (YYYY-MM-DD)
    fecha_limite: Optional[str] = None     # Fecha limite de respuesta (YYYY-MM-DD)
    link_descarga: Optional[str] = None
    zona_sismica: Optional[int] = None     # Se sobreescribe automaticamente desde comuna
    tipologias: Optional[List[str]] = None

    @field_validator("empresa")
    @classmethod
    def empresa_no_vacia(cls, v: str) -> str:
        """La empresa no puede estar vacia ni ser solo espacios."""
        v = v.strip()
        if not v:
            raise ValueError("La empresa desarrolladora es obligatoria (no puede estar vacia)")
        if len(v) < 2:
            raise ValueError("La empresa debe tener al menos 2 caracteres")
        return v

    @field_validator("nombre_proyecto")
    @classmethod
    def nombre_no_vacio(cls, v: str) -> str:
        """El nombre del proyecto no puede estar vacio."""
        v = v.strip()
        if not v:
            raise ValueError("El nombre del proyecto es obligatorio")
        if len(v) < 3:
            raise ValueError("El nombre del proyecto debe tener al menos 3 caracteres")
        return v

    @field_validator("comuna")
    @classmethod
    def comuna_no_vacia(cls, v: str) -> str:
        """La comuna es obligatoria."""
        v = v.strip()
        if not v:
            raise ValueError("La comuna es obligatoria — seleccione una de las 33 comunas de O'Higgins")
        return v

    @field_validator("tipo_proyecto")
    @classmethod
    def tipo_valido(cls, v: str) -> str:
        """El tipo de proyecto debe ser uno de los 4 validos."""
        validos = {"HAB", "TEC", "DOS", "OTR"}
        if v.upper() not in validos:
            raise ValueError(f"Tipo de proyecto invalido. Valores validos: {', '.join(sorted(validos))}")
        return v.upper()

    @field_validator("fecha_limite")
    @classmethod
    def validar_fechas(cls, v: Optional[str], info) -> Optional[str]:
        """La fecha limite debe ser posterior o igual a la fecha de solicitud."""
        if not v:
            return v
        fecha_sol = info.data.get("fecha_solicitud")
        if fecha_sol and fecha_sol > v:
            raise ValueError("La fecha limite no puede ser anterior a la fecha de solicitud")
        return v


class SolicitudIngUpdate(BaseModel):
    nombre_proyecto: Optional[str] = None
    empresa: Optional[str] = None
    tipo_proyecto: Optional[str] = None
    comuna: Optional[str] = None
    modulos: Optional[List[str]] = None
    fecha_solicitud: Optional[str] = None
    fecha_limite: Optional[str] = None
    link_descarga: Optional[str] = None
    zona_sismica: Optional[int] = None
    superficie_terreno: Optional[float] = None
    cantidad_calicatas: Optional[int] = None
    tipologias: Optional[List[str]] = None


class SolicitudIngEstadoPatch(BaseModel):
    estado: str  # recibida / en_revision / aceptada / observada


class SolicitudIngRead(BaseModel):
    id: str
    proyecto_id: Optional[str] = None
    acronimo_proyecto: Optional[str] = None
    numero_iteracion: int
    solicitud_anterior_id: Optional[str] = None
    estado: str
    nombre_proyecto: str
    empresa: str
    tipo_proyecto: str
    comuna: Optional[str] = None
    comuna_codigo: Optional[str] = None
    modulos_lista: List[str] = Field(default_factory=list)
    fecha_solicitud: Optional[str] = None
    fecha_limite: Optional[str] = None
    link_descarga: Optional[str] = None
    zona_sismica: Optional[int] = None
    superficie_terreno: Optional[float] = None
    cantidad_calicatas: Optional[int] = None
    tipologias_lista: List[str] = Field(default_factory=list)
    ruta_carpeta: Optional[str] = None
    email_generado: Optional[str] = None
    fecha_envio_email: Optional[datetime] = None
    session_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_json(cls, obj: Any) -> "SolicitudIngRead":
        """Construye desde ORM parseando campos JSON."""
        data = {}
        for field in obj.__table__.columns.keys():
            data[field] = getattr(obj, field)
        # Parsear JSON
        data["modulos_lista"] = obj.get_modulos() if hasattr(obj, "get_modulos") else []
        data["tipologias_lista"] = obj.get_tipologias() if hasattr(obj, "get_tipologias") else []
        return cls(**data)


SolicitudIngOut = SolicitudIngRead


class SolicitudIngDetalle(SolicitudIngRead):
    """Solicitud con documentos y revisiones anidadas."""
    documentos: List["DocumentoIngRead"] = Field(default_factory=list)
    revisiones: List["RevisionCruzadaRead"] = Field(default_factory=list)
    conteo_documentos: Dict[str, int] = Field(default_factory=dict)
    progreso_revisiones: Dict[str, Any] = Field(default_factory=dict)
    puede_pasar_a_r01: bool = False


class SolicitudIngResumen(BaseModel):
    """Resumen para listados (card view)."""
    id: str
    acronimo_proyecto: Optional[str] = None
    numero_iteracion: int
    estado: str
    nombre_proyecto: str
    empresa: str
    tipo_proyecto: Optional[str] = None
    comuna: Optional[str] = None
    modulos_lista: List[str] = Field(default_factory=list)
    fecha_solicitud: Optional[str] = None
    fecha_limite: Optional[str] = None
    total_documentos: int = 0
    documentos_aceptados: int = 0
    documentos_observados: int = 0
    documentos_faltantes: int = 0
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# Documento ING
# ============================================================

class DocumentoIngCreate(BaseModel):
    nombre_archivo: str
    tipo_documento: str  # MEMORIA / PLANO / INFORME / PRESUPUESTO / OTRO
    modulo: str  # MDS / EST / HAB / URB
    tipologia: Optional[str] = None
    ruta_local: Optional[str] = None
    hash_sha256: Optional[str] = None


class DocumentoIngEstadoPatch(BaseModel):
    estado: str  # pendiente / aceptado / observado / faltante / no_aplica
    observacion: Optional[str] = None


class DocumentoIngRead(BaseModel):
    id: str
    solicitud_ing_id: str
    nombre_archivo: str
    tipo_documento: str
    modulo: str
    tipologia: Optional[str] = None
    estado: str
    observacion: Optional[str] = None
    hash_sha256: Optional[str] = None
    ruta_local: Optional[str] = None
    iteracion_aceptada_en: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


DocumentoIngOut = DocumentoIngRead


class DocumentoIngListado(BaseModel):
    """Documentos agrupados por modulo para la UI."""
    MDS: List[DocumentoIngRead] = Field(default_factory=list)
    EST: List[DocumentoIngRead] = Field(default_factory=list)
    HAB: List[DocumentoIngRead] = Field(default_factory=list)
    URB: List[DocumentoIngRead] = Field(default_factory=list)


class DocumentoIngComparacion(BaseModel):
    """Para comparar dos documentos (deteccion de copias)."""
    son_identicos: bool
    hash_1: Optional[str] = None
    hash_2: Optional[str] = None
    tamano_1: Optional[int] = None
    tamano_2: Optional[int] = None


# ============================================================
# Revision Cruzada
# ============================================================

class RevisionCruzadaCreate(BaseModel):
    tipo_revision: str  # MDS_TOPO / EST_ARQ / HAB_PRES
    numero_revision: str
    descripcion: str
    fuente_1: Optional[str] = None
    valor_1: Optional[str] = None
    fuente_2: Optional[str] = None
    valor_2: Optional[str] = None


class RevisionCruzadaEstadoPatch(BaseModel):
    estado: str  # pendiente / aceptado / observado / faltante
    observacion: Optional[str] = None
    fran_marco: bool = True


class RevisionCruzadaRead(BaseModel):
    id: str
    solicitud_ing_id: str
    tipo_revision: str
    numero_revision: str
    descripcion: str
    fuente_1: Optional[str] = None
    valor_1: Optional[str] = None
    fuente_2: Optional[str] = None
    valor_2: Optional[str] = None
    estado: str
    observacion: Optional[str] = None
    fran_marco: bool
    session_id: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


RevisionCruzadaOut = RevisionCruzadaRead


class RevisionCruzadaListado(BaseModel):
    """Revisiones agrupadas por tipo para la UI."""
    MDS_TOPO: List[RevisionCruzadaRead] = Field(default_factory=list)
    EST_ARQ: List[RevisionCruzadaRead] = Field(default_factory=list)
    HAB_PRES: List[RevisionCruzadaRead] = Field(default_factory=list)


# ============================================================
# Email
# ============================================================

class EmailGeneradoRead(BaseModel):
    asunto: str
    cuerpo: str            # Version texto plano (fallback)
    cuerpo_html: str       # Version HTML profesional
    estadisticas: Dict[str, Any]
    session_id: str


class EmailEnviadoPatch(BaseModel):
    """Registrar que el email fue enviado."""
    pass


# ============================================================
# Dashboard / Estadisticas
# ============================================================

class IngDashboard(BaseModel):
    en_revision: int
    aceptadas: int
    observadas: int
    recibidas: int
    vencimiento_proximo: List[Dict[str, Any]] = Field(default_factory=list)
    iteraciones_mes: int = 0


class IngHistorialIteracion(BaseModel):
    """Resumen de una iteracion para el historial."""
    id: str
    numero_iteracion: int
    estado: str
    total_documentos: int
    aceptados: int
    observados: int
    faltantes: int
    created_at: Optional[datetime] = None


class IngComparacionIteraciones(BaseModel):
    """Comparacion ING #N vs ING #(N+1)."""
    ing_anterior_id: str
    ing_anterior_numero: int
    ing_nueva_id: str
    ing_nueva_numero: int
    cambios: List[Dict[str, Any]] = Field(default_factory=list)
    resultado: str  # "aceptada" / "observada"


# ============================================================
# Siguiente Iteracion (R6)
# ============================================================

class SiguienteIteracionRead(BaseModel):
    """Respuesta al crear ING #(N+1)."""
    solicitud_nueva: SolicitudIngRead
    documentos_heredados: int
    documentos_pendientes: int
    mensaje: str


# ============================================================
# 1.8: Listado con estado vacio amigable
# ============================================================

class SolicitudIngListadoResponse(BaseModel):
    """Respuesta paginada del listado de solicitudes ING.
    Cuando no hay solicitudes, incluye mensaje amigable y CTA."""
    solicitudes: List[SolicitudIngResumen] = Field(default_factory=list)
    total: int = 0
    vacio: bool = True
    mensaje: Optional[str] = None
    cta_texto: Optional[str] = None
    cta_url: Optional[str] = None
