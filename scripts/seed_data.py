"""
Script de datos de prueba para TRAZA — Modulo ING.

Crea 8 proyectos ficticios con diferentes estados, comunas, tipos y escenarios
de revision para facilitar el desarrollo y testing de la aplicacion.

Uso:
    python scripts/seed_data.py          # Carga datos sobre la DB existente
    python scripts/seed_data.py --reset  # Borra la DB y recrea todo
    python scripts/seed_data.py --help   # Muestra ayuda

Escenarios creados:
    1. Condominio Los Almendros (HAB) — observada, con docs mixtos + ING#2
    2. Centro Medico Los Andes (TEC) — recibida, sin documentos
    3. Villa El Sol (HAB) — observada, con observaciones
    4. Parque Industrial Norte (TEC) — aceptada, lista para R01
    5. Complejo Deportivo (DOS) — en_revision, con docs variados
    6. Residencial El Llano (HAB) — recibida, recien llegada
    7. Conjunto Habitacional Vista (HAB) — observada, con faltantes
    8. Edificio Plaza Central (HAB) — aceptada, lista para R01
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timedelta

from app.database import engine, SessionLocal, init_db
from app.models import Proyecto, LogAuditoria
from app.models_ing import SolicitudIng, DocumentoIng, RevisionCruzada, TablaCalicatasMinimas
from app.schemas_ing import (
    SolicitudIngCreate,
    DocumentoIngCreate,
    DocumentoIngEstadoPatch,
    RevisionCruzadaEstadoPatch,
)
from app.services.ing_service import (
    SolicitudIngService,
    DocumentoIngService,
    RevisionCruzadaService,
)
from app.data.comunas import COMUNAS_OHIGGINS


# ═══════════════════════════════════════════════════════════
# Configuracion
# ═══════════════════════════════════════════════════════════

SESSION_ID = "seed-data-001"

# ═══════════════════════════════════════════════════════════
# Documentos por modulo (templates)
# ═══════════════════════════════════════════════════════════

DOCUMENTOS_TEMPLATES = {
    "MDS": [
        {"nombre": "Informe_MDS_{}.pdf", "tipo": "INFORME"},
        {"nombre": "Plano_Topografia_{}.pdf", "tipo": "PLANO"},
    ],
    "EST": [
        {"nombre": "Memoria_EST_T01_{}.pdf", "tipo": "MEMORIA", "tipologia": "T01"},
        {"nombre": "Memoria_EST_T02_{}.pdf", "tipo": "MEMORIA", "tipologia": "T02"},
        {"nombre": "Plano_EST_T01_{}.pdf", "tipo": "PLANO", "tipologia": "T01"},
        {"nombre": "Plano_EST_T02_{}.pdf", "tipo": "PLANO", "tipologia": "T02"},
    ],
    "HAB": [
        {"nombre": "Memoria_HAB_{}.pdf", "tipo": "MEMORIA"},
        {"nombre": "Plano_HAB_PlantaElevadora_{}.pdf", "tipo": "PLANO"},
        {"nombre": "Presupuesto_HAB_{}.pdf", "tipo": "PRESUPUESTO"},
    ],
    "URB": [
        {"nombre": "Memoria_URB_{}.pdf", "tipo": "MEMORIA"},
        {"nombre": "Plano_URB_Vialidad_{}.pdf", "tipo": "PLANO"},
    ],
}


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

def reset_database():
    """Elimina la base de datos SQLite existente."""
    db_path = "./traza.db"
    for ext in ["", "-shm", "-wal"]:
        f = db_path + ext
        if os.path.exists(f):
            os.remove(f)
            print(f"  [RESET] Eliminado: {f}")
    print("  [RESET] Base de datos limpia")


def contar_solicitudes(db):
    """Cuenta las solicitudes existentes."""
    from sqlalchemy import func
    return db.query(func.count(SolicitudIng.id)).scalar()


def crear_solicitud(db, datos):
    """Crea una solicitud ING usando el servicio oficial."""
    create_data = SolicitudIngCreate(
        nombre_proyecto=datos["nombre"],
        empresa=datos["empresa"],
        tipo_proyecto=datos["tipo_proyecto"],
        comuna=datos["comuna"],
        modulos=datos["modulos"],
        fecha_solicitud=datos["fecha_solicitud"],
        fecha_limite=datos["fecha_limite"],
        link_descarga=datos["link_descarga"],
        tipologias=datos.get("tipologias"),
    )
    solicitud = SolicitudIngService.crear(db, create_data, session_id=SESSION_ID)
    
    # Actualizar campos adicionales
    solicitud.superficie_terreno = datos.get("superficie_terreno")
    solicitud.cantidad_calicatas = datos.get("cantidad_calicatas")
    db.commit()
    db.refresh(solicitud)
    
    return solicitud


def crear_documentos_para_solicitud(db, solicitud):
    """Crea documentos para una solicitud segun sus modulos (todos en pendiente)."""
    docs_creados = []
    for modulo in solicitud.get_modulos():
        templates = DOCUMENTOS_TEMPLATES.get(modulo, [])
        for tmpl in templates:
            nombre = tmpl["nombre"].format(solicitud.acronimo_proyecto or "PROY")
            doc_data = DocumentoIngCreate(
                nombre_archivo=nombre,
                tipo_documento=tmpl["tipo"],
                modulo=modulo,
                tipologia=tmpl.get("tipologia"),
            )
            doc = DocumentoIngService.crear(db, solicitud.id, doc_data)
            docs_creados.append(doc)
    db.refresh(solicitud)
    return docs_creados


def marcar_documento(db, doc, estado, observacion=None):
    """Marca un documento con un estado especifico."""
    patch = DocumentoIngEstadoPatch(estado=estado, observacion=observacion)
    try:
        DocumentoIngService.cambiar_estado(db, doc.id, patch, session_id=SESSION_ID)
    except ValueError as e:
        print(f"      [WARN] No se pudo marcar doc {doc.nombre_archivo}: {e}")


def crear_revisiones_para_solicitud(db, solicitud):
    """Crea el checklist de 7 revisiones cruzadas."""
    RevisionCruzadaService.crear_checklist_default(db, solicitud.id, session_id=SESSION_ID)
    db.refresh(solicitud)


def marcar_revision(db, rev, estado, observacion=None):
    """Marca una revision cruzada con un estado."""
    patch = RevisionCruzadaEstadoPatch(estado=estado, observacion=observacion, fran_marco=True)
    try:
        RevisionCruzadaService.marcar_estado(db, rev.id, patch, session_id=SESSION_ID)
    except ValueError as e:
        print(f"      [WARN] No se pudo marcar rev {rev.numero_revision}: {e}")


def find_doc_by_name(solicitud, partial_name):
    """Encuentra un documento por nombre parcial."""
    for doc in solicitud.documentos:
        if partial_name in doc.nombre_archivo:
            return doc
    return None


def find_rev_by_numero(solicitud, numero):
    """Encuentra una revision por numero."""
    for rev in solicitud.revisiones:
        if rev.numero_revision == numero:
            return rev
    return None


# ═══════════════════════════════════════════════════════════
# Escenarios de configuracion
# ═══════════════════════════════════════════════════════════

def configurar_observada(db, solicitud, docs_observados=None, revs_observadas=None):
    """
    Configura una solicitud como 'observada'.
    Marca algunos documentos/revisiones como observados/faltantes.
    """
    # 1. Cambiar a en_revision
    SolicitudIngService.cambiar_estado(db, solicitud.id, "en_revision", session_id=SESSION_ID)
    
    # 2. Crear documentos y revisiones
    crear_documentos_para_solicitud(db, solicitud)
    crear_revisiones_para_solicitud(db, solicitud)
    
    # 3. Marcar documentos segun config
    if docs_observados:
        for cfg in docs_observados:
            doc = find_doc_by_name(solicitud, cfg["nombre"])
            if doc:
                obs = cfg.get("observacion", f"Observacion: {doc.nombre_archivo}")
                marcar_documento(db, doc, cfg["estado"], obs)
            else:
                print(f"      [WARN] Doc no encontrado: {cfg['nombre']}")
    
    # 4. Marcar revisiones segun config
    if revs_observadas:
        for cfg in revs_observadas:
            rev = find_rev_by_numero(solicitud, cfg["numero"])
            if rev:
                obs = cfg.get("observacion")
                marcar_revision(db, rev, cfg["estado"], obs)
            else:
                print(f"      [WARN] Rev no encontrada: {cfg['numero']}")
    
    # Refrescar para ver estado final
    db.refresh(solicitud)
    return solicitud


def configurar_aceptada(db, solicitud):
    """
    Configura una solicitud como 'aceptada'.
    Marca TODOS los documentos como aceptados y TODAS las revisiones como aceptadas.
    """
    # 1. Cambiar a en_revision
    SolicitudIngService.cambiar_estado(db, solicitud.id, "en_revision", session_id=SESSION_ID)
    
    # 2. Crear documentos y revisiones
    crear_documentos_para_solicitud(db, solicitud)
    crear_revisiones_para_solicitud(db, solicitud)
    
    # 3. Marcar TODOS los documentos como aceptados
    for doc in solicitud.documentos:
        marcar_documento(db, doc, "aceptado")
    
    # 4. Marcar TODAS las revisiones como aceptadas
    for rev in solicitud.revisiones:
        marcar_revision(db, rev, "aceptado")
    
    db.refresh(solicitud)
    return solicitud


def configurar_en_revision(db, solicitud):
    """
    Configura una solicitud como 'en_revision'.
    Crea documentos y revisiones pero deja algunos pendientes.
    """
    # 1. Cambiar a en_revision
    SolicitudIngService.cambiar_estado(db, solicitud.id, "en_revision", session_id=SESSION_ID)
    
    # 2. Crear documentos y revisiones
    crear_documentos_para_solicitud(db, solicitud)
    crear_revisiones_para_solicitud(db, solicitud)
    
    # 3. Marcar algunos documentos como aceptados, dejar otros pendientes
    for doc in solicitud.documentos:
        if "Informe_MDS" in doc.nombre_archivo or "Memoria_EST_T01" in doc.nombre_archivo:
            marcar_documento(db, doc, "aceptado")
    
    # 4. Marcar algunas revisiones como aceptadas, dejar otras pendientes
    for rev in solicitud.revisiones:
        if rev.numero_revision in ("3.1.1", "3.2.3"):
            marcar_revision(db, rev, "aceptado")
    
    db.refresh(solicitud)
    return solicitud


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Carga datos de prueba en TRAZA")
    parser.add_argument("--reset", action="store_true", help="Borra la DB y recrea desde cero")
    args = parser.parse_args()

    print("=" * 60)
    print("  TRAZA — Script de Datos de Prueba")
    print("=" * 60)

    if args.reset:
        print("\n[1/4] Reseteando base de datos...")
        reset_database()
    
    print("\n[1/4] Inicializando base de datos...")
    init_db()
    
    db = SessionLocal()
    
    try:
        count_antes = contar_solicitudes(db)
        if count_antes > 0 and not args.reset:
            print(f"\n  [INFO] Ya existen {count_antes} solicitudes en la DB.")
            print(f"  [INFO] Use --reset para limpiar y recrear.")
            db.close()
            return
        
        print("\n[2/4] Creando proyectos ficticios...")
        solicitudes_creadas = []
        
        # ── 1. Condominio Los Almendros (HAB) — OBSERVADA (para crear ING#2) ──
        print("\n  [1/8] Condominio Los Almendros — OBSERVADA + ING#2...")
        s1 = crear_solicitud(db, {
            "nombre": "Condominio Los Almendros",
            "empresa": "Constructora del Sur SpA",
            "tipo_proyecto": "HAB",
            "comuna": "Rancagua",
            "modulos": ["MDS", "EST", "HAB"],
            "fecha_solicitud": "2026-04-15",
            "fecha_limite": "2026-06-01",
            "link_descarga": "https://drive.google.com/almendros",
            "tipologias": ["T01", "T02"],
            "superficie_terreno": 8500.0,
            "cantidad_calicatas": 4,
        })
        configurar_observada(db, s1,
            docs_observados=[
                {"nombre": "Memoria_EST_T02", "estado": "observado", "observacion": "Memoria EST T02 incompleta, falta verificar cargas vivas"},
                {"nombre": "Plano_HAB", "estado": "faltante", "observacion": "No se entrego plano HAB de planta elevadora"},
            ],
            revs_observadas=[
                {"numero": "3.2.2", "estado": "observado", "observacion": "Memoria EST T02 no verificada"},
                {"numero": "3.3.1", "estado": "faltante", "observacion": "Falta plano HAB"},
            ]
        )
        solicitudes_creadas.append(s1)
        
        # ── 2. Centro Medico Los Andes (TEC) — RECIBIDA ──
        print("  [2/8] Centro Medico Los Andes — RECIBIDA...")
        s2 = crear_solicitud(db, {
            "nombre": "Centro Medico Los Andes",
            "empresa": "Inversiones Saludable Ltda",
            "tipo_proyecto": "TEC",
            "comuna": "Rengo",
            "modulos": ["MDS", "EST"],
            "fecha_solicitud": "2026-05-10",
            "fecha_limite": "2026-07-20",
            "link_descarga": "https://drive.google.com/centromedico",
            "tipologias": None,
            "superficie_terreno": 3200.0,
            "cantidad_calicatas": 3,
        })
        # Sin documentos, sin revisiones — queda en recibida
        solicitudes_creadas.append(s2)
        
        # ── 3. Villa El Sol (HAB) — OBSERVADA ──
        print("  [3/8] Villa El Sol — OBSERVADA...")
        s3 = crear_solicitud(db, {
            "nombre": "Villa El Sol",
            "empresa": "Desarrollos Habitacionales SA",
            "tipo_proyecto": "HAB",
            "comuna": "Requínoa",
            "modulos": ["MDS", "EST", "HAB"],
            "fecha_solicitud": "2026-03-20",
            "fecha_limite": "2026-05-15",
            "link_descarga": "https://drive.google.com/villasol",
            "tipologias": ["T01"],
            "superficie_terreno": 12000.0,
            "cantidad_calicatas": 5,
        })
        configurar_observada(db, s3,
            docs_observados=[
                {"nombre": "Memoria_EST_T01", "estado": "observado", "observacion": "Falta verificar combinaciones de carga"},
                {"nombre": "Presupuesto_HAB", "estado": "faltante", "observacion": "Presupuesto HAB no entregado"},
            ],
            revs_observadas=[
                {"numero": "3.2.2", "estado": "observado", "observacion": "Memoria EST incompleta"},
                {"numero": "3.3.3", "estado": "faltante", "observacion": "Falta presupuesto HAB"},
            ]
        )
        solicitudes_creadas.append(s3)
        
        # ── 4. Parque Industrial Norte (TEC) — ACEPTADA ──
        print("  [4/8] Parque Industrial Norte — ACEPTADA...")
        s4 = crear_solicitud(db, {
            "nombre": "Parque Industrial Norte",
            "empresa": "Grupo Industrial Cachapoal SpA",
            "tipo_proyecto": "TEC",
            "comuna": "San Fernando",
            "modulos": ["MDS", "EST", "URB"],
            "fecha_solicitud": "2026-02-01",
            "fecha_limite": "2026-04-30",
            "link_descarga": "https://drive.google.com/parqueind",
            "tipologias": None,
            "superficie_terreno": 25000.0,
            "cantidad_calicatas": 8,
        })
        configurar_aceptada(db, s4)
        solicitudes_creadas.append(s4)
        
        # ── 5. Complejo Deportivo (DOS) — EN_REVISION ──
        print("  [5/8] Complejo Deportivo — EN_REVISION...")
        s5 = crear_solicitud(db, {
            "nombre": "Complejo Deportivo",
            "empresa": "Municipalidad de Santa Cruz",
            "tipo_proyecto": "DOS",
            "comuna": "Santa Cruz",
            "modulos": ["MDS", "EST", "HAB"],
            "fecha_solicitud": "2026-04-25",
            "fecha_limite": "2026-07-10",
            "link_descarga": "https://drive.google.com/deportivo",
            "tipologias": ["T01"],
            "superficie_terreno": 18000.0,
            "cantidad_calicatas": 6,
        })
        configurar_en_revision(db, s5)
        solicitudes_creadas.append(s5)
        
        # ── 6. Residencial El Llano (HAB) — RECIBIDA ──
        print("  [6/8] Residencial El Llano — RECIBIDA...")
        s6 = crear_solicitud(db, {
            "nombre": "Residencial El Llano",
            "empresa": "Constructora Llano Verde Ltda",
            "tipo_proyecto": "HAB",
            "comuna": "Machalí",
            "modulos": ["MDS", "EST", "HAB"],
            "fecha_solicitud": "2026-05-12",
            "fecha_limite": "2026-08-01",
            "link_descarga": "https://drive.google.com/elllano",
            "tipologias": ["T01", "T02"],
            "superficie_terreno": 5500.0,
            "cantidad_calicatas": 4,
        })
        # Sin documentos, recien llegada
        solicitudes_creadas.append(s6)
        
        # ── 7. Conjunto Habitacional Vista (HAB) — OBSERVADA ──
        print("  [7/8] Conjunto Habitacional Vista — OBSERVADA...")
        s7 = crear_solicitud(db, {
            "nombre": "Conjunto Habitacional Vista",
            "empresa": "Inmobiliaria Vista Hermosa SA",
            "tipo_proyecto": "HAB",
            "comuna": "Doñihue",
            "modulos": ["MDS", "EST", "HAB"],
            "fecha_solicitud": "2026-03-05",
            "fecha_limite": "2026-04-20",
            "link_descarga": "https://drive.google.com/vista",
            "tipologias": ["T01"],
            "superficie_terreno": 4200.0,
            "cantidad_calicatas": 3,
        })
        configurar_observada(db, s7,
            docs_observados=[
                {"nombre": "Memoria_HAB", "estado": "faltante", "observacion": "Memoria HAB no entregada"},
                {"nombre": "Presupuesto_HAB", "estado": "observado", "observacion": "Presupuesto no cuadra con memorias"},
            ],
            revs_observadas=[
                {"numero": "3.3.2", "estado": "faltante", "observacion": "Falta memoria HAB"},
                {"numero": "3.3.3", "estado": "observado", "observacion": "Presupuesto inconsistente"},
            ]
        )
        solicitudes_creadas.append(s7)
        
        # ── 8. Edificio Plaza Central (HAB) — ACEPTADA ──
        print("  [8/8] Edificio Plaza Central — ACEPTADA...")
        s8 = crear_solicitud(db, {
            "nombre": "Edificio Plaza Central",
            "empresa": "Constructora Metropolitana SpA",
            "tipo_proyecto": "HAB",
            "comuna": "Rancagua",
            "modulos": ["MDS", "EST", "HAB", "URB"],
            "fecha_solicitud": "2026-01-15",
            "fecha_limite": "2026-03-30",
            "link_descarga": "https://drive.google.com/plazacentral",
            "tipologias": ["T01", "T02"],
            "superficie_terreno": 15000.0,
            "cantidad_calicatas": 6,
        })
        configurar_aceptada(db, s8)
        solicitudes_creadas.append(s8)
        
        # ── ING#2 para Los Almendros ──
        print("\n[3/4] Creando iteracion ING#2 para Los Almendros...")
        try:
            ing2 = SolicitudIngService.crear_siguiente_iteracion(db, s1.id, session_id=SESSION_ID)
            print(f"  [OK] ING#2 creada: {ing2.acronimo_proyecto} (iteracion #{ing2.numero_iteracion})")
            
            # Configurar ING#2 como en_revision con algunos docs
            configurar_en_revision(db, ing2)
            
            # Marcar algunos documentos como observados para variedad
            for doc in ing2.documentos:
                if "Memoria_EST_T01" in doc.nombre_archivo:
                    marcar_documento(db, doc, "observado", 
                        "Memoria EST T01 requiere correcciones de la iteracion anterior")
                elif "Informe_MDS" in doc.nombre_archivo:
                    marcar_documento(db, doc, "aceptado")
            
            db.refresh(ing2)
            
        except ValueError as e:
            print(f"  [WARN] No se pudo crear ING#2: {e}")
        
        # ── Resumen ──
        print("\n[4/4] Resumen de datos creados:")
        print("-" * 60)
        
        for sol in solicitudes_creadas:
            docs_count = len(sol.documentos)
            rev_count = len(sol.revisiones)
            estado_icon = {
                "recibida": "📥",
                "en_revision": "🔍",
                "aceptada": "✅",
                "observada": "⚠️",
            }.get(sol.estado, "❓")
            
            print(f"  {estado_icon} {sol.acronimo_proyecto} — {sol.nombre_proyecto}")
            print(f"      Estado: {sol.estado} | Iteracion: #{sol.numero_iteracion}")
            print(f"      Comuna: {sol.comuna} | Empresa: {sol.empresa}")
            print(f"      Documentos: {docs_count} | Revisiones: {rev_count}")
            print()
        
        count_despues = contar_solicitudes(db)
        print("-" * 60)
        print(f"  Total solicitudes: {count_despues}")
        print("-" * 60)
        print("\n  ✅ Datos de prueba cargados exitosamente!")
        print(f"\n  Para iniciar TRAZA:")
        print(f"     uvicorn app.main:app --reload --host 127.0.0.1 --port 8000")
        print(f"     http://127.0.0.1:8000/ing")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
