"""Servicios de negocio para el Modulo ING.

Reglas implementadas:
  R4: ING aceptada = todos documentos aceptados/no_aplica
  R5: No se puede pasar a R01 sin ING aceptada
  R6: Si aceptado en N -> no_aplica en N+1 (herencia)
  R10: Observacion obligatoria si estado = 'observado'
  R11: No eliminar solicitud con documentos
  R12: Iteracion aceptada es inmutable
"""
import json
import hashlib
import os
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import select, desc, asc

from app.models_ing import SolicitudIng, DocumentoIng, RevisionCruzada, TablaCalicatasMinimas
from app.models import Proyecto, LogAuditoria
from app.schemas_ing import (
    SolicitudIngCreate,
    SolicitudIngUpdate,
    DocumentoIngCreate,
    DocumentoIngEstadoPatch,
    RevisionCruzadaCreate,
    RevisionCruzadaEstadoPatch,
)
from app.data.comunas import (
    generar_acronimo,
    get_comuna_codigo,
    get_zona_sismica,
    get_tipo_proyecto_letra,
    listar_comunas,
    listar_tipos_proyecto,
)
from app.services.carpetas_service import EstructuraCarpetasService


# ──────────────────────────────────────────────
# Templates de revisiones cruzadas (checklist)
# ──────────────────────────────────────────────

CHECKLIST_TEMPLATE = [
    {
        "tipo_revision": "MDS_TOPO",
        "numero_revision": "3.1.1",
        "descripcion": "Calicatas minimas segun superficie del terreno",
        "fuente_1": "superficie_terreno",
        "valor_1": None,
        "fuente_2": "cantidad_calicatas",
        "valor_2": None,
    },
    {
        "tipo_revision": "EST_ARQ",
        "numero_revision": "3.2.1",
        "descripcion": "Planos EST por tipologia estructural",
        "fuente_1": "tipologias_detectadas",
        "valor_1": None,
        "fuente_2": "planos_est_registrados",
        "valor_2": None,
    },
    {
        "tipo_revision": "EST_ARQ",
        "numero_revision": "3.2.2",
        "descripcion": "Memorias EST por tipologia estructural",
        "fuente_1": "tipologias_detectadas",
        "valor_1": None,
        "fuente_2": "memorias_est_registradas",
        "valor_2": None,
    },
    {
        "tipo_revision": "EST_ARQ",
        "numero_revision": "3.2.3",
        "descripcion": "Deteccion de copias en memorias EST",
        "fuente_1": "hash_memoria_t01",
        "valor_1": None,
        "fuente_2": "hash_memoria_t02",
        "valor_2": None,
    },
    {
        "tipo_revision": "HAB_PRES",
        "numero_revision": "3.3.1",
        "descripcion": "Obras con plano HAB",
        "fuente_1": "obras_presupuesto",
        "valor_1": None,
        "fuente_2": "planos_hab_registrados",
        "valor_2": None,
    },
    {
        "tipo_revision": "HAB_PRES",
        "numero_revision": "3.3.2",
        "descripcion": "Obras con memoria HAB",
        "fuente_1": "obras_presupuesto",
        "valor_1": None,
        "fuente_2": "memorias_hab_registradas",
        "valor_2": None,
    },
    {
        "tipo_revision": "HAB_PRES",
        "numero_revision": "3.3.3",
        "descripcion": "Memoria HAB describe todas las obras del presupuesto",
        "fuente_1": "memoria_hab_contenido",
        "valor_1": None,
        "fuente_2": "lista_obras_presupuesto",
        "valor_2": None,
    },
]


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _session_id(prefix: str = "local") -> str:
    import time
    import os as _os
    return f"{prefix}-{int(time.time())}-{_os.getpid()}"


def _log(db: Session, entidad_tipo: str, entidad_id: str, accion: str, detalle: dict, session_id: str):
    log = LogAuditoria(
        entidad_tipo=entidad_tipo,
        entidad_id=entidad_id,
        accion=accion,
        detalle_json=json.dumps(detalle, default=str),
        session_id=session_id,
    )
    db.add(log)


