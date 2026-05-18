"""FastAPI app factory para TRAZA."""
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, select, func, nullsfirst

from app.config import settings
from app.database import init_db, get_db
from app.models import Proyecto, LogAuditoria
from app.models_ing import SolicitudIng
from app.services.ing_service import SolicitudIngService
from app.routers import (
    proyectos,
    documentos,
    evidencias,
    verificaciones,
    dictamenes,
    auditoria,
    extracciones,
    ing,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Evento startup: inicializa la base de datos."""
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="TRAZA",
        description="Sistema de trazabilidad normativa 100% offline",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Routers
    app.include_router(proyectos.router)
    app.include_router(documentos.router)
    app.include_router(evidencias.router)
    app.include_router(verificaciones.router)
    app.include_router(dictamenes.router)
    app.include_router(auditoria.router)
    app.include_router(extracciones.router)
    app.include_router(ing.router)

    # Static files
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.isdir(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # Jinja2 templates
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    templates = Jinja2Templates(directory=templates_dir)

    @app.get("/", response_class=HTMLResponse)
    async def root(request: Request, db: Session = Depends(get_db)):
        """Dashboard principal con KPIs."""
        # KPIs — usar estilo SQLAlchemy 2.0 select() para compatibilidad con Python 3.14
        total_proyectos = db.execute(select(func.count()).select_from(Proyecto)).scalar() or 0
        en_evaluacion = db.execute(select(func.count()).select_from(Proyecto).where(Proyecto.estado == "EN_EVALUACION")).scalar() or 0
        evaluados = db.execute(select(func.count()).select_from(Proyecto).where(Proyecto.estado == "EVALUADO")).scalar() or 0

        kpis = {
            "total_proyectos": total_proyectos,
            "en_evaluacion": en_evaluacion,
            "evaluados": evaluados,
            "score_promedio": 0,
        }

        # Proyectos recientes
        proyectos_recientes = db.execute(
            select(Proyecto).order_by(Proyecto.created_at.desc()).limit(10)
        ).scalars().all()

        # Actividad reciente
        actividad_reciente = db.execute(
            select(LogAuditoria).order_by(LogAuditoria.created_at.desc()).limit(20)
        ).scalars().all()

        return templates.TemplateResponse(request, "dashboard/index.html", {
            "title": "Dashboard",
            "kpis": kpis,
            "proyectos_recientes": list(proyectos_recientes),
            "actividad_reciente": list(actividad_reciente),
        })

    @app.get("/health")
    async def health():
        return {"status": "ok", "debug": settings.DEBUG, "session_prefix": settings.SESSION_PREFIX}

    # ═══════════════════════════════════════════════════════════
    # RUTAS HTML: Modulo ING
    # ═══════════════════════════════════════════════════════════

    @app.get("/ing", response_class=HTMLResponse)
    async def page_ing_lista(request: Request, estado: Optional[str] = None, db: Session = Depends(get_db)):
        """Pagina: Lista de solicitudes ING con datos renderizados desde el servidor."""
        # Imports ya disponibles globalmente: select, func, desc, nullsfirst

        # Dashboard stats
        q_estados = select(SolicitudIng.estado, func.count()).group_by(SolicitudIng.estado)
        estado_counts = {row[0]: row[1] for row in db.execute(q_estados)}

        # Vencimientos proximos (7 dias)
        hoy = datetime.now()
        todas = db.execute(
            select(SolicitudIng).where(SolicitudIng.estado.in_(["recibida", "en_revision"]))
        ).scalars().all()
        vencimientos = []
        for sol in todas:
            if sol.fecha_limite:
                try:
                    fecha_lim = datetime.strptime(sol.fecha_limite, "%Y-%m-%d")
                    dias = (fecha_lim - hoy).days
                    if 0 <= dias <= 7:
                        vencimientos.append({
                            "id": sol.id, "nombre_proyecto": sol.nombre_proyecto,
                            "fecha_limite": sol.fecha_limite, "dias_restantes": dias, "estado": sol.estado,
                        })
                except (ValueError, TypeError):
                    pass

        primer_dia = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        iter_mes = db.execute(select(func.count()).where(SolicitudIng.created_at >= primer_dia)).scalar() or 0

        dashboard = {
            "en_revision": estado_counts.get("en_revision", 0),
            "aceptadas": estado_counts.get("aceptada", 0),
            "observadas": estado_counts.get("observada", 0),
            "recibidas": estado_counts.get("recibida", 0),
            "vencimiento_proximo": vencimientos,
            "iteraciones_mes": iter_mes,
        }

        # Solicitudes — ordenadas por fecha limite ascendente (urgentes primero), luego por fecha de creacion
        # nullsfirst ya importado arriba
        query = select(SolicitudIng).order_by(
            nullsfirst(SolicitudIng.fecha_limite.asc()),  # Urgentes primero
            desc(SolicitudIng.created_at)                  # Luego mas recientes
        )
        if estado:
            query = query.where(SolicitudIng.estado == estado)
        all_sols = db.execute(query.limit(50)).scalars().all()

        solicitudes_list = []
        for sol in all_sols:
            conteo = sol.conteo_documentos()
            dias_restantes = None
            if sol.fecha_limite:
                try:
                    dias_restantes = (datetime.strptime(sol.fecha_limite, "%Y-%m-%d") - hoy).days
                except:
                    pass
            solicitudes_list.append({
                "id": sol.id, "acronimo_proyecto": sol.acronimo_proyecto,
                "nombre_proyecto": sol.nombre_proyecto, "empresa": sol.empresa,
                "comuna": sol.comuna, "estado": sol.estado,
                "numero_iteracion": sol.numero_iteracion,
                "fecha_limite": sol.fecha_limite, "dias_restantes": dias_restantes,
                "total_documentos": conteo["total"],
                "documentos_aceptados": conteo["aceptado"],
                "documentos_observados": conteo["observado"],
                "documentos_faltantes": conteo["faltante"],
            })

        return templates.TemplateResponse(request, "ing/lista.html", {
            "estado_activo": estado,
            "dashboard": dashboard,
            "solicitudes": solicitudes_list,
        })

    @app.get("/ing/flujo", response_class=HTMLResponse)
    async def page_ing_flujo(request: Request):
        """Pagina: Diagrama del flujo de ingreso de proyectos."""
        return templates.TemplateResponse("ing/flujo_ingreso.html", {"request": request, "title": "Flujo de Ingreso"})

    @app.get("/ing/nueva", response_class=HTMLResponse)
    async def page_ing_nueva(request: Request, db: Session = Depends(get_db)):
        """Pagina: Formulario nueva solicitud ING."""
        proyectos = list(db.execute(select(Proyecto).where(Proyecto.estado == "ACTIVO").order_by(Proyecto.created_at.desc())).scalars().all())
        return templates.TemplateResponse(request, "ing/nueva.html", {
            "proyectos": proyectos,
        })

    @app.get("/ing/{solicitud_id}", response_class=HTMLResponse)
    async def page_ing_detalle(solicitud_id: str, request: Request, db: Session = Depends(get_db)):
        """Pagina: Detalle de solicitud ING con documentos y revisiones."""
        solicitud = SolicitudIngService.get(db, solicitud_id)
        if not solicitud:
            return HTMLResponse(content="<h1>Solicitud ING no encontrada</h1>", status_code=404)

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

        # Dias restantes para fecha limite
        dias_restantes = None
        if solicitud.fecha_limite:
            try:
                dias_restantes = (datetime.strptime(solicitud.fecha_limite, "%Y-%m-%d") - datetime.now()).days
            except (ValueError, TypeError):
                pass

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
            "dias_restantes": dias_restantes,
        })

    return app


# Global app instance for direct import (tests, uvicorn, etc.)
app = create_app()
