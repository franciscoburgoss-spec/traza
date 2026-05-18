"""
Router: Verificaciones
Ejecucion de reglas de verificacion y consulta de resultados.
"""

import json
import os
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import (
    Dictamen,
    Documento,
    Evidencia,
    LogAuditoria,
    Proyecto,
    Verificacion,
)
from app.schemas import (
    DictamenOut,
    PaginatedResponse,
    VerificacionOut,
    VerificacionPayload,
)

router = APIRouter(prefix="/api/v1", tags=["verificaciones"])
settings = get_settings()


def _session_id() -> str:
    return f"{settings.SESSION_PREFIX}-{int(time.time())}-{os.getpid()}"


def _log(
    db: Session,
    entidad_tipo: str,
    entidad_id: UUID | None,
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
# POST /proyectos/{proyecto_id}/verificar
# ---------------------------------------------------------------------------

@router.post(
    "/proyectos/{proyecto_id}/verificar",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
def ejecutar_verificaciones(
    proyecto_id: UUID, db: Session = Depends(get_db)
):
    """
    Ejecuta todas las reglas de verificacion para un proyecto.
    Recorre todas las evidencias y aplica las reglas correspondientes.
    """
    proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not proyecto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado"
        )

    sid = _session_id()

    # Obtener todas las evidencias del proyecto
    evidencias = (
        db.query(Evidencia)
        .join(Documento)
        .filter(Documento.proyecto_id == proyecto_id)
        .all()
    )

    if not evidencias:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay evidencias para verificar. Extraiga evidencias primero.",
        )

    # Limpiar verificaciones anteriores
    verificaciones_previas = (
        db.query(Verificacion)
        .join(Evidencia)
        .join(Documento)
        .filter(Documento.proyecto_id == proyecto_id)
        .all()
    )
    for v in verificaciones_previas:
        db.delete(v)
    db.commit()

    # Ejecutar reglas de verificacion
    resultados = _ejecutar_reglas(evidencias, db, sid)

    # Actualizar estado del proyecto
    proyecto.estado = "EVALUADO"
    db.commit()

    # Actualizar o crear dictamen
    dictamen = db.query(Dictamen).filter(Dictamen.proyecto_id == proyecto_id).first()
    total_ok = sum(1 for r in resultados if r["resultado"] == "CUMPLE")
    total_fail = sum(1 for r in resultados if r["resultado"] == "NO_CUMPLE")

    if not dictamen:
        dictamen = Dictamen(
            proyecto_id=proyecto_id,
            estado="EN_PROCESO",
            total_verificaciones=len(resultados),
            total_cumplen=total_ok,
            total_no_cumplen=total_fail,
            score=round(total_ok / len(resultados) * 100, 2) if resultados else 0.0,
            session_id=sid,
        )
        db.add(dictamen)
    else:
        dictamen.total_verificaciones = len(resultados)
        dictamen.total_cumplen = total_ok
        dictamen.total_no_cumplen = total_fail
        dictamen.score = round(total_ok / len(resultados) * 100, 2) if resultados else 0.0
        dictamen.session_id = sid

    db.commit()

    _log(
        db,
        "Proyecto",
        proyecto_id,
        "VERIFICAR",
        {
            "total_verificaciones": len(resultados),
            "cumplen": total_ok,
            "no_cumplen": total_fail,
            "score": dictamen.score,
            "session_id": sid,
        },
        sid,
    )
    db.commit()

    return {
        "session_id": sid,
        "total_verificaciones": len(resultados),
        "total_cumplen": total_ok,
        "total_no_cumplen": total_fail,
        "score": dictamen.score,
        "detalle": resultados,
    }


