"""Servicio de logging de auditoria para TRAZA."""
from sqlalchemy.orm import Session
import json
from app.models import LogAuditoria


def log_action(
    db: Session,
    entidad_tipo: str,
    entidad_id: str,
    accion: str,
    detalle_json: dict = None,
    session_id: str = None,
) -> LogAuditoria:
    log = LogAuditoria(
        entidad_tipo=entidad_tipo,
        entidad_id=entidad_id,
        accion=accion,
        detalle_json=json.dumps(detalle_json) if detalle_json else None,
        session_id=session_id,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
