"""CRUD de Proyectos con SQLAlchemy 2.0."""
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from typing import List, Optional

from app.models import Proyecto
from app.schemas import ProyectoCreate


def crear_proyecto(db: Session, data: ProyectoCreate) -> Proyecto:
    proyecto = Proyecto(
        codigo=data.codigo,
        nombre=data.nombre,
        tipo_proyecto=data.tipo_proyecto,
        ref_comuna=data.ref_comuna,
        ref_zona_sismica=data.ref_zona_sismica,
        ref_tipo_suelo=data.ref_tipo_suelo,
        ref_Ao=data.ref_Ao,
        estado=data.estado or "ACTIVO",
    )
    db.add(proyecto)
    db.commit()
    db.refresh(proyecto)
    return proyecto


def get_proyecto(db: Session, proyecto_id: str) -> Optional[Proyecto]:
    return db.get(Proyecto, proyecto_id)


def get_proyecto_by_codigo(db: Session, codigo: str) -> Optional[Proyecto]:
    stmt = select(Proyecto).where(Proyecto.codigo == codigo)
    return db.execute(stmt).scalar_one_or_none()


def listar_proyectos(db: Session, skip: int = 0, limit: int = 100) -> List[Proyecto]:
    stmt = select(Proyecto).offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


def actualizar_estado(db: Session, proyecto_id: str, nuevo_estado: str) -> Optional[Proyecto]:
    stmt = (
        update(Proyecto)
        .where(Proyecto.id == proyecto_id)
        .values(estado=nuevo_estado)
        .execution_options(synchronize_session="fetch")
    )
    db.execute(stmt)
    db.commit()
    return get_proyecto(db, proyecto_id)
