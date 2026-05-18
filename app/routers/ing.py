"""
Router: Modulo ING (Ingreso al Banco de Proyectos)

Endpoints para gestionar solicitudes ING, documentos, revisiones cruzadas,
generacion de email al Coordinador, y control de iteraciones (R6).

Flujo de ingreso:
  1. Fran crea Solicitud ING (nombre, comuna, tipo, fechas)
  2. TRAZA genera acronimo [T][YY][CCC][NN] y crea Proyecto automaticamente
  3. Los documentos se registran contra esa Solicitud ING
  4. Las revisiones cruzadas verifican coherencia
  5. Al aceptar, el Proyecto queda listo para R01
"""
import os
import time
from typing import Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Proyecto
from app.models_ing import SolicitudIng, DocumentoIng, RevisionCruzada
from app.services.ing_service import (
    SolicitudIngService,
    DocumentoIngService,
    RevisionCruzadaService,
    ValidacionNormativaService,
)
from app.services.carpetas_service import EstructuraCarpetasService
from app.data.comunas import (
    listar_comunas,
    listar_tipos_proyecto,
    generar_acronimo,
    get_zona_sismica,
)
from app.schemas_ing import (
    SolicitudIngCreate,
    SolicitudIngUpdate,
    SolicitudIngEstadoPatch,
    SolicitudIngRead,
    SolicitudIngDetalle,
    SolicitudIngResumen,
    SolicitudIngOut,
    DocumentoIngCreate,
    DocumentoIngEstadoPatch,
    DocumentoIngRead,
    DocumentoIngListado,
    DocumentoIngComparacion,
    RevisionCruzadaCreate,
    RevisionCruzadaEstadoPatch,
    RevisionCruzadaRead,
    RevisionCruzadaListado,
    EmailGeneradoRead,
    EmailEnviadoPatch,
    IngDashboard,
    IngHistorialIteracion,
    SolicitudIngListadoResponse,
    SiguienteIteracionRead,
)

router = APIRouter(prefix="/api/v1/ing", tags=["ing"])

# Templates para rutas HTML
templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=templates_dir)

settings = get_settings()


def _session_id() -> str:
    return f"{settings.SESSION_PREFIX}-{int(time.time())}-{os.getpid()}"


# ═══════════════════════════════════════════════════════════════
# SOLICITUDES ING
# ═══════════════════════════════════════════════════════════════

@router.post("/solicitudes", response_model=SolicitudIngOut, status_code=status.HTTP_201_CREATED)
def crear_solicitud(payload: SolicitudIngCreate, db: Session = Depends(get_db)):
    """CA-ING-01: Crear Solicitud ING #1. Genera acronimo [T][YY][CCC][NN] y Proyecto automaticamente."""
    try:
        solicitud = SolicitudIngService.crear(db, payload, session_id=_session_id())
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    return SolicitudIngRead.from_orm_with_json(solicitud)