def _ejecutar_reglas(
    evidencias: list[Evidencia], db: Session, sid: str
) -> list[dict]:
    """
    Ejecuta las reglas de verificacion sobre las evidencias.
    Carga reglas desde YAML y las aplica.
    """
    resultados: list[dict] = []

    # Reglas stub - en produccion se cargan desde YAML
    reglas = [
        {
            "codigo": "REGLA_001",
            "campo": "area_construccion",
            "condicion": "valor_numerico > 0",
            "mensaje_ok": "Area de construccion valida",
            "mensaje_fail": "Area de construccion debe ser mayor a 0",
        },
        {
            "codigo": "REGLA_002",
            "campo": "altura_edificio",
            "condicion": "valor_numerico > 0",
            "mensaje_ok": "Altura de edificio valida",
            "mensaje_fail": "Altura de edificio debe ser mayor a 0",
        },
        {
            "codigo": "REGLA_003",
            "campo": "resistencia_hormigon",
            "condicion": "valor_numerico >= 20",
            "mensaje_ok": "Resistencia del hormigon cumple norma",
            "mensaje_fail": "Resistencia del hormigon debe ser >= 20 MPa",
        },
        {
            "codigo": "REGLA_004",
            "campo": "numero_pisos",
            "condicion": "valor_numerico > 0",
            "mensaje_ok": "Numero de pisos valido",
            "mensaje_fail": "Numero de pisos debe ser mayor a 0",
        },
        {
            "codigo": "REGLA_005",
            "campo": "sistema_estructural",
            "condicion": "valor_no_vacio",
            "mensaje_ok": "Sistema estructural especificado",
            "mensaje_fail": "Sistema estructural no puede estar vacio",
        },
    ]

    reglas_por_campo = {r["campo"]: r for r in reglas}

    for ev in evidencias:
        regla = reglas_por_campo.get(ev.campo)
        if not regla:
            continue

        resultado, mensaje = _evaluar_regla(ev, regla)

        ver = Verificacion(
            evidencia_id=ev.id,
            regla_codigo=regla["codigo"],
            resultado=resultado,
            mensaje=mensaje,
            payload_json=json.dumps(
                {
                    "valor_evidencia": ev.valor,
                    "unidad": ev.unidad,
                    "condicion": regla["condicion"],
                }
            ),
            session_id=sid,
        )
        db.add(ver)
        resultados.append(
            {
                "regla": regla["codigo"],
                "campo": ev.campo,
                "valor": ev.valor,
                "resultado": resultado,
                "mensaje": mensaje,
            }
        )

    db.commit()
    return resultados


def _evaluar_regla(ev: Evidencia, regla: dict) -> tuple[str, str]:
    """Evalua una regla contra una evidencia."""
    try:
        if ev.valor is None or ev.valor.strip() == "":
            return "NO_CUMPLE", regla["mensaje_fail"]

        if regla["condicion"].startswith("valor_numerico"):
            val = float(ev.valor)
            cond = regla["condicion"].replace("valor_numerico", str(val))
            if eval(cond):
                return "CUMPLE", regla["mensaje_ok"]
            return "NO_CUMPLE", regla["mensaje_fail"]

        if regla["condicion"] == "valor_no_vacio":
            if ev.valor and ev.valor.strip():
                return "CUMPLE", regla["mensaje_ok"]
            return "NO_CUMPLE", regla["mensaje_fail"]

        return "NO_APLICA", "Condicion no reconocida"
    except (ValueError, TypeError):
        return "NO_CUMPLE", f"Valor no numerico: {ev.valor}"


# ---------------------------------------------------------------------------
# GET /proyectos/{proyecto_id}/verificaciones
# ---------------------------------------------------------------------------

@router.get("/proyectos/{proyecto_id}/verificaciones", response_model=list[VerificacionOut])
def listar_verificaciones_proyecto(
    proyecto_id: UUID, db: Session = Depends(get_db)
):
    proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not proyecto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado"
        )

    verificaciones = (
        db.query(Verificacion)
        .join(Evidencia)
        .join(Documento)
        .filter(Documento.proyecto_id == proyecto_id)
        .order_by(Verificacion.ejecutada_en.desc())
        .all()
    )
    return verificaciones


# ---------------------------------------------------------------------------
# GET /verificaciones/{id}
# ---------------------------------------------------------------------------

@router.get("/verificaciones/{verificacion_id}", response_model=VerificacionOut)
def ver_verificacion(verificacion_id: UUID, db: Session = Depends(get_db)):
    ver = db.query(Verificacion).filter(Verificacion.id == verificacion_id).first()
    if not ver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verificacion no encontrada",
        )
    return ver
