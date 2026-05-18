"""
Router: Dictamenes
Consulta, generacion, edicion y cambio de estado de dictamenes.
"""

import json
import os
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Dictamen, Evidencia, LogAuditoria, Proyecto, Verificacion
from app.schemas import DictamenEstadoPatch, DictamenOut, DictamenUpdate

router = APIRouter(prefix="/api/v1", tags=["dictamenes"])
settings = get_settings()

# Templates para renderizar HAB HTML
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))


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
# GET /proyectos/{proyecto_id}/dictamen
# ---------------------------------------------------------------------------

@router.get("/proyectos/{proyecto_id}/dictamen", response_model=DictamenOut)
def ver_dictamen(proyecto_id: UUID, db: Session = Depends(get_db)):
    proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not proyecto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado"
        )

    dictamen = db.query(Dictamen).filter(Dictamen.proyecto_id == proyecto_id).first()
    if not dictamen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El proyecto no tiene dictamen generado aun",
        )
    return dictamen


# ---------------------------------------------------------------------------
# GET /proyectos/{proyecto_id}/dictamen/hab (HTML)
# ---------------------------------------------------------------------------

@router.get("/proyectos/{proyecto_id}/dictamen/hab", response_class=HTMLResponse)
def ver_dictamen_html(request: Request, proyecto_id: UUID, db: Session = Depends(get_db)):
    proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not proyecto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado"
        )

    dictamen = db.query(Dictamen).filter(Dictamen.proyecto_id == proyecto_id).first()
    if not dictamen or not dictamen.hab_html:
        # Template basico si no hay HAB generado
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><title>HAB - {proyecto.nombre}</title></head>
        <body>
            <h1>Hoja de Analisis de Build (HAB)</h1>
            <p><strong>Proyecto:</strong> {proyecto.nombre} ({proyecto.codigo})</p>
            <p><strong>Estado:</strong> {dictamen.estado if dictamen else 'Sin dictamen'}</p>
            <hr/>
            <p>El dictamen aun no tiene contenido HTML generado.</p>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)

    return HTMLResponse(content=dictamen.hab_html)


# ---------------------------------------------------------------------------
# POST /proyectos/{proyecto_id}/dictamen
# ---------------------------------------------------------------------------

@router.post(
    "/proyectos/{proyecto_id}/dictamen",
    response_model=DictamenOut,
    status_code=status.HTTP_201_CREATED,
)
def generar_dictamen(proyecto_id: UUID, db: Session = Depends(get_db)):
    proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not proyecto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado"
        )

    # Obtener verificaciones del proyecto
    verificaciones = (
        db.query(Verificacion)
        .join(Evidencia)
        .join(Proyecto, Evidencia.documento.has(proyecto_id=proyecto_id))
        .all()
    )

    # Contar resultados
    total = len(verificaciones)
    total_ok = sum(1 for v in verificaciones if v.resultado == "CUMPLE")
    total_fail = sum(1 for v in verificaciones if v.resultado == "NO_CUMPLE")
    score = round(total_ok / total * 100, 2) if total > 0 else 0.0

    # Generar texto del dictamen
    dictamen_texto = _generar_texto_dictamen(proyecto, verificaciones, score)

    # Generar HTML del HAB
    hab_html = _generar_hab_html(proyecto, verificaciones, score)

    # Determinar estado inicial
    estado = "CON_OBSERVACIONES" if total_fail > 0 else "EN_PROCESO"

    sid = _session_id()

    # Actualizar o crear dictamen
    dictamen = db.query(Dictamen).filter(Dictamen.proyecto_id == proyecto_id).first()
    if dictamen:
        dictamen.estado = estado
        dictamen.total_verificaciones = total
        dictamen.total_cumplen = total_ok
        dictamen.total_no_cumplen = total_fail
        dictamen.score = score
        dictamen.dictamen_texto = dictamen_texto
        dictamen.hab_html = hab_html
        dictamen.session_id = sid
        dictamen.editable = True
    else:
        dictamen = Dictamen(
            proyecto_id=proyecto_id,
            estado=estado,
            total_verificaciones=total,
            total_cumplen=total_ok,
            total_no_cumplen=total_fail,
            score=score,
            dictamen_texto=dictamen_texto,
            hab_html=hab_html,
            justificacion=_generar_justificacion(verificaciones),
            editable=True,
            session_id=sid,
        )
        db.add(dictamen)

    db.commit()
    db.refresh(dictamen)

    _log(
        db,
        "Dictamen",
        dictamen.id,
        "GENERAR",
        {
            "proyecto_id": str(proyecto_id),
            "total_verificaciones": total,
            "score": score,
            "estado": estado,
            "session_id": sid,
        },
        sid,
    )
    db.commit()
    return dictamen