@router.get("/solicitudes", response_model=SolicitudIngListadoResponse)
def listar_solicitudes(
    estado: Optional[str] = Query(None),
    proyecto_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """1.8: Listar solicitudes ING con filtros opcionales.
    Cuando no hay solicitudes, devuelve estado vacio amigable con mensaje y CTA."""
    solicitudes = SolicitudIngService.listar(db, estado=estado, proyecto_id=proyecto_id, skip=skip, limit=limit)

    # 1.8: Estado vacio amigable
    if not solicitudes:
        return SolicitudIngListadoResponse(
            solicitudes=[],
            total=0,
            vacio=True,
            mensaje="No hay solicitudes ING registradas aun. Crea tu primera solicitud para comenzar.",
            cta_texto="Crear primera solicitud",
            cta_url="/ing/nueva",
        )

    resultado = []
    for sol in solicitudes:
        conteo = sol.conteo_documentos()
        resumen = SolicitudIngResumen(
            id=sol.id,
            proyecto_id=sol.proyecto_id,
            numero_iteracion=sol.numero_iteracion,
            estado=sol.estado,
            nombre_proyecto=sol.nombre_proyecto,
            empresa=sol.empresa,
            tipo_proyecto=sol.tipo_proyecto,
            comuna=sol.comuna,
            modulos_lista=sol.get_modulos(),
            fecha_solicitud=sol.fecha_solicitud,
            fecha_limite=sol.fecha_limite,
            total_documentos=conteo["total"],
            documentos_aceptados=conteo["aceptado"],
            documentos_observados=conteo["observado"],
            documentos_faltantes=conteo["faltante"],
            created_at=sol.created_at,
        )
        resultado.append(resumen)

    return SolicitudIngListadoResponse(
        solicitudes=resultado,
        total=len(resultado),
        vacio=False,
    )


@router.get("/solicitudes/{solicitud_id}", response_model=SolicitudIngDetalle)
def ver_solicitud(solicitud_id: str, db: Session = Depends(get_db)):
    """Ver solicitud ING con documentos y revisiones anidadas."""
    solicitud = SolicitudIngService.get(db, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud ING no encontrada")

    base = SolicitudIngRead.from_orm_with_json(solicitud)
    detalle_data = base.model_dump()
    detalle_data["documentos"] = [DocumentoIngRead.model_validate(d).model_dump() for d in solicitud.documentos]
    detalle_data["revisiones"] = [RevisionCruzadaRead.model_validate(r).model_dump() for r in solicitud.revisiones]
    detalle_data["conteo_documentos"] = solicitud.conteo_documentos()
    detalle_data["progreso_revisiones"] = solicitud.progreso_revisiones()
    detalle_data["puede_pasar_a_r01"] = solicitud.puede_pasar_a_r01()
    return detalle_data


@router.put("/solicitudes/{solicitud_id}", response_model=SolicitudIngOut)
def actualizar_solicitud(solicitud_id: str, payload: SolicitudIngUpdate, db: Session = Depends(get_db)):
    """Actualizar datos de una solicitud ING."""
    solicitud = SolicitudIngService.actualizar(db, solicitud_id, payload, session_id=_session_id())
    if not solicitud:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud ING no encontrada")
    return SolicitudIngRead.from_orm_with_json(solicitud)


@router.patch("/solicitudes/{solicitud_id}/estado", response_model=SolicitudIngOut)
def cambiar_estado_solicitud(solicitud_id: str, payload: SolicitudIngEstadoPatch, db: Session = Depends(get_db)):
    """Cambiar estado de la solicitud ING (recibida/en_revision/aceptada/observada)."""
    try:
        solicitud = SolicitudIngService.cambiar_estado(db, solicitud_id, payload.estado, session_id=_session_id())
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    if not solicitud:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud ING no encontrada")
    return SolicitudIngRead.from_orm_with_json(solicitud)


@router.post("/solicitudes/{solicitud_id}/siguiente-iteracion", response_model=SolicitudIngOut, status_code=status.HTTP_201_CREATED)
def crear_siguiente_iteracion(solicitud_id: str, db: Session = Depends(get_db)):
    """CA-ING-13: Crear ING #(N+1) aplicando R6 (herencia de aceptados como no_aplica)."""
    try:
        ing_nueva = SolicitudIngService.crear_siguiente_iteracion(db, solicitud_id, session_id=_session_id())
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    return SolicitudIngRead.from_orm_with_json(ing_nueva)


# ═══════════════════════════════════════════════════════════════
# DOCUMENTOS ING
# ═══════════════════════════════════════════════════════════════

@router.post("/solicitudes/{solicitud_id}/documentos", response_model=DocumentoIngRead, status_code=status.HTTP_201_CREATED)
def registrar_documento(solicitud_id: str, payload: DocumentoIngCreate, db: Session = Depends(get_db)):
    """CA-ING-03/04: Registrar documento y calcular hash SHA256."""
    # Verificar que la solicitud exista
    solicitud = SolicitudIngService.get(db, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud ING no encontrada")

    # R12: No modificar si esta aceptada
    if solicitud.estado == "aceptada":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No se pueden agregar documentos a una solicitud ya aceptada (R12)",
        )

    doc = DocumentoIngService.crear(db, solicitud_id, payload, calcular_hash=True)
    return doc


@router.get("/solicitudes/{solicitud_id}/documentos", response_model=DocumentoIngListado)
def listar_documentos(solicitud_id: str, db: Session = Depends(get_db)):
    """Listar documentos agrupados por modulo."""
    solicitud = SolicitudIngService.get(db, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud ING no encontrada")

    listado = DocumentoIngListado()
    for doc in solicitud.documentos:
        getattr(listado, doc.modulo, listado.URB).append(DocumentoIngRead.model_validate(doc))
    return listado


@router.patch("/documentos/{doc_id}/estado")
def cambiar_estado_documento(doc_id: str, payload: DocumentoIngEstadoPatch, db: Session = Depends(get_db)):
    """CA-ING-06/07: Cambiar estado de documento con observacion obligatoria si es 'observado'.
    Transiciona automaticamente el estado de la solicitud (R4)."""
    try:
        doc = DocumentoIngService.cambiar_estado(db, doc_id, payload, session_id=_session_id())
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    # Obtener la solicitud actualizada para devolver el nuevo estado
    solicitud = SolicitudIngService.get(db, doc.solicitud_ing_id)
    return {
        "documento": DocumentoIngRead.model_validate(doc).model_dump(),
        "solicitud_estado": solicitud.estado if solicitud else None,
        "solicitud_id": doc.solicitud_ing_id,
    }


@router.post("/documentos/{doc_id}/hash")
def recalcular_hash_documento(doc_id: str, db: Session = Depends(get_db)):
    """(Re)calcular hash SHA256 para deteccion de copias."""
    try:
        hash_val = DocumentoIngService.recalcular_hash(db, doc_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return {"hash_sha256": hash_val}


@router.get("/documentos/{doc_id}/comparar/{doc2_id}")
def comparar_documentos(doc_id: str, doc2_id: str, db: Session = Depends(get_db)):
    """Comparar dos documentos (deteccion de copias por hash)."""
    try:
        resultado = DocumentoIngService.comparar_documentos(db, doc_id, doc2_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return resultado


# ═══════════════════════════════════════════════════════════════
# REVISIONES CRUZADAS
# ═══════════════════════════════════════════════════════════════

@router.post("/solicitudes/{solicitud_id}/revisiones", response_model=list, status_code=status.HTTP_201_CREATED)
def crear_revisiones_default(solicitud_id: str, db: Session = Depends(get_db)):
    """CA-ING-05: Crear/Pre-poblar el checklist de 7 revisiones cruzadas."""
    solicitud = SolicitudIngService.get(db, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud ING no encontrada")

    revisiones = RevisionCruzadaService.crear_checklist_default(db, solicitud_id, session_id=_session_id())
    return [RevisionCruzadaRead.model_validate(r) for r in revisiones]


@router.get("/solicitudes/{solicitud_id}/revisiones", response_model=RevisionCruzadaListado)
def listar_revisiones(solicitud_id: str, db: Session = Depends(get_db)):
    """Listar revisiones cruzadas agrupadas por tipo."""
    solicitud = SolicitudIngService.get(db, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud ING no encontrada")

    listado = RevisionCruzadaListado()
    for rev in solicitud.revisiones:
        getattr(listado, rev.tipo_revision, []).append(RevisionCruzadaRead.model_validate(rev))
    return listado


@router.patch("/revisiones/{rev_id}/estado")
def marcar_revision(rev_id: str, payload: RevisionCruzadaEstadoPatch, db: Session = Depends(get_db)):
    """CA-ING-06: Fran marca resultado de una revision cruzada.
    Transiciona automaticamente el estado de la solicitud (R4)."""
    revision = RevisionCruzadaService.marcar_estado(db, rev_id, payload, session_id=_session_id())

    # Obtener la solicitud actualizada para devolver el nuevo estado
    solicitud = SolicitudIngService.get(db, revision.solicitud_ing_id)
    return {
        "revision": RevisionCruzadaRead.model_validate(revision).model_dump(),
        "solicitud_estado": solicitud.estado if solicitud else None,
        "solicitud_id": revision.solicitud_ing_id,
    }


@router.post("/solicitudes/{solicitud_id}/reiniciar-revisiones")
def reiniciar_revisiones(solicitud_id: str, db: Session = Depends(get_db)):
    """Reiniciar TODAS las revisiones cruzadas a 'pendiente', limpiando observaciones y fran_marco.
    Transiciona automaticamente el estado de la solicitud (R4)."""
    solicitud = SolicitudIngService.get(db, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud ING no encontrada")
    count = RevisionCruzadaService.reiniciar_todas(db, solicitud_id, session_id=_session_id())

    # Recargar la solicitud para obtener el estado actualizado
    db.refresh(solicitud)
    return {
        "reiniciadas": count,
        "mensaje": f"{count} revisiones reiniciadas a 'pendiente'",
        "solicitud_estado": solicitud.estado,
        "solicitud_id": solicitud_id,
    }


@router.get("/solicitudes/{solicitud_id}/progreso")
def ver_progreso(solicitud_id: str, db: Session = Depends(get_db)):
    """Ver progreso del checklist (X/7 revisadas, Y/7 aceptadas)."""
    solicitud = SolicitudIngService.get(db, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud ING no encontrada")
    return solicitud.progreso_revisiones()


@router.get("/solicitudes/{solicitud_id}/carpetas")
def ver_estructura_carpetas(solicitud_id: str, db: Session = Depends(get_db)):
    """R7: Ver estructura de carpetas /PDP/ING/{acronimo}/ del proyecto."""
    solicitud = SolicitudIngService.get(db, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud ING no encontrada")

    if not solicitud.acronimo_proyecto:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Solicitud sin acronimo")

    return {
        "acronimo": solicitud.acronimo_proyecto,
        "ruta_base": solicitud.ruta_carpeta,
        "existe": EstructuraCarpetasService.existe_estructura(solicitud.acronimo_proyecto),
        "subcarpetas": EstructuraCarpetasService.listar_subcarpetas(solicitud.acronimo_proyecto),
    }


# ═══════════════════════════════════════════════════════════════
# EMAIL
# ═══════════════════════════════════════════════════════════════

@router.post("/solicitudes/{solicitud_id}/generar-email")
def generar_email(solicitud_id: str, db: Session = Depends(get_db)):
    """CA-ING-08: Generar borrador de email con aceptados/observados/faltantes."""
    try:
        resultado = SolicitudIngService.generar_email(db, solicitud_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return resultado


@router.get("/solicitudes/{solicitud_id}/email")
def ver_email_generado(solicitud_id: str, db: Session = Depends(get_db)):
    """Ver ultimo email generado."""
    solicitud = SolicitudIngService.get(db, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud ING no encontrada")

    if not solicitud.email_generado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No hay email generado para esta solicitud")

    return {
        "email_generado": solicitud.email_generado,
        "fecha_envio": solicitud.fecha_envio_email,
    }


@router.post("/solicitudes/{solicitud_id}/enviar-email")
def registrar_envio_email(solicitud_id: str, db: Session = Depends(get_db)):
    """CA-ING-09: Registrar que el email fue enviado."""
    try:
        solicitud = SolicitudIngService.registrar_envio_email(db, solicitud_id, session_id=_session_id())
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return {"ok": True, "fecha_envio": solicitud.fecha_envio_email}


# ═══════════════════════════════════════════════════════════════
# DASHBOARD / ESTADISTICAS
# ═══════════════════════════════════════════════════════════════

@router.get("/dashboard")
def dashboard_ing(db: Session = Depends(get_db)):
    """CA-ING-14: Panel de Fran — conteos por estado, vencimientos proximos, iteraciones del mes."""
    return SolicitudIngService.dashboard(db)


@router.get("/proyectos/{proyecto_id}/historial")
def historial_iteraciones(proyecto_id: str, db: Session = Depends(get_db)):
    """Ver todas las iteraciones ING de un proyecto."""
    from sqlalchemy import select, asc
    query = select(SolicitudIng).where(SolicitudIng.proyecto_id == proyecto_id).order_by(asc(SolicitudIng.numero_iteracion))
    solicitudes = list(db.execute(query).scalars().all())

    resultado = []
    for sol in solicitudes:
        conteo = sol.conteo_documentos()
        resultado.append({
            "id": sol.id,
            "numero_iteracion": sol.numero_iteracion,
            "estado": sol.estado,
            "total_documentos": conteo["total"],
            "aceptados": conteo["aceptado"],
            "observados": conteo["observado"],
            "faltantes": conteo["faltante"],
            "created_at": sol.created_at,
        })
    return resultado


# ═══════════════════════════════════════════════════════════════
# VALIDACION NORMATIVA
# ═══════════════════════════════════════════════════════════════

@router.post("/validar-calicatas")
def validar_calicatas(superficie_terreno: float, cantidad_calicatas: int):
    """CA-ING-16: Validar calicatas minimas segun tabla normativa."""
    return ValidacionNormativaService.validar_calicatas(superficie_terreno, cantidad_calicatas)


# ═══════════════════════════════════════════════════════════════
# RECALCULAR ESTADO (helpers)
# ═══════════════════════════════════════════════════════════════

@router.post("/solicitudes/{solicitud_id}/recalcular-estado")
def recalcular_estado_solicitud(solicitud_id: str, db: Session = Depends(get_db)):
    """Recalcular estado de la solicitud basado en documentos (R4)."""
    solicitud = SolicitudIngService.get(db, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud ING no encontrada")

    nuevo_estado = solicitud.recalcular_estado()
    if nuevo_estado != solicitud.estado:
        solicitud.estado = nuevo_estado
        db.commit()
        db.refresh(solicitud)

    return {
        "estado_anterior": solicitud.estado,
        "estado_actual": nuevo_estado,
        "conteo_documentos": solicitud.conteo_documentos(),
    }


# ═══════════════════════════════════════════════════════════════
# CATALOGOS (comunas, tipos de proyecto)
# ═══════════════════════════════════════════════════════════════

@router.get("/catalogos/comunas")
def listar_comunas_ohiggins():
    """Lista las 33 comunas de la Region de O'Higgins con sus codigos y zona sismica."""
    return listar_comunas()


@router.get("/catalogos/tipos-proyecto")
def listar_tipos():
    """Lista los tipos de proyecto disponibles para el acronimo."""
    return listar_tipos_proyecto()


@router.get("/catalogos/zona-sismica/{comuna}")
def zona_sismica_por_comuna(comuna: str):
    """Obtiene la zona sismica INMUTABLE para una comuna. No se puede modificar."""
    zona = get_zona_sismica(comuna)
    if zona == 0:
        raise HTTPException(status_code=404, detail=f"Comuna '{comuna}' no encontrada")
    return {"comuna": comuna, "zona_sismica": zona, "inmutable": True}


@router.post("/preview-acronimo")
def preview_acronimo(
    tipo_proyecto: str,
    comuna: str,
    nombre_proyecto: str,
    anio: Optional[int] = None,
):
    """Previsualiza el acronimo que se generaria sin crear nada."""
    return {"acronimo": generar_acronimo(tipo_proyecto, comuna, nombre_proyecto, anio)}


# ═══════════════════════════════════════════════════════════════
# RUTAS HTML (paginas)
# ═══════════════════════════════════════════════════════════════

@router.get("/pages/ing", include_in_schema=False)
def page_ing_lista(request: Request, estado: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Pagina HTML: Lista de solicitudes ING."""
    return templates.TemplateResponse(request, "ing/lista.html", {
        "estado_activo": estado,
    })


@router.get("/pages/ing/nueva", include_in_schema=False)
def page_ing_nueva(request: Request, db: Session = Depends(get_db)):
    """Pagina HTML: Formulario nueva solicitud ING."""
    from sqlalchemy import select
    proyectos = list(db.execute(select(Proyecto).where(Proyecto.estado == "ACTIVO").order_by(Proyecto.created_at.desc())).scalars().all())
    return templates.TemplateResponse(request, "ing/nueva.html", {
        "proyectos": proyectos,
    })


@router.get("/pages/ing/{solicitud_id}", include_in_schema=False)
def page_ing_detalle(solicitud_id: str, request: Request, db: Session = Depends(get_db)):
    """Pagina HTML: Detalle de solicitud ING con documentos y revisiones."""
    solicitud = SolicitudIngService.get(db, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud ING no encontrada")

    # Agrupar documentos por modulo
    documentos_por_modulo = {"MDS": [], "EST": [], "HAB": [], "URB": []}
    for doc in solicitud.documentos:
        if doc.modulo in documentos_por_modulo:
            documentos_por_modulo[doc.modulo].append(doc)
        else:
            documentos_por_modulo["URB"].append(doc)

    # Agrupar revisiones por tipo
    revisiones_por_tipo = {"MDS_TOPO": [], "EST_ARQ": [], "HAB_PRES": []}
    for rev in solicitud.revisiones:
        if rev.tipo_revision in revisiones_por_tipo:
            revisiones_por_tipo[rev.tipo_revision].append(rev)

    return templates.TemplateResponse(request, "ing/detalle.html", {
        "solicitud": solicitud,
        "modulos": solicitud.get_modulos(),
        "conteo": solicitud.conteo_documentos(),
        "progreso": solicitud.progreso_revisiones(),
        "puede_pasar_a_r01": solicitud.puede_pasar_a_r01(),
        "solicitud_anterior_id": solicitud.solicitud_anterior_id,
        "documentos_por_modulo": documentos_por_modulo,
        "revisiones_por_tipo": revisiones_por_tipo,
        "revisiones": solicitud.revisiones,
    })