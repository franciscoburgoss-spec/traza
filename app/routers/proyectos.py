"""
Router: Proyectos
CRUD completo + cambio de estado para proyectos.
"""

import json
import os
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.database import get_db
from app.models import Documento, Evidencia, LogAuditoria, Proyecto
from app.schemas import (
    PaginatedResponse,
    ProyectoCreate,
    ProyectoEstadoPatch,
    ProyectoOut,
    ProyectoUpdate,
    ProyectoWithDocumentos,
)

router = APIRouter(prefix="/api/v1", tags=["proyectos"])
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
# POST /proyectos
# ---------------------------------------------------------------------------

@router.post("/proyectos", response_model=ProyectoOut, status_code=status.HTTP_201_CREATED)
def crear_proyecto(payload: ProyectoCreate, db: Session = Depends(get_db)):
    # Verificar unicidad de codigo
    existente = db.query(Proyecto).filter(Proyecto.codigo == payload.codigo).first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un proyecto con codigo '{payload.codigo}'",
        )

    proyecto = Proyecto(**payload.model_dump())
    db.add(proyecto)
    db.commit()
    db.refresh(proyecto)

    sid = _session_id()
    _log(
        db,
        "Proyecto",
        proyecto.id,
        "CREAR",
        {"codigo": payload.codigo, "nombre": payload.nombre},
        sid,
    )
    db.commit()
    return proyecto


# ---------------------------------------------------------------------------
# GET /proyectos
# ---------------------------------------------------------------------------

@router.get("/proyectos", response_model=PaginatedResponse)
def listar_proyectos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    estado: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Proyecto)
    if estado:
        query = query.filter(Proyecto.estado == estado)

    total = query.count()
    items = (
        query.order_by(Proyecto.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaginatedResponse(
        total=total, page=page, page_size=page_size, items=items
    )


# ---------------------------------------------------------------------------
# GET /proyectos/{id}
# ---------------------------------------------------------------------------

@router.get("/proyectos/{proyecto_id}", response_model=ProyectoWithDocumentos)
def ver_proyecto(proyecto_id: UUID, db: Session = Depends(get_db)):
    proyecto = (
        db.query(Proyecto)
        .options(joinedload(Proyecto.documentos))
        .filter(Proyecto.id == proyecto_id)
        .first()
    )
    if not proyecto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado",
        )
    return proyecto


# ---------------------------------------------------------------------------
# PUT /proyectos/{id}
# ---------------------------------------------------------------------------

@router.put("/proyectos/{proyecto_id}", response_model=ProyectoOut)
def actualizar_proyecto(
    proyecto_id: UUID, payload: ProyectoUpdate, db: Session = Depends(get_db)
):
    proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not proyecto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado",
        )

    datos = payload.model_dump(exclude_unset=True)
    for campo, valor in datos.items():
        setattr(proyecto, campo, valor)

    db.commit()
    db.refresh(proyecto)

    sid = _session_id()
    _log(db, "Proyecto", proyecto.id, "ACTUALIZAR", datos, sid)
    db.commit()
    return proyecto


# ---------------------------------------------------------------------------
# DELETE /proyectos/{id}
# ---------------------------------------------------------------------------

@router.delete("/proyectos/{proyecto_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_proyecto(proyecto_id: UUID, db: Session = Depends(get_db)):
    proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not proyecto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado",
        )

    sid = _session_id()
    _log(
        db,
        "Proyecto",
        proyecto.id,
        "ELIMINAR",
        {"codigo": proyecto.codigo, "nombre": proyecto.nombre},
        sid,
    )

    db.delete(proyecto)
    db.commit()
    return None


# ---------------------------------------------------------------------------
# PATCH /proyectos/{id}/estado
# ---------------------------------------------------------------------------

@router.patch("/proyectos/{proyecto_id}/estado", response_model=ProyectoOut)
def cambiar_estado_proyecto(
    proyecto_id: UUID, payload: ProyectoEstadoPatch, db: Session = Depends(get_db)
):
    proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not proyecto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado",
        )

    estado_anterior = proyecto.estado
    proyecto.estado = payload.estado
    db.commit()
    db.refresh(proyecto)

    sid = _session_id()
    _log(
        db,
        "Proyecto",
        proyecto.id,
        "CAMBIAR_ESTADO",
        {"anterior": estado_anterior, "nuevo": payload.estado},
        sid,
    )
    db.commit()
    return proyecto
