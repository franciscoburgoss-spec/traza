"""
Router: Documentos
Registro, listado, extraccion y eliminacion de documentos.
"""

import hashlib
import json
import os
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.database import get_db
from app.models import Documento, Evidencia, LogAuditoria, Proyecto
from app.schemas import (
    DocumentoConEvidencias,
    DocumentoCreate,
    DocumentoOut,
    EvidenciaCreate,
    EvidenciaOut,
)

router = APIRouter(prefix="/api/v1", tags=["documentos"])
settings = get_settings()


def _session_id() -> str:
    return f"{settings.SESSION_PREFIX}-{int(time.time())}-{os.getpid()}"


def _log(
    db: Session,
    entidad_tipo: str,
    entidad_id: UUID,
    accion: str,
    detalle: dict,
    session_id: str,
):
    log = LogAuditoria(
        entidad_tipo=entidad_tipo,
        entidad_id=entidad_id,
        accion=accion,
        detalle_json=json.dumps(detalle, default=str),
        session_id=session_id,
    )
    db.add(log)


def _compute_sha256(file_path: str) -> str:
    """Calcula SHA256 de un archivo local."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# POST /proyectos/{proyecto_id}/documentos
# ---------------------------------------------------------------------------

@router.post(
    "/proyectos/{proyecto_id}/documentos",
    response_model=DocumentoOut,
    status_code=status.HTTP_201_CREATED,
)
def registrar_documento(
    proyecto_id: UUID, payload: DocumentoCreate, db: Session = Depends(get_db)
):
    # Verificar que el proyecto existe
    proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not proyecto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado"
        )

    # Calcular hash si la ruta existe
    hash_val = None
    if payload.ruta_local and os.path.isfile(payload.ruta_local):
        hash_val = _compute_sha256(payload.ruta_local)

    doc = Documento(
        proyecto_id=proyecto_id,
        modulo=payload.modulo,
        tipo_documento=payload.tipo_documento,
        nombre_archivo=payload.nombre_archivo,
        ruta_local=payload.ruta_local,
        hash_sha256=hash_val,
        extraccion_estado="PENDIENTE",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    sid = _session_id()
    _log(
        db,
        "Documento",
        doc.id,
        "REGISTRAR",
        {
            "proyecto_id": str(proyecto_id),
            "nombre_archivo": payload.nombre_archivo,
            "modulo": payload.modulo,
        },
        sid,
    )
    db.commit()
    return doc


# ---------------------------------------------------------------------------
# GET /proyectos/{proyecto_id}/documentos
# ---------------------------------------------------------------------------

@router.get("/proyectos/{proyecto_id}/documentos", response_model=list[DocumentoOut])
def listar_documentos(proyecto_id: UUID, db: Session = Depends(get_db)):
    # Verificar proyecto
    proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not proyecto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado"
        )

    docs = (
        db.query(Documento)
        .filter(Documento.proyecto_id == proyecto_id)
        .order_by(Documento.created_at.desc())
        .all()
    )
    return docs


# ---------------------------------------------------------------------------
# POST /documentos/{id}/extraer
# ---------------------------------------------------------------------------

@router.post("/documentos/{documento_id}/extraer", response_model=list[EvidenciaOut])
def ejecutar_extraccion(documento_id: UUID, db: Session = Depends(get_db)):
    doc = (
        db.query(Documento).filter(Documento.id == documento_id).first()
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado"
        )

    sid = _session_id()

    # Ejecutar extractores basados en el tipo de documento
    evidencias_extraidas = _run_extractors(doc, db, sid)

    # Actualizar estado del documento
    doc.extraccion_estado = "EXTRAIDO"
    doc.extraccion_json = json.dumps(
        {"session_id": sid, "evidencias": len(evidencias_extraidas)}, default=str
    )
    db.commit()
    db.refresh(doc)

    _log(
        db,
        "Documento",
        doc.id,
        "EXTRAER",
        {"evidencias_extraidas": len(evidencias_extraidas), "session_id": sid},
        sid,
    )
    db.commit()
    return evidencias_extraidas


def _run_extractors(doc: Documento, db: Session, sid: str) -> list[Evidencia]:
    """
    Ejecuta extractores segun el tipo de documento.
    Este es un stub que simula la extraccion - se conectara
    con los 33 extractores reales en fase de integracion.
    """
    evidencias: list[Evidencia] = []

    # Stub: simular extraccion de algunos campos comunes
    campos_stub = {
        "MEMORIA_CALCULO": [
            {"campo": "area_construccion", "valor": "1250.50", "valor_tipo": "NUMERICO", "unidad": "m2"},
            {"campo": "altura_edificio", "valor": "18.5", "valor_tipo": "NUMERICO", "unidad": "m"},
            {"campo": "sistema_estructural", "valor": "Porticos de hormigon armado", "valor_tipo": "TEXTO"},
        ],
        "PLANOS_ESTRUCTURALES": [
            {"campo": "numero_pisos", "valor": "5", "valor_tipo": "NUMERICO", "unidad": "pisos"},
            {"campo": "tipo_cimentacion", "valor": "Zapata aislada", "valor_tipo": "TEXTO"},
        ],
        "ESPECIFICACIONES_TECNICAS": [
            {"campo": "resistencia_hormigon", "valor": "25", "valor_tipo": "NUMERICO", "unidad": "MPa"},
            {"campo": "acero_refuerzo", "valor": "A63-42H", "valor_tipo": "TEXTO"},
        ],
    }

    campos = campos_stub.get(doc.tipo_documento, [])

    for c in campos:
        ev = Evidencia(
            documento_id=doc.id,
            campo=c["campo"],
            valor=c["valor"],
            valor_tipo=c.get("valor_tipo"),
            unidad=c.get("unidad"),
            extractor="stub_extractor",
            confidence=0.92,
            validada_manual=False,
        )
        db.add(ev)
        evidencias.append(ev)

    db.commit()
    for ev in evidencias:
        db.refresh(ev)

    return evidencias


# ---------------------------------------------------------------------------
# GET /documentos/{id}/evidencias
# ---------------------------------------------------------------------------

@router.get("/documentos/{documento_id}/evidencias", response_model=list[EvidenciaOut])
def listar_evidencias_documento(documento_id: UUID, db: Session = Depends(get_db)):
    doc = db.query(Documento).filter(Documento.id == documento_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado"
        )

    evidencias = (
        db.query(Evidencia)
        .filter(Evidencia.documento_id == documento_id)
        .order_by(Evidencia.created_at.desc())
        .all()
    )
    return evidencias


# ---------------------------------------------------------------------------
# DELETE /documentos/{id}
# ---------------------------------------------------------------------------

@router.delete("/documentos/{documento_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_documento(documento_id: UUID, db: Session = Depends(get_db)):
    doc = db.query(Documento).filter(Documento.id == documento_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado"
        )

    sid = _session_id()
    _log(
        db,
        "Documento",
        doc.id,
        "ELIMINAR",
        {"nombre_archivo": doc.nombre_archivo, "modulo": doc.modulo},
        sid,
    )

    db.delete(doc)
    db.commit()
    return None