def calcular_hash_sha256(ruta_local: str) -> Optional[str]:
    """Calcula hash SHA256 de un archivo."""
    if not ruta_local or not os.path.isfile(ruta_local):
        return None
    h = hashlib.sha256()
    with open(ruta_local, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ──────────────────────────────────────────────
# SolicitudIngService
# ──────────────────────────────────────────────

class SolicitudIngService:

    @staticmethod
    def crear(db: Session, data: SolicitudIngCreate, session_id: Optional[str] = None) -> SolicitudIng:
        """
        Crea Solicitud ING #1, genera acronimo [T][YY][CCC][NN],
        crea el Proyecto automaticamente y vincula.

        La zona sismica se calcula AUTOMATICAMENTE desde la comuna
        (INMUTABLE — no se puede modificar manualmente).
        """
        sid = session_id or _session_id()
        anio_actual = datetime.now().year

        # Zona sismica: AUTOMATICA desde la comuna (ignora valor enviado)
        zona = get_zona_sismica(data.comuna)

        # Obtener codigo de comuna
        comuna_codigo = get_comuna_codigo(data.comuna)

        # Generar acronimo [T][YY][CCC][NN]
        acronimo = generar_acronimo(
            tipo_proyecto=data.tipo_proyecto,
            comuna=data.comuna,
            nombre_proyecto=data.nombre_proyecto,
            anio=anio_actual,
        )

        # Verificar que no exista un proyecto con ese acronimo
        existente = db.execute(
            select(Proyecto).where(Proyecto.codigo == acronimo)
        ).scalar_one_or_none()
        if existente:
            # Agregar sufijo numerico si ya existe
            acronimo = f"{acronimo}A"

        # Crear el Proyecto automaticamente
        proyecto = Proyecto(
            codigo=acronimo,
            nombre=data.nombre_proyecto,
            tipo_proyecto=data.tipo_proyecto,
            ref_comuna=data.comuna,
            ref_zona_sismica=zona if zona > 0 else None,
            estado="ACTIVO",
        )
        db.add(proyecto)
        db.flush()  # Para obtener el ID del proyecto

        # Crear la solicitud ING vinculada al proyecto
        # NOTA: superficie_terreno y cantidad_calicatas NO se ingresan aqui.
        #       Se registran mas tarde en las revisiones cruzadas.
        solicitud = SolicitudIng(
            proyecto_id=proyecto.id,
            acronimo_proyecto=acronimo,
            numero_iteracion=1,
            solicitud_anterior_id=None,
            estado="recibida",
            nombre_proyecto=data.nombre_proyecto,
            empresa=data.empresa,
            tipo_proyecto=data.tipo_proyecto,
            comuna=data.comuna,
            comuna_codigo=comuna_codigo,
            modulos=json.dumps(data.modulos),
            fecha_solicitud=data.fecha_solicitud,
            fecha_limite=data.fecha_limite,
            link_descarga=data.link_descarga,
            zona_sismica=zona if zona > 0 else None,
            tipologias=json.dumps(data.tipologias) if data.tipologias else None,
            session_id=sid,
        )
        db.add(solicitud)
        db.commit()
        db.refresh(solicitud)

        # R7: Crear estructura de carpetas /PDP/ING/{acronimo}/
        try:
            ruta_carpeta = EstructuraCarpetasService.crear_estructura(acronimo)
            solicitud.ruta_carpeta = ruta_carpeta
            db.commit()
            db.refresh(solicitud)
        except OSError as e:
            # Si falla la creacion de carpetas, no bloquear la creacion de la solicitud
            _log(db, "SolicitudIng", solicitud.id, "ERROR_CARPETAS", {
                "acronimo": acronimo,
                "error": str(e),
            }, sid)
            db.commit()

        _log(db, "SolicitudIng", solicitud.id, "CREAR", {
            "acronimo": acronimo,
            "numero_iteracion": 1,
            "nombre_proyecto": data.nombre_proyecto,
            "comuna": data.comuna,
            "tipo_proyecto": data.tipo_proyecto,
            "ruta_carpeta": solicitud.ruta_carpeta,
        }, sid)
        db.commit()
        return solicitud

    @staticmethod
    def get(db: Session, solicitud_id: str) -> Optional[SolicitudIng]:
        return db.get(SolicitudIng, solicitud_id)

    @staticmethod
    def listar(db: Session, estado: Optional[str] = None, proyecto_id: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[SolicitudIng]:
        query = select(SolicitudIng)
        if estado:
            query = query.where(SolicitudIng.estado == estado)
        if proyecto_id:
            query = query.where(SolicitudIng.proyecto_id == proyecto_id)
        # 1.6: Ordenar por fecha_limite ASC (mas urgentes primero), NULL al final
        query = query.order_by(SolicitudIng.fecha_limite.asc().nullslast(), desc(SolicitudIng.created_at)).offset(skip).limit(limit)
        return list(db.execute(query).scalars().all())

    @staticmethod
    def transicionar_estado_automatico(db: Session, solicitud_id: str, session_id: Optional[str] = None) -> Optional[str]:
        """
        Transiciona automaticamente el estado de la solicitud basado en
        el estado de sus documentos y revisiones cruzadas.

        Reglas de transicion (solo desde 'en_revision'):
          - Si TODOS los documentos son 'aceptado'/'no_aplica'
            Y TODAS las revisiones cruzadas son 'aceptado'
            → estado = 'aceptada'

          - Si ALGUN documento es 'observado'/'faltante'
            O ALGUNA revision es 'observado'/'faltante'
            → estado = 'observada'

          - Si hay documentos/revisiones 'pendientes'
            → no transicionar (queda 'en_revision')

        Retorna el nuevo estado, o None si no hubo transicion.
        """
        solicitud = db.get(SolicitudIng, solicitud_id)
        if not solicitud or solicitud.estado not in ("en_revision",):
            return None

        # Conteo de documentos
        docs = solicitud.documentos
        tiene_pendientes = any(d.estado == "pendiente" for d in docs)
        tiene_observados = any(d.estado in ("observado", "faltante") for d in docs)
        todos_docs_ok = all(d.estado in ("aceptado", "no_aplica") for d in docs) if docs else False

        # Conteo de revisiones cruzadas
        revs = solicitud.revisiones
        tiene_rev_pendientes = any(r.estado == "pendiente" for r in revs)
        tiene_rev_observadas = any(r.estado in ("observado", "faltante") for r in revs)
        todas_rev_ok = all(r.estado == "aceptado" for r in revs) if revs else False

        # Decision de transicion
        nuevo_estado = None

        if tiene_observados or tiene_rev_observadas:
            # Hay observaciones/faltantes → observada
            nuevo_estado = "observada"
        elif (todos_docs_ok and todas_rev_ok and len(docs) > 0 and len(revs) > 0):
            # Todo aceptado → aceptada
            nuevo_estado = "aceptada"
        elif (todos_docs_ok and len(revs) == 0 and len(docs) > 0):
            # Solo documentos (sin revisiones cruzadas) todos aceptados → aceptada
            nuevo_estado = "aceptada"
        # Si hay pendientes → no transicionar

        if nuevo_estado and nuevo_estado != solicitud.estado:
            estado_anterior = solicitud.estado
            solicitud.estado = nuevo_estado
            solicitud.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(solicitud)

            sid = session_id or _session_id()
            _log(db, "SolicitudIng", solicitud.id, "TRANSICION_AUTO", {
                "anterior": estado_anterior,
                "nuevo": nuevo_estado,
                "docs_total": len(docs),
                "docs_aceptados": sum(1 for d in docs if d.estado in ("aceptado", "no_aplica")),
                "docs_observados": sum(1 for d in docs if d.estado in ("observado", "faltante")),
                "revs_total": len(revs),
                "revs_aceptadas": sum(1 for r in revs if r.estado == "aceptado"),
                "revs_observadas": sum(1 for r in revs if r.estado in ("observado", "faltante")),
            }, sid)
            db.commit()

        return nuevo_estado

    @staticmethod
    def actualizar(db: Session, solicitud_id: str, data: SolicitudIngUpdate, session_id: Optional[str] = None) -> Optional[SolicitudIng]:
        solicitud = db.get(SolicitudIng, solicitud_id)
        if not solicitud:
            return None

        # R12: No modificar si esta aceptada (solo campos no criticos)
        campos_actualizables = ["nombre_proyecto", "empresa", "fecha_limite", "link_descarga",
                                 "comuna", "zona_sismica", "superficie_terreno", "cantidad_calicatas"]
        if solicitud.estado == "aceptada":
            campos_actualizables = ["fecha_limite", "link_descarga"]

        datos = data.model_dump(exclude_unset=True)
        for campo, valor in datos.items():
            if campo in campos_actualizables:
                if campo == "modulos" and isinstance(valor, list):
                    solicitud.set_modulos(valor)
                elif campo == "tipologias" and isinstance(valor, list):
                    solicitud.set_tipologias(valor)
                else:
                    setattr(solicitud, campo, valor)

        solicitud.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(solicitud)

        sid = session_id or _session_id()
        _log(db, "SolicitudIng", solicitud.id, "ACTUALIZAR", datos, sid)
        db.commit()
        return solicitud

    @staticmethod
    def cambiar_estado(db: Session, solicitud_id: str, nuevo_estado: str, session_id: Optional[str] = None) -> Optional[SolicitudIng]:
        solicitud = db.get(SolicitudIng, solicitud_id)
        if not solicitud:
            return None

        # R12: No cambiar estado si ya esta aceptada
        if solicitud.estado == "aceptada" and nuevo_estado != "aceptada":
            raise ValueError("No se puede cambiar el estado de una solicitud ya aceptada (R12)")

        estado_anterior = solicitud.estado
        solicitud.estado = nuevo_estado
        solicitud.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(solicitud)

        sid = session_id or _session_id()
        _log(db, "SolicitudIng", solicitud.id, "CAMBIAR_ESTADO", {
            "anterior": estado_anterior, "nuevo": nuevo_estado,
        }, sid)
        db.commit()
        return solicitud

    @staticmethod
    def crear_siguiente_iteracion(db: Session, solicitud_anterior_id: str, session_id: Optional[str] = None) -> SolicitudIng:
        """Crear ING #(N+1) aplicando R6 (herencia de aceptados como no_aplica)."""
        sid = session_id or _session_id()

        ing_anterior = db.get(SolicitudIng, solicitud_anterior_id)
        if not ing_anterior:
            raise ValueError(f"Solicitud anterior {solicitud_anterior_id} no encontrada")

        if ing_anterior.estado != "observada":
            raise ValueError(f"Solo se puede crear siguiente iteracion si estado='observada', actual={ing_anterior.estado}")

        # Crear ING nueva
        ing_nueva = SolicitudIng(
            proyecto_id=ing_anterior.proyecto_id,
            numero_iteracion=ing_anterior.numero_iteracion + 1,
            solicitud_anterior_id=ing_anterior.id,
            estado="recibida",
            nombre_proyecto=ing_anterior.nombre_proyecto,
            empresa=ing_anterior.empresa,
            modulos=ing_anterior.modulos,
            fecha_limite=ing_anterior.fecha_limite,
            link_descarga=ing_anterior.link_descarga,
            comuna=ing_anterior.comuna,
            zona_sismica=ing_anterior.zona_sismica,
            superficie_terreno=ing_anterior.superficie_terreno,
            cantidad_calicatas=ing_anterior.cantidad_calicatas,
            tipologias=ing_anterior.tipologias,
            session_id=sid,
        )
        db.add(ing_nueva)
        db.flush()  # Para obtener el ID

        # R6: Heredar documentos aceptados como 'no_aplica'
        documentos_heredados = 0
        documentos_pendientes = 0

        for doc_ant in ing_anterior.documentos:
            if doc_ant.estado == "aceptado":
                nuevo_estado = "no_aplica"
                iteracion_aceptada = doc_ant.iteracion_aceptada_en or ing_anterior.numero_iteracion
                documentos_heredados += 1
            elif doc_ant.estado in ("observado", "faltante"):
                nuevo_estado = "pendiente"
                iteracion_aceptada = None
                documentos_pendientes += 1
            else:
                continue  # no_aplica o pendiente -> no heredar

            doc_nuevo = DocumentoIng(
                solicitud_ing_id=ing_nueva.id,
                nombre_archivo=doc_ant.nombre_archivo,
                tipo_documento=doc_ant.tipo_documento,
                modulo=doc_ant.modulo,
                tipologia=doc_ant.tipologia,
                estado=nuevo_estado,
                observacion=None if nuevo_estado == "no_aplica" else doc_ant.observacion,
                hash_sha256=doc_ant.hash_sha256,
                ruta_local=doc_ant.ruta_local,
                iteracion_aceptada_en=iteracion_aceptada,
            )
            db.add(doc_nuevo)

        db.commit()
        db.refresh(ing_nueva)

        _log(db, "SolicitudIng", ing_nueva.id, "SIGUIENTE_ITERACION", {
            "iteracion_anterior": ing_anterior.numero_iteracion,
            "iteracion_nueva": ing_nueva.numero_iteracion,
            "documentos_heredados": documentos_heredados,
            "documentos_pendientes": documentos_pendientes,
        }, sid)
        db.commit()
        return ing_nueva

    @staticmethod
    def generar_email(db: Session, solicitud_id: str) -> Dict[str, Any]:
        """Genera el borrador de email con aceptados/observados/faltantes."""
        solicitud = db.get(SolicitudIng, solicitud_id)
        if not solicitud:
            raise ValueError("Solicitud no encontrada")

        # Agrupar documentos por estado
        aceptados = []
        observados = []
        faltantes = []

        for doc in solicitud.documentos:
            if doc.estado == "aceptado":
                aceptados.append(doc)
            elif doc.estado == "observado":
                observados.append(doc)
            elif doc.estado == "faltante":
                faltantes.append(doc)

        # Construir cuerpo del email
        lineas = [
            f"Estimado Coordinador,",
            "",
            f"Resultado verificacion ING — Proyecto {solicitud.nombre_proyecto}:",
            "",
            f"ACEPTADOS ({len(aceptados)}):",
        ]
        for doc in aceptados:
            lineas.append(f"  • {doc.nombre_archivo} — {doc.modulo}")
            if doc.tipologia:
                lineas[-1] += f" ({doc.tipologia})"

        lineas.append("")
        lineas.append(f"OBSERVADOS ({len(observados)}):")
        for doc in observados:
            lineas.append(f"  • {doc.nombre_archivo} — {doc.modulo}")
            if doc.observacion:
                lineas.append(f"    Motivo: {doc.observacion}")

        if faltantes:
            lineas.append("")
            lineas.append(f"FALTANTES ({len(faltantes)}):")
            for doc in faltantes:
                lineas.append(f"  • {doc.nombre_archivo} — {doc.modulo}")
                if doc.observacion:
                    lineas.append(f"    Nota: {doc.observacion}")

        lineas.extend([
            "",
            "Quedo atento.",
            "",
            "---",
            f"Generado por TRAZA — Solicitud ING #{solicitud.numero_iteracion} | {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Session: {solicitud.session_id}",
        ])

        # 1.12: Generar version HTML profesional
        from app.services.email_service import (
            renderizar_email_resultado_ing,
            generar_email_texto_plano,
        )

        cuerpo_html = renderizar_email_resultado_ing(solicitud, aceptados, observados, faltantes)
        cuerpo_texto = generar_email_texto_plano(solicitud, aceptados, observados, faltantes)

        asunto = f"Resultado ING — {solicitud.nombre_proyecto}"

        # Guardar version texto plano en la solicitud (compatibilidad)
        solicitud.email_generado = cuerpo_texto
        db.commit()

        return {
            "asunto": asunto,
            "cuerpo": cuerpo_texto,
            "cuerpo_html": cuerpo_html,
            "estadisticas": {
                "aceptados": len(aceptados),
                "observados": len(observados),
                "faltantes": len(faltantes),
                "total": len(solicitud.documentos),
            },
            "session_id": solicitud.session_id,
        }

    @staticmethod
    def registrar_envio_email(db: Session, solicitud_id: str, session_id: Optional[str] = None) -> SolicitudIng:
        solicitud = db.get(SolicitudIng, solicitud_id)
        if not solicitud:
            raise ValueError("Solicitud no encontrada")

        solicitud.fecha_envio_email = datetime.utcnow()
        db.commit()
        db.refresh(solicitud)

        sid = session_id or _session_id()
        _log(db, "SolicitudIng", solicitud.id, "EMAIL_ENVIADO", {
            "iteracion": solicitud.numero_iteracion,
        }, sid)
        db.commit()
        return solicitud

    @staticmethod
    def dashboard(db: Session) -> Dict[str, Any]:
        """Estadisticas para el panel de Fran."""
        from sqlalchemy import func

        resultados = {
            "en_revision": 0,
            "aceptadas": 0,
            "observadas": 0,
            "recibidas": 0,
            "vencimiento_proximo": [],
            "iteraciones_mes": 0,
        }

        query = select(SolicitudIng.estado, func.count()).group_by(SolicitudIng.estado)
        for estado, count in db.execute(query):
            if estado in resultados:
                resultados[estado] = count

        # Vencimientos proximos (7 dias)
        hoy = datetime.now()
        # SQLite guarda fecha_limite como TEXT, no comparamos directamente
        todas = db.execute(select(SolicitudIng).where(SolicitudIng.estado.in_(["recibida", "en_revision"]))).scalars().all()
        for sol in todas:
            if sol.fecha_limite:
                try:
                    fecha_lim = datetime.strptime(sol.fecha_limite, "%Y-%m-%d")
                    dias_restantes = (fecha_lim - hoy).days
                    if 0 <= dias_restantes <= 7:
                        resultados["vencimiento_proximo"].append({
                            "id": sol.id,
                            "nombre_proyecto": sol.nombre_proyecto,
                            "fecha_limite": sol.fecha_limite,
                            "dias_restantes": dias_restantes,
                            "estado": sol.estado,
                        })
                except (ValueError, TypeError):
                    pass

        # Iteraciones del mes
        primer_dia_mes = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        query_mes = select(func.count()).where(SolicitudIng.created_at >= primer_dia_mes)
        resultados["iteraciones_mes"] = db.execute(query_mes).scalar() or 0

        return resultados


# ──────────────────────────────────────────────
# DocumentoIngService
# ──────────────────────────────────────────────

class DocumentoIngService:

    @staticmethod
    def crear(db: Session, solicitud_id: str, data: DocumentoIngCreate, calcular_hash: bool = True) -> DocumentoIng:
        hash_val = data.hash_sha256
        if calcular_hash and data.ruta_local and not hash_val:
            hash_val = calcular_hash_sha256(data.ruta_local)

        doc = DocumentoIng(
            solicitud_ing_id=solicitud_id,
            nombre_archivo=data.nombre_archivo,
            tipo_documento=data.tipo_documento,
            modulo=data.modulo,
            tipologia=data.tipologia,
            estado="pendiente",
            hash_sha256=hash_val,
            ruta_local=data.ruta_local,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc

    @staticmethod
    def get(db: Session, doc_id: str) -> Optional[DocumentoIng]:
        return db.get(DocumentoIng, doc_id)

    @staticmethod
    def listar_por_solicitud(db: Session, solicitud_id: str) -> List[DocumentoIng]:
        query = select(DocumentoIng).where(DocumentoIng.solicitud_ing_id == solicitud_id)
        return list(db.execute(query).scalars().all())

    @staticmethod
    def cambiar_estado(db: Session, doc_id: str, data: DocumentoIngEstadoPatch, session_id: Optional[str] = None) -> DocumentoIng:
        doc = db.get(DocumentoIng, doc_id)
        if not doc:
            raise ValueError(f"Documento {doc_id} no encontrado")

        # R10: Observacion obligatoria si estado = 'observado'
        if data.estado == "observado" and not data.observacion:
            raise ValueError("El campo 'observacion' es obligatorio cuando estado='observado' (R10)")

        doc.estado = data.estado
        doc.observacion = data.observacion

        # Si se acepta, registrar en qué iteracion
        if data.estado == "aceptado":
            solicitud = db.get(SolicitudIng, doc.solicitud_ing_id)
            if solicitud:
                doc.iteracion_aceptada_en = solicitud.numero_iteracion

        db.commit()
        db.refresh(doc)

        # Transicion automatica de estado de la solicitud (R4)
        SolicitudIngService.transicionar_estado_automatico(db, doc.solicitud_ing_id, session_id=session_id)

        return doc

    @staticmethod
    def recalcular_hash(db: Session, doc_id: str) -> Optional[str]:
        doc = db.get(DocumentoIng, doc_id)
        if not doc:
            raise ValueError(f"Documento {doc_id} no encontrado")

        if not doc.ruta_local or not os.path.isfile(doc.ruta_local):
            return None

        doc.hash_sha256 = calcular_hash_sha256(doc.ruta_local)
        db.commit()
        db.refresh(doc)
        return doc.hash_sha256

    @staticmethod
    def comparar_documentos(db: Session, doc_id_1: str, doc_id_2: str) -> Dict[str, Any]:
        doc1 = db.get(DocumentoIng, doc_id_1)
        doc2 = db.get(DocumentoIng, doc_id_2)

        if not doc1 or not doc2:
            raise ValueError("Uno o ambos documentos no encontrados")

        son_identicos = False
        if doc1.hash_sha256 and doc2.hash_sha256:
            son_identicos = doc1.hash_sha256 == doc2.hash_sha256

        tamano_1 = os.path.getsize(doc1.ruta_local) if doc1.ruta_local and os.path.isfile(doc1.ruta_local) else None
        tamano_2 = os.path.getsize(doc2.ruta_local) if doc2.ruta_local and os.path.isfile(doc2.ruta_local) else None

        return {
            "son_identicos": son_identicos,
            "hash_1": doc1.hash_sha256,
            "hash_2": doc2.hash_sha256,
            "tamano_1": tamano_1,
            "tamano_2": tamano_2,
        }


# ──────────────────────────────────────────────
# RevisionCruzadaService
# ──────────────────────────────────────────────

class RevisionCruzadaService:

    @staticmethod
    def crear_checklist_default(db: Session, solicitud_id: str, session_id: Optional[str] = None) -> List[RevisionCruzada]:
        """Pre-pobla el checklist con las 7 revisiones cruzadas por defecto."""
        sid = session_id or _session_id()
        revisiones = []

        for item in CHECKLIST_TEMPLATE:
            # No crear duplicados
            existente = db.execute(
                select(RevisionCruzada).where(
                    RevisionCruzada.solicitud_ing_id == solicitud_id,
                    RevisionCruzada.numero_revision == item["numero_revision"],
                )
            ).scalar_one_or_none()

            if existente:
                continue

            rev = RevisionCruzada(
                solicitud_ing_id=solicitud_id,
                tipo_revision=item["tipo_revision"],
                numero_revision=item["numero_revision"],
                descripcion=item["descripcion"],
                fuente_1=item.get("fuente_1"),
                valor_1=item.get("valor_1"),
                fuente_2=item.get("fuente_2"),
                valor_2=item.get("valor_2"),
                estado="pendiente",
                fran_marco=False,
                session_id=sid,
            )
            db.add(rev)
            revisiones.append(rev)

        db.commit()
        for rev in revisiones:
            db.refresh(rev)
        return revisiones

    @staticmethod
    def crear(db: Session, solicitud_id: str, data: RevisionCruzadaCreate, session_id: Optional[str] = None) -> RevisionCruzada:
        sid = session_id or _session_id()
        rev = RevisionCruzada(
            solicitud_ing_id=solicitud_id,
            tipo_revision=data.tipo_revision,
            numero_revision=data.numero_revision,
            descripcion=data.descripcion,
            fuente_1=data.fuente_1,
            valor_1=data.valor_1,
            fuente_2=data.fuente_2,
            valor_2=data.valor_2,
            estado="pendiente",
            fran_marco=False,
            session_id=sid,
        )
        db.add(rev)
        db.commit()
        db.refresh(rev)
        return rev

    @staticmethod
    def get(db: Session, rev_id: str) -> Optional[RevisionCruzada]:
        return db.get(RevisionCruzada, rev_id)

    @staticmethod
    def listar_por_solicitud(db: Session, solicitud_id: str) -> List[RevisionCruzada]:
        query = select(RevisionCruzada).where(RevisionCruzada.solicitud_ing_id == solicitud_id)
        return list(db.execute(query).scalars().all())

    @staticmethod
    def marcar_estado(db: Session, rev_id: str, data: RevisionCruzadaEstadoPatch, session_id: Optional[str] = None) -> RevisionCruzada:
        rev = db.get(RevisionCruzada, rev_id)
        if not rev:
            raise ValueError(f"Revision {rev_id} no encontrada")

        rev.estado = data.estado
        # Si se acepta, limpiar la observacion automaticamente
        if data.estado == "aceptado":
            rev.observacion = None
        elif data.observacion is not None:
            rev.observacion = data.observacion
        rev.fran_marco = data.fran_marco
        db.commit()
        db.refresh(rev)

        # Transicion automatica de estado de la solicitud (R4)
        SolicitudIngService.transicionar_estado_automatico(db, rev.solicitud_ing_id, session_id=session_id)

        return rev

    @staticmethod
    def reiniciar_todas(db: Session, solicitud_id: str, session_id: Optional[str] = None) -> int:
        """Reinicia TODAS las revisiones cruzadas a 'pendiente', limpiando observaciones y fran_marco."""
        revisiones = RevisionCruzadaService.listar_por_solicitud(db, solicitud_id)
        count = 0
        for rev in revisiones:
            rev.estado = "pendiente"
            rev.observacion = None
            rev.fran_marco = False
            count += 1
        db.commit()
        # Refrescar despues del commit
        for rev in revisiones:
            db.refresh(rev)

        # Transicion automatica de estado de la solicitud (R4)
        # Nota: al reiniciar a 'pendiente', probablemente vuelva a 'en_revision' si estaba 'observada'
        SolicitudIngService.transicionar_estado_automatico(db, solicitud_id, session_id=session_id)

        return count


# ──────────────────────────────────────────────
# Validacion normativa
# ──────────────────────────────────────────────

class ValidacionNormativaService:

    @staticmethod
    def validar_calicatas(superficie_terreno: float, cantidad_calicatas: int) -> Dict[str, Any]:
        """Valida si la cantidad de calicatas cumple el minimo normativo."""
        minimo = TablaCalicatasMinimas.calicatas_para_superficie(superficie_terreno)
        cumple = cantidad_calicatas >= minimo

        return {
            "superficie_terreno": superficie_terreno,
            "cantidad_calicatas_informada": cantidad_calicatas,
            "minimo_normativo": minimo,
            "cumple": cumple,
            "mensaje": f"Cumple: {cantidad_calicatas} >= {minimo}" if cumple else f"No cumple: {cantidad_calicatas} < {minimo}",
        }
