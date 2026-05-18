"""
Router: Evidencias
Listado, creacion manual, actualizacion, validacion y eliminacion de evidencias.
"""

import json
import os
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Documento, Evidencia, LogAuditoria
from app.schemas import (
    EvidenciaCreate,
    EvidenciaOut,
    EvidenciaUpdate,
    EvidenciaValidarPatch,
    PaginatedResponse,
)

router = APIRouter(prefix="/api/v1", tags=["evidencias"])
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


# ---------------------------------------------------------------------------
# GET /evidencias
# ---------------------------------------------------------------------------

@router.get("/evidencias", response_model=PaginatedResponse)
def listar_evidencias(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    documento_id: UUID | None = Query(None),
    campo: str | None = Query(None),
    extractor: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Evidencia)

    if documento_id:
        query = query.filter(Evidencia.documento_id == documento_id)
    if campo:
        query = query.filter(Evidencia.campo.ilike(f"%{campo}%"))
    if extractor:
        query = query.filter(Evidencia.extractor == extractor)

    total = query.count()
    items = (
        query.order_by(Evidencia.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaginatedResponse(
        total=total, page=page, page_size=page_size, items=items
    )


# ---------------------------------------------------------------------------
# POST /evidencias
# ---------------------------------------------------------------------------

@router.post("/evidencias", response_model=EvidenciaOut, status_code=status.HTTP_201_CREATED)
def crear_evidencia_manual(payload: EvidenciaCreate, db: Session = Depends(get_db)):
    # Verificar que el documento existe
    doc = db.query(Documento).filter(Documento.id == payload.documento_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado"
        )

    datos = payload.model_dump()
    datos["validada_manual"] = True  # Evidencias manuales se marcan como validadas
    datos["extractor"] = "MANUAL"

    evidencia = Evidencia(**datos)
    db.add(evidencia)
    db.commit()
    db.refresh(evidencia)

    sid = _session_id()
    _log(
        db,
        "Evidencia",
        evidencia.id,
        "CREAR_MANUAL",
        {"documento_id": str(payload.documento_id), "campo": payload.campo},
        sid,
    )
    db.commit()
    return evidencia


# ---------------------------------------------------------------------------
# PUT /evidencias/{id}
# ---------------------------------------------------------------------------

@router.put("/evidencias/{evidencia_id}", response_model=EvidenciaOut)
def actualizar_evidencia(
    evidencia_id: UUID, payload: EvidenciaUpdate, db: Session = Depends(get_db)
):
    ev = db.query(Evidencia).filter(Evidencia.id == evidencia_id).first()
    if not ev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Evidencia no encontrada"
        )

    datos = payload.model_dump(exclude_unset=True)
    for campo, valor in datos.items():
        setattr(ev, campo, valor)

    db.commit()
    db.refresh(ev)

    sid = _session_id()
    _log(db, "Evidencia", ev.id, "ACTUALIZAR", datos, sid)
    db.commit()
    return ev


# ---------------------------------------------------------------------------
# PATCH /evidencias/{id}/validar
# ---------------------------------------------------------------------------

@router.patch("/evidencias/{evidencia_id}/validar", response_model=EvidenciaOut)
def validar_evidencia(
    evidencia_id: UUID, payload: EvidenciaValidarPatch, db: Session = Depends(get_db)
):
    ev = db.query(Evidencia).filter(Evidencia.id == evidencia_id).first()
    if not ev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Evidencia no encontrada"
        )

    ev.validada_manual = payload.validada_manual
    if payload.observacion is not None:
        ev.observacion = payload.observacion

    db.commit()
    db.refresh(ev)

    sid = _session_id()
    _log(
        db,
        "Evidencia",
        ev.id,
        "VALIDAR",
        {"validada_manual": payload.validada_manual, "observacion": payload.observacion},
        sid,
    )
    db.commit()
    return ev


# ---------------------------------------------------------------------------
# DELETE /evidencias/{id}
# ---------------------------------------------------------------------------

@router.delete("/evidencias/{evidencia_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_evidencia(evidencia_id: UUID, db: Session = Depends(get_db)):
    ev = db.query(Evidencia).filter(Evidencia.id == evidencia_id).first()
    if not ev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Evidencia no encontrada"
        )

    sid = _session_id()
    _log(
        db,
        "Evidencia",
        ev.id,
        "ELIMINAR",
        {"campo": ev.campo, "documento_id": str(ev.documento_id)},
        sid,
    )

    db.delete(ev)
    db.commit()
    return None