def _generar_texto_dictamen(
    proyecto: Proyecto, verificaciones: list[Verificacion], score: float
) -> str:
    """Genera el texto del dictamen basado en las verificaciones."""
    lineas = [
        f"DICTAMEN DE REVISION TECNICA - PROYECTO {proyecto.codigo}",
        f"Nombre: {proyecto.nombre}",
        f"Tipo: {proyecto.tipo_proyecto}",
        "",
        f"SCORE GLOBAL: {score}%",
        f"Total verificaciones: {len(verificaciones)}",
        "",
        "RESULTADOS POR REGLA:",
    ]

    for v in verificaciones:
        icono = "✓" if v.resultado == "CUMPLE" else "✗" if v.resultado == "NO_CUMPLE" else "?"
        lineas.append(f"  [{icono}] {v.regla_codigo}: {v.mensaje}")

    lineas.append("")
    lineas.append("CONCLUSION:")
    if score >= 90:
        lineas.append("El proyecto cumple satisfactoriamente con los requisitos tecnicos evaluados.")
    elif score >= 70:
        lineas.append("El proyecto presenta observaciones menores que deben ser corregidas.")
    else:
        lineas.append("El proyecto presenta deficiencias tecnicas significativas.")

    return "\n".join(lineas)


def _generar_hab_html(
    proyecto: Proyecto, verificaciones: list[Verificacion], score: float
) -> str:
    """Genera el HTML de la Hoja de Analisis de Build."""
    filas = ""
    for v in verificaciones:
        color = "#28a745" if v.resultado == "CUMPLE" else "#dc3545" if v.resultado == "NO_CUMPLE" else "#6c757d"
        filas += f"""
        <tr>
            <td>{v.regla_codigo}</td>
            <td>{v.evidencia.campo if v.evidencia else '-'}</td>
            <td>{v.evidencia.valor if v.evidencia else '-'}</td>
            <td style="color:{color};font-weight:bold;">{v.resultado}</td>
            <td>{v.mensaje or ''}</td>
        </tr>
        """

    color_score = "#28a745" if score >= 90 else "#ffc107" if score >= 70 else "#dc3545"

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>HAB - {proyecto.nombre}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        .score {{ font-size: 48px; color: {color_score}; font-weight: bold; }}
        table {{ width: 100%%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f4f4f4; }}
        .header {{ background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Hoja de Analisis de Build (HAB)</h1>
        <p><strong>Proyecto:</strong> {proyecto.nombre} ({proyecto.codigo})</p>
        <p><strong>Tipo:</strong> {proyecto.tipo_proyecto}</p>
        <div class="score">Score: {score}%%</div>
    </div>
    <table>
        <thead>
            <tr><th>Regla</th><th>Campo</th><th>Valor</th><th>Resultado</th><th>Mensaje</th></tr>
        </thead>
        <tbody>
            {filas}
        </tbody>
    </table>
</body>
</html>"""


def _generar_justificacion(verificaciones: list[Verificacion]) -> str:
    """Genera la justificacion del dictamen."""
    fallas = [v for v in verificaciones if v.resultado == "NO_CUMPLE"]
    if not fallas:
        return "Todas las verificaciones cumplen con los requisitos establecidos."

    lineas = ["Observaciones encontradas:"]
    for v in fallas:
        lineas.append(f"- {v.regla_codigo}: {v.mensaje}")
    return "\n".join(lineas)


# ---------------------------------------------------------------------------
# PUT /dictamenes/{id}
# ---------------------------------------------------------------------------

@router.put("/dictamenes/{dictamen_id}", response_model=DictamenOut)
def editar_dictamen(
    dictamen_id: UUID, payload: DictamenUpdate, db: Session = Depends(get_db)
):
    dictamen = db.query(Dictamen).filter(Dictamen.id == dictamen_id).first()
    if not dictamen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dictamen no encontrado"
        )

    if not dictamen.editable:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El dictamen no es editable en su estado actual",
        )

    datos = payload.model_dump(exclude_unset=True)
    for campo, valor in datos.items():
        setattr(dictamen, campo, valor)

    db.commit()
    db.refresh(dictamen)

    sid = _session_id()
    _log(db, "Dictamen", dictamen.id, "EDITAR", datos, sid)
    db.commit()
    return dictamen


# ---------------------------------------------------------------------------
# PATCH /dictamenes/{id}/estado
# ---------------------------------------------------------------------------

@router.patch("/dictamenes/{dictamen_id}/estado", response_model=DictamenOut)
def cambiar_estado_dictamen(
    dictamen_id: UUID, payload: DictamenEstadoPatch, db: Session = Depends(get_db)
):
    dictamen = db.query(Dictamen).filter(Dictamen.id == dictamen_id).first()
    if not dictamen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dictamen no encontrado"
        )

    estado_anterior = dictamen.estado
    dictamen.estado = payload.estado

    # Si se aprueba o rechaza, marcar como no editable
    if payload.estado in ("APROBADO", "RECHAZADO"):
        dictamen.editable = False

    db.commit()
    db.refresh(dictamen)

    sid = _session_id()
    _log(
        db,
        "Dictamen",
        dictamen.id,
        "CAMBIAR_ESTADO",
        {"anterior": estado_anterior, "nuevo": payload.estado},
        sid,
    )
    db.commit()
    return dictamen


# ---------------------------------------------------------------------------
# DELETE /dictamenes/{id}
# ---------------------------------------------------------------------------

@router.delete("/dictamenes/{dictamen_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_dictamen(dictamen_id: UUID, db: Session = Depends(get_db)):
    dictamen = db.query(Dictamen).filter(Dictamen.id == dictamen_id).first()
    if not dictamen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dictamen no encontrado"
        )

    sid = _session_id()
    _log(
        db,
        "Dictamen",
        dictamen.id,
        "ELIMINAR",
        {"proyecto_id": str(dictamen.proyecto_id)},
        sid,
    )

    db.delete(dictamen)
    db.commit()
    return None
