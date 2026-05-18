"""
Router: Auditoria
Consulta de logs de auditoria con filtros.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Documento, Evidencia, LogAuditoria, Proyecto, Verificacion
from app.schemas import LogAuditoriaOut, PaginatedResponse

router = APIRouter(prefix="/api/v1", tags=["auditoria"])


# ---------------------------------------------------------------------------
# GET /auditoria
# ---------------------------------------------------------------------------

@router.get("/auditoria", response_model=PaginatedResponse)
def listar_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    entidad_tipo: str | None = Query(None),
    accion: str | None = Query(None),
    session_id: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(LogAuditoria)

    if entidad_tipo:
        query = query.filter(LogAuditoria.entidad_tipo == entidad_tipo)
    if accion:
        query = query.filter(LogAuditoria.accion == accion)
    if session_id:
        query = query.filter(LogAuditoria.session_id == session_id)

    total = query.count()
    items = (
        query.order_by(LogAuditoria.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaginatedResponse(
        total=total, page=page, page_size=page_size, items=items
    )


# ---------------------------------------------------------------------------
# GET /auditoria/proyecto/{proyecto_id}
# ---------------------------------------------------------------------------

@router.get("/auditoria/proyecto/{proyecto_id}", response_model=PaginatedResponse)
def logs_por_proyecto(
    proyecto_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not proyecto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado"
        )

    # Obtener IDs de entidades relacionadas
    doc_ids = [
        d[0]
        for d in db.query(Documento.id)
        .filter(Documento.proyecto_id == proyecto_id)
        .all()
    ]

    ev_ids = [
        e[0]
        for e in db.query(Evidencia.id)
        .filter(Evidencia.documento_id.in_(doc_ids))
        .all()
    ]

    ver_ids = [
        v[0]
        for v in db.query(Verificacion.id)
        .filter(Verificacion.evidencia_id.in_(ev_ids))
        .all()
    ]

    # Buscar logs relacionados
    query = db.query(LogAuditoria).filter(
        (
            (LogAuditoria.entidad_tipo == "Proyecto")
            & (LogAuditoria.entidad_id == proyecto_id)
        )
        | (
            (LogAuditoria.entidad_tipo == "Documento")
            & (LogAuditoria.entidad_id.in_(doc_ids))
        )
        | (
            (LogAuditoria.entidad_tipo == "Evidencia")
            & (LogAuditoria.entidad_id.in_(ev_ids))
        )
        | (
            (LogAuditoria.entidad_tipo == "Verificacion")
            & (LogAuditoria.entidad_id.in_(ver_ids))
        )
    )

    total = query.count()
    items = (
        query.order_by(LogAuditoria.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaginatedResponse(
        total=total, page=page, page_size=page_size, items=items
    )
