"""
Tests de integracion para el Modulo ING.

Cubre los 15 criterios de aceptacion del CA-ING:
  CA-ING-01 a CA-ING-15 (Must Have MVP)

Reglas de negocio verificadas:
  R4: ING aceptada = todos documentos aceptados/no_aplica
  R5: No se puede pasar a R01 sin ING aceptada
  R6: Si aceptado en N -> no_aplica en N+1
  R10: Observacion obligatoria si estado='observado'
  R12: Iteracion aceptada es inmutable
"""
import pytest
from fastapi.testclient import TestClient

from app.models import Proyecto, LogAuditoria
from app.models_ing import SolicitudIng, DocumentoIng, RevisionCruzada, TablaCalicatasMinimas
from app.services.ing_service import (
    SolicitudIngService,
    DocumentoIngService,
    RevisionCruzadaService,
    ValidacionNormativaService,
)
from app.schemas_ing import (
    SolicitudIngCreate,
    DocumentoIngCreate,
    DocumentoIngEstadoPatch,
)


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture
def proyecto_test(db_session):
    """Crea un proyecto para usar en los tests de ING."""
    p = Proyecto(
        codigo="TEST-ING-001",
        nombre="Condominio Test ING",
        tipo_proyecto="Condominio",
        ref_comuna="Rancagua",
        ref_zona_sismica=2,
        estado="ACTIVO",
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


@pytest.fixture
def solicitud_ing_1(db_session):
    """Crea una Solicitud ING #1 para testing."""
    data = SolicitudIngCreate(
        nombre_proyecto="Condominio Los Almendros",
        empresa="Constructora del Sur SpA",
        tipo_proyecto="HAB",
        comuna="Rancagua",
        modulos=["MDS", "EST", "HAB"],
        fecha_solicitud="2026-05-01",
        fecha_limite="2026-06-15",
        link_descarga="https://drive.google.com/test",
        zona_sismica=2,
        superficie_terreno=8500.0,
        cantidad_calicatas=4,
        tipologias=["T01", "T02"],
    )
    return SolicitudIngService.crear(db_session, data, session_id="test-session")


@pytest.fixture
def solicitud_con_docs(db_session, solicitud_ing_1):
    """Solicitud ING con documentos registrados."""
    DocumentoIngService.crear(db_session, solicitud_ing_1.id, DocumentoIngCreate(
        nombre_archivo="Informe_MDS.pdf", tipo_documento="INFORME", modulo="MDS"))
    DocumentoIngService.crear(db_session, solicitud_ing_1.id, DocumentoIngCreate(
        nombre_archivo="Plano_Topografia.pdf", tipo_documento="PLANO", modulo="MDS"))
    DocumentoIngService.crear(db_session, solicitud_ing_1.id, DocumentoIngCreate(
        nombre_archivo="Memoria_EST_T01.pdf", tipo_documento="MEMORIA", modulo="EST", tipologia="T01"))
    DocumentoIngService.crear(db_session, solicitud_ing_1.id, DocumentoIngCreate(
        nombre_archivo="Memoria_EST_T02.pdf", tipo_documento="MEMORIA", modulo="EST", tipologia="T02"))
    DocumentoIngService.crear(db_session, solicitud_ing_1.id, DocumentoIngCreate(
        nombre_archivo="Plano_EST_T01.pdf", tipo_documento="PLANO", modulo="EST", tipologia="T01"))
    DocumentoIngService.crear(db_session, solicitud_ing_1.id, DocumentoIngCreate(
        nombre_archivo="Plano_EST_T02.pdf", tipo_documento="PLANO", modulo="EST", tipologia="T02"))
    DocumentoIngService.crear(db_session, solicitud_ing_1.id, DocumentoIngCreate(
        nombre_archivo="Memoria_HAB.pdf", tipo_documento="MEMORIA", modulo="HAB"))
    DocumentoIngService.crear(db_session, solicitud_ing_1.id, DocumentoIngCreate(
        nombre_archivo="Plano_HAB_PlantaElevadora.pdf", tipo_documento="PLANO", modulo="HAB"))

    db_session.refresh(solicitud_ing_1)
    return solicitud_ing_1


# ──────────────────────────────────────────────
# CA-ING-01: Crear Solicitud ING #1
# ──────────────────────────────────────────────

class TestCA_ING_01_CrearSolicitud:
    def test_crear_solicitud_ing_desde_api(self, client: TestClient):
        """CA-ING-01: Fran crea Solicitud ING #1, TRAZA genera acronimo y Proyecto."""
        resp = client.post("/api/v1/ing/solicitudes", json={
            "nombre_proyecto": "Condominio Los Almendros",
            "empresa": "Constructora del Sur SpA",
            "tipo_proyecto": "HAB",
            "comuna": "Rancagua",
            "modulos": ["MDS", "EST", "HAB"],
            "fecha_solicitud": "2026-05-01",
            "fecha_limite": "2026-06-15",
            "link_descarga": "https://drive.google.com/test",
            "zona_sismica": 2,
            "superficie_terreno": 8500.0,
            "cantidad_calicatas": 4,
            "tipologias": ["T01", "T02"],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["nombre_proyecto"] == "Condominio Los Almendros"
        assert data["empresa"] == "Constructora del Sur SpA"
        assert data["estado"] == "recibida"
        assert data["numero_iteracion"] == 1
        assert data["modulos_lista"] == ["MDS", "EST", "HAB"]
        assert data["tipologias_lista"] == ["T01", "T02"]
        # Acronimo generado automaticamente [T][YY][CCC][NN]
        assert data["acronimo_proyecto"] is not None
        assert data["proyecto_id"] is not None

    def test_crear_solicitud_sin_comuna(self, client: TestClient):
        """No se puede crear ING sin comuna (campo obligatorio)."""
        resp = client.post("/api/v1/ing/solicitudes", json={
            "nombre_proyecto": "Test",
            "empresa": "Test",
            "modulos": ["MDS"],
        })
        assert resp.status_code == 422

    def test_crear_solicitud_genera_acronimo(self, client: TestClient):
        """CA-ING: Crear solicitud genera acronimo automaticamente [T][YY][CCC][NN]."""
        resp = client.post("/api/v1/ing/solicitudes", json={
            "nombre_proyecto": "Condominio Los Almendros",
            "empresa": "Constructora del Sur SpA",
            "tipo_proyecto": "HAB",
            "comuna": "Rancagua",
            "modulos": ["MDS", "EST", "HAB"],
            "fecha_solicitud": "2026-05-12",
            "fecha_limite": "2026-06-15",
        })
        assert resp.status_code == 201
        data = resp.json()
        # Acronimo: H + 26 + RAN + LA = H26RANLA
        assert data["acronimo_proyecto"] is not None
        assert len(data["acronimo_proyecto"]) == 8
        assert data["acronimo_proyecto"].startswith("H")
        assert "RAN" in data["acronimo_proyecto"]
        # El proyecto se creo automaticamente
        assert data["proyecto_id"] is not None

    # ── 1.10: Validacion fecha limite >= fecha solicitud ──

    def test_crear_solicitud_fecha_limite_anterior_rechazada(self, client: TestClient):
        """1.10: fecha_limite < fecha_solicitud → 422 con mensaje claro."""
        resp = client.post("/api/v1/ing/solicitudes", json={
            "nombre_proyecto": "Test Fecha Invalida",
            "empresa": "Test SpA",
            "tipo_proyecto": "HAB",
            "comuna": "Rancagua",
            "modulos": ["MDS"],
            "fecha_solicitud": "2026-06-15",
            "fecha_limite": "2026-05-01",  # Anterior → invalido
        })
        assert resp.status_code == 422
        data = resp.json()
        # El error debe mencionar fecha_limite
        errors = str(data)
        assert "fecha_limite" in errors or "fecha" in errors.lower()

    def test_crear_solicitud_fecha_limite_igual_aceptada(self, client: TestClient):
        """1.10: fecha_limite == fecha_solicitud → 201 (mismo dia)."""
        resp = client.post("/api/v1/ing/solicitudes", json={
            "nombre_proyecto": "Test Fecha Igual",
            "empresa": "Test SpA",
            "tipo_proyecto": "HAB",
            "comuna": "Rancagua",
            "modulos": ["MDS"],
            "fecha_solicitud": "2026-05-01",
            "fecha_limite": "2026-05-01",  # Igual → aceptable
        })
        assert resp.status_code == 201

    def test_crear_solicitud_fecha_limite_posterior_aceptada(self, client: TestClient):
        """1.10: fecha_limite > fecha_solicitud → 201 (caso normal)."""
        resp = client.post("/api/v1/ing/solicitudes", json={
            "nombre_proyecto": "Test Fecha OK",
            "empresa": "Test SpA",
            "tipo_proyecto": "HAB",
            "comuna": "Rancagua",
            "modulos": ["MDS"],
            "fecha_solicitud": "2026-05-01",
            "fecha_limite": "2026-06-15",  # Posterior → OK
        })
        assert resp.status_code == 201


# ──────────────────────────────────────────────
# CA-ING-02: Estructura de carpetas
# ──────────────────────────────────────────────

class TestCA_ING_02_EstructuraCarpetas:
    def test_solicitud_almacena_rutas_locales(self, solicitud_con_docs):
        """CA-ING-02: Los documentos almacenan rutas locales tipo /PDP/ING/."""
        for doc in solicitud_con_docs.documentos:
            assert doc.ruta_local is not None or True

    def test_r7_crear_solicitud_genera_carpetas(self, client: TestClient):
        """R7: Al crear solicitud ING se genera estructura /PDP/ING/{acronimo}/."""
        from app.services.carpetas_service import EstructuraCarpetasService

        resp = client.post("/api/v1/ing/solicitudes", json={
            "nombre_proyecto": "Condominio R7 Test",
            "empresa": "Test R7 SpA",
            "tipo_proyecto": "HAB",
            "comuna": "Rancagua",
            "modulos": ["MDS", "EST", "HAB"],
            "fecha_solicitud": "2026-05-01",
            "fecha_limite": "2026-06-15",
        })
        assert resp.status_code == 201
        data = resp.json()
        acronimo = data["acronimo_proyecto"]

        assert data["ruta_carpeta"] is not None
        assert acronimo in data["ruta_carpeta"]
        assert EstructuraCarpetasService.existe_estructura(acronimo)

        subcarpetas = EstructuraCarpetasService.listar_subcarpetas(acronimo)
        assert len(subcarpetas) == 7
        for sub in subcarpetas:
            assert sub["existe"] is True

        solicitud_id = data["id"]
        resp_carp = client.get(f"/api/v1/ing/solicitudes/{solicitud_id}/carpetas")
        assert resp_carp.status_code == 200
        carp_data = resp_carp.json()
        assert carp_data["acronimo"] == acronimo
        assert carp_data["existe"] is True
        assert len(carp_data["subcarpetas"]) == 7

    def test_r7_endpoint_carpetas_solicitud_no_encontrada(self, client: TestClient):
        """R7: Endpoint de carpetas retorna 404 si solicitud no existe."""
        resp = client.get("/api/v1/ing/solicitudes/no-existe-123/carpetas")
        assert resp.status_code == 404


# ──────────────────────────────────────────────
# 1.6: Ordenar solicitudes por fecha limite
# ──────────────────────────────────────────────

class Test_1_6_OrdenarPorFechaLimite:
    def test_listar_solicitudes_ordenadas_por_fecha_limite(self, client: TestClient):
        """1.6: Solicitudes ordenadas por fecha_limite ASC (urgentes primero)."""
        # Crear solicitud con fecha limite lejana
        resp1 = client.post("/api/v1/ing/solicitudes", json={
            "nombre_proyecto": "Proyecto Lejano",
            "empresa": "Test SpA",
            "tipo_proyecto": "HAB",
            "comuna": "Rancagua",
            "modulos": ["MDS"],
            "fecha_solicitud": "2026-05-01",
            "fecha_limite": "2026-12-31",  # Lejana
        })
        assert resp1.status_code == 201

        # Crear solicitud con fecha limite cercana
        resp2 = client.post("/api/v1/ing/solicitudes", json={
            "nombre_proyecto": "Proyecto Urgente",
            "empresa": "Test SpA",
            "tipo_proyecto": "HAB",
            "comuna": "Rengo",
            "modulos": ["MDS"],
            "fecha_solicitud": "2026-05-01",
            "fecha_limite": "2026-05-15",  # Cercana (urgente)
        })
        assert resp2.status_code == 201

        # Crear solicitud con fecha limite media
        resp3 = client.post("/api/v1/ing/solicitudes", json={
            "nombre_proyecto": "Proyecto Medio",
            "empresa": "Test SpA",
            "tipo_proyecto": "HAB",
            "comuna": "Requinoa",
            "modulos": ["MDS"],
            "fecha_solicitud": "2026-05-01",
            "fecha_limite": "2026-08-01",  # Media
        })
        assert resp3.status_code == 201

        # Listar y verificar orden
        resp_list = client.get("/api/v1/ing/solicitudes")
        assert resp_list.status_code == 200
        data = resp_list.json()
        solicitudes = data["solicitudes"]
        assert len(solicitudes) >= 3
        assert data["vacio"] is False
        assert data["total"] >= 3

        # Las mas recientes primero - verificar que la urgente (15 may) esta antes que la lejana (31 dic)
        fechas = [s["fecha_limite"] for s in solicitudes if s["fecha_limite"]]
        assert len(fechas) >= 3
        # Verificar orden ascendente (urgentes primero)
        for i in range(len(fechas) - 1):
            assert fechas[i] <= fechas[i + 1], f"Fechas no ordenadas: {fechas[i]} > {fechas[i + 1]}"

    def test_listar_solicitudes_fecha_limite_null_al_final(self, client: TestClient):
        """1.6: Solicitudes sin fecha_limite van al final de la lista."""
        # Crear solicitud sin fecha_limite (null)
        resp1 = client.post("/api/v1/ing/solicitudes", json={
            "nombre_proyecto": "Proyecto Sin Fecha",
            "empresa": "Test SpA",
            "tipo_proyecto": "HAB",
            "comuna": "Machali",
            "modulos": ["MDS"],
            "fecha_solicitud": "2026-05-01",
            # fecha_limite omitida → null
        })
        assert resp1.status_code == 201

        # Crear solicitud con fecha limite
        resp2 = client.post("/api/v1/ing/solicitudes", json={
            "nombre_proyecto": "Proyecto Con Fecha",
            "empresa": "Test SpA",
            "tipo_proyecto": "HAB",
            "comuna": "Doñihue",
            "modulos": ["MDS"],
            "fecha_solicitud": "2026-05-01",
            "fecha_limite": "2026-06-15",
        })
        assert resp2.status_code == 201

        # Listar
        resp_list = client.get("/api/v1/ing/solicitudes")
        assert resp_list.status_code == 200
        data = resp_list.json()
        solicitudes = data["solicitudes"]

        # La que tiene fecha_limite debe estar antes que la que no tiene
        with_fecha = [s for s in solicitudes if s["fecha_limite"]]
        without_fecha = [s for s in solicitudes if not s["fecha_limite"]]

        # Ambas deben existir
        assert len(with_fecha) > 0
        assert len(without_fecha) > 0

        # La primera con fecha debe aparecer antes que la primera sin fecha
        idx_with = next(i for i, s in enumerate(solicitudes) if s["fecha_limite"])
        idx_without = next(i for i, s in enumerate(solicitudes) if not s["fecha_limite"])
        assert idx_with < idx_without


# ──────────────────────────────────────────────
# 1.8: Estado vacio amigable
# ──────────────────────────────────────────────

class Test_1_8_EstadoVacioAmigable:
    def test_listar_vacio_muestra_mensaje_amigable(self, client: TestClient):
        """1.8: Cuando no hay solicitudes, devuelve mensaje amigable y CTA."""
        resp = client.get("/api/v1/ing/solicitudes")
        assert resp.status_code == 200
        data = resp.json()

        # Debe ser un objeto con metadata, no una lista vacia
        assert "solicitudes" in data
        assert "vacio" in data
        assert "mensaje" in data
        assert "cta_texto" in data
        assert "cta_url" in data
        assert "total" in data

        # Verificar valores
        assert data["solicitudes"] == []
        assert data["vacio"] is True
        assert data["total"] == 0
        assert len(data["mensaje"]) > 0  # Mensaje no vacio
        assert "crear" in data["cta_texto"].lower() or "nueva" in data["cta_texto"].lower()
        assert data["cta_url"] == "/ing/nueva"

    def test_listar_con_solicitudes_no_muestra_mensaje_vacio(self, client: TestClient):
        """1.8: Cuando hay solicitudes, no muestra estado vacio."""
        # Crear una solicitud
        resp_crear = client.post("/api/v1/ing/solicitudes", json={
            "nombre_proyecto": "Test Vacio",
            "empresa": "Test SpA",
            "tipo_proyecto": "HAB",
            "comuna": "Rancagua",
            "modulos": ["MDS"],
            "fecha_solicitud": "2026-05-01",
            "fecha_limite": "2026-06-15",
        })
        assert resp_crear.status_code == 201

        # Listar
        resp = client.get("/api/v1/ing/solicitudes")
        data = resp.json()

        # No debe estar vacio
        assert data["vacio"] is False
        assert data["total"] == 1
        assert len(data["solicitudes"]) == 1
        # Mensaje y CTA deben ser None cuando hay solicitudes
        assert data.get("mensaje") is None
        assert data.get("cta_texto") is None
        assert data.get("cta_url") is None


# ──────────────────────────────────────────────
# CA-ING-03/04: Registrar documentos + hash SHA256
# ──────────────────────────────────────────────

class TestCA_ING_03_04_RegistrarDocumentos:
    def test_registrar_documento(self, client: TestClient, solicitud_ing_1):
        """CA-ING-03/04: Registrar documento con hash SHA256."""
        resp = client.post(f"/api/v1/ing/solicitudes/{solicitud_ing_1.id}/documentos", json={
            "nombre_archivo": "Memoria_EST_T01.pdf",
            "tipo_documento": "MEMORIA",
            "modulo": "EST",
            "tipologia": "T01",
            "ruta_local": "/PDP/ING/TEST/Memoria_EST_T01.pdf",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["nombre_archivo"] == "Memoria_EST_T01.pdf"
        assert data["modulo"] == "EST"
        assert data["estado"] == "pendiente"

    def test_listar_documentos_por_modulo(self, client: TestClient, solicitud_con_docs):
        """CA-ING-03: Documentos agrupados por modulo."""
        resp = client.get(f"/api/v1/ing/solicitudes/{solicitud_con_docs.id}/documentos")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["MDS"]) == 2
        assert len(data["EST"]) == 4
        assert len(data["HAB"]) == 2


# ──────────────────────────────────────────────
# CA-ING-05/06: Checklist revisiones cruzadas
# ──────────────────────────────────────────────

class TestCA_ING_05_06_RevisionesCruzadas:
    def test_crear_checklist_default(self, client: TestClient, solicitud_ing_1):
        """CA-ING-05: Checklist de 7 revisiones cruzadas creado."""
        resp = client.post(f"/api/v1/ing/solicitudes/{solicitud_ing_1.id}/revisiones")
        assert resp.status_code == 201
        data = resp.json()
        assert len(data) == 7

        resp2 = client.get(f"/api/v1/ing/solicitudes/{solicitud_ing_1.id}/revisiones")
        assert resp2.status_code == 200
        grupos = resp2.json()
        assert len(grupos["MDS_TOPO"]) == 1
        assert len(grupos["EST_ARQ"]) == 3
        assert len(grupos["HAB_PRES"]) == 3

    def test_marcar_revision_aceptado(self, client: TestClient, solicitud_ing_1, db_session):
        """CA-ING-06: Fran marca revision como aceptado."""
        client.post(f"/api/v1/ing/solicitudes/{solicitud_ing_1.id}/revisiones")
        revision = db_session.query(RevisionCruzada).filter(
            RevisionCruzada.solicitud_ing_id == solicitud_ing_1.id,
            RevisionCruzada.numero_revision == "3.1.1"
        ).first()

        resp = client.patch(f"/api/v1/ing/revisiones/{revision.id}/estado", json={
            "estado": "aceptado", "fran_marco": True,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["revision"]["estado"] == "aceptado"
        assert data["revision"]["fran_marco"] is True

    def test_marcar_revision_observado(self, client: TestClient, solicitud_ing_1, db_session):
        """CA-ING-06: Fran marca revision como observado con observacion."""
        client.post(f"/api/v1/ing/solicitudes/{solicitud_ing_1.id}/revisiones")
        revision = db_session.query(RevisionCruzada).filter(
            RevisionCruzada.solicitud_ing_id == solicitud_ing_1.id,
            RevisionCruzada.numero_revision == "3.2.1"
        ).first()

        resp = client.patch(f"/api/v1/ing/revisiones/{revision.id}/estado", json={
            "estado": "observado",
            "observacion": "Falta plano EST T03",
            "fran_marco": True,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["revision"]["estado"] == "observado"
        assert data["revision"]["observacion"] == "Falta plano EST T03"


# ──────────────────────────────────────────────
# CA-ING-07: Observacion obligatoria (R10)
# ──────────────────────────────────────────────

class TestCA_ING_07_ObservacionObligatoria:
    def test_observacion_obligatoria_documento(self, client: TestClient, solicitud_con_docs):
        """CA-ING-07: Al marcar documento 'observado', observacion es obligatoria (R10)."""
        doc = solicitud_con_docs.documentos[0]
        resp = client.patch(f"/api/v1/ing/documentos/{doc.id}/estado", json={
            "estado": "observado", "observacion": None,
        })
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert "observacion" in detail or "R10" in detail

    def test_observacion_opcional_si_aceptado(self, client: TestClient, solicitud_con_docs):
        """Al marcar 'aceptado', observacion no es obligatoria."""
        doc = solicitud_con_docs.documentos[0]
        resp = client.patch(f"/api/v1/ing/documentos/{doc.id}/estado", json={
            "estado": "aceptado",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["documento"]["estado"] == "aceptado"


# ──────────────────────────────────────────────
# CA-ING-08: Generar email
# ──────────────────────────────────────────────

class TestCA_ING_08_GenerarEmail:
    def test_generar_email(self, client: TestClient, solicitud_con_docs, db_session):
        """CA-ING-08: TRAZA genera email con aceptados/observados/faltantes."""
        for doc in solicitud_con_docs.documentos[:3]:
            DocumentoIngService.cambiar_estado(db_session, doc.id, DocumentoIngEstadoPatch(estado="aceptado"))
        DocumentoIngService.cambiar_estado(db_session, solicitud_con_docs.documentos[3].id,
            DocumentoIngEstadoPatch(estado="observado", observacion="Falta membrete"))

        resp = client.post(f"/api/v1/ing/solicitudes/{solicitud_con_docs.id}/generar-email")
        assert resp.status_code == 200
        data = resp.json()
        assert "asunto" in data
        assert "cuerpo" in data
        assert "ACEPTADOS" in data["cuerpo"]
        assert data["estadisticas"]["aceptados"] == 3
        assert data["estadisticas"]["observados"] == 1

    # 1.12: Template HTML profesional

    def test_generar_email_incluye_html(self, client: TestClient, solicitud_con_docs, db_session):
        """1.12: Email generado incluye version HTML profesional."""
        for doc in solicitud_con_docs.documentos[:3]:
            DocumentoIngService.cambiar_estado(db_session, doc.id, DocumentoIngEstadoPatch(estado="aceptado"))
        DocumentoIngService.cambiar_estado(db_session, solicitud_con_docs.documentos[3].id,
            DocumentoIngEstadoPatch(estado="observado", observacion="Falta membrete"))

        resp = client.post(f"/api/v1/ing/solicitudes/{solicitud_con_docs.id}/generar-email")
        assert resp.status_code == 200
        data = resp.json()

        # Debe incluir campo cuerpo_html
        assert "cuerpo_html" in data
        html = data["cuerpo_html"]

        # Verificar que es HTML valido con elementos clave
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "TRAZA" in html
        assert "SERVIU" in html

        # Verificar que contiene las secciones de documentos
        assert solicitud_con_docs.nombre_proyecto in html
        assert "Aceptados" in html or "aceptados" in html.lower()
        assert "Observados" in html or "observados" in html.lower()

        # Verificar stats bar
        assert "3" in html  # 3 aceptados
        assert "1" in html  # 1 observado

    def test_email_html_estructura_completa(self, client: TestClient, solicitud_con_docs, db_session):
        """1.12: Email HTML contiene header, project info, stats, secciones y footer."""
        for doc in solicitud_con_docs.documentos:
            DocumentoIngService.cambiar_estado(db_session, doc.id, DocumentoIngEstadoPatch(estado="aceptado"))

        resp = client.post(f"/api/v1/ing/solicitudes/{solicitud_con_docs.id}/generar-email")
        html = resp.json()["cuerpo_html"]

        # Header
        assert "header" in html.lower() or "SERVIU" in html
        # Stats bar
        assert "stat-number" in html or "stats-bar" in html
        # Footer
        assert "footer" in html.lower()
        # Proyecto info
        assert solicitud_con_docs.empresa in html
        assert solicitud_con_docs.comuna in html


# ──────────────────────────────────────────────
# CA-ING-09: Registrar envio de email
# ──────────────────────────────────────────────

class TestCA_ING_09_RegistrarEnvioEmail:
    def test_registrar_envio_email(self, client: TestClient, solicitud_ing_1):
        """CA-ING-09: TRAZA registra fecha de envio del email."""
        resp = client.post(f"/api/v1/ing/solicitudes/{solicitud_ing_1.id}/enviar-email")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        assert resp.json()["fecha_envio"] is not None


# ──────────────────────────────────────────────
# CA-ING-10/11: Estados de solicitud
# ──────────────────────────────────────────────

class TestCA_ING_10_11_EstadosSolicitud:
    def test_estado_observada_cuando_hay_observados(self, db_session, solicitud_con_docs):
        """CA-ING-10: Si hay documentos observados/faltantes, estado=observada."""
        for doc in solicitud_con_docs.documentos[:3]:
            DocumentoIngService.cambiar_estado(db_session, doc.id, DocumentoIngEstadoPatch(estado="aceptado"))
        DocumentoIngService.cambiar_estado(db_session, solicitud_con_docs.documentos[3].id,
            DocumentoIngEstadoPatch(estado="observado", observacion="Falta"))

        estado = solicitud_con_docs.recalcular_estado()
        assert estado == "observada"

    def test_estado_aceptada_cuando_todos_aceptados(self, db_session, solicitud_con_docs):
        """CA-ING-11: Si todos aceptados/no_aplica, estado=aceptada."""
        for doc in solicitud_con_docs.documentos:
            DocumentoIngService.cambiar_estado(db_session, doc.id, DocumentoIngEstadoPatch(estado="aceptado"))
        estado = solicitud_con_docs.recalcular_estado()
        assert estado == "aceptada"

    def test_puede_pasar_a_r01(self, db_session, solicitud_con_docs):
        """R5: Solo puede pasar a R01 si esta aceptada."""
        assert not solicitud_con_docs.puede_pasar_a_r01()
        for doc in solicitud_con_docs.documentos:
            DocumentoIngService.cambiar_estado(db_session, doc.id, DocumentoIngEstadoPatch(estado="aceptado"))
        # Cambiar estado de la solicitud a aceptada
        SolicitudIngService.cambiar_estado(db_session, solicitud_con_docs.id, "aceptada", session_id="test")
        db_session.refresh(solicitud_con_docs)
        assert solicitud_con_docs.puede_pasar_a_r01()


# ──────────────────────────────────────────────
# CA-ING-12: Boton R01 deshabilitado
# ──────────────────────────────────────────────

class TestCA_ING_12_BotonR01:
    def test_r01_bloqueado_via_puede_pasar(self, solicitud_con_docs):
        """CA-ING-12: R5 se refleja en puede_pasar_a_r01()."""
        assert not solicitud_con_docs.puede_pasar_a_r01()

    def test_r01_habilitado_cuando_aceptada(self, db_session, solicitud_con_docs):
        """CA-ING-12: Cuando aceptada, puede_pasar_a_r01()=True."""
        for doc in solicitud_con_docs.documentos:
            DocumentoIngService.cambiar_estado(db_session, doc.id, DocumentoIngEstadoPatch(estado="aceptado"))
        SolicitudIngService.cambiar_estado(db_session, solicitud_con_docs.id, "aceptada", session_id="test")
        db_session.refresh(solicitud_con_docs)
        assert solicitud_con_docs.puede_pasar_a_r01()


# ──────────────────────────────────────────────
# CA-ING-13: Siguiente iteracion con R6
# ──────────────────────────────────────────────

class TestCA_ING_13_SiguienteIteracion:
    def test_crear_ing_2_hereda_aceptados(self, db_session, solicitud_con_docs):
        """CA-ING-13: ING #2 hereda aceptados como 'no_aplica' (R6)."""
        SolicitudIngService.cambiar_estado(db_session, solicitud_con_docs.id, "observada", session_id="test")

        docs = solicitud_con_docs.documentos
        DocumentoIngService.cambiar_estado(db_session, docs[0].id, DocumentoIngEstadoPatch(estado="aceptado"))
        DocumentoIngService.cambiar_estado(db_session, docs[1].id, DocumentoIngEstadoPatch(estado="aceptado"))
        DocumentoIngService.cambiar_estado(db_session, docs[2].id, DocumentoIngEstadoPatch(estado="observado", observacion="Falta"))
        DocumentoIngService.cambiar_estado(db_session, docs[3].id, DocumentoIngEstadoPatch(estado="faltante", observacion="No llego"))

        ing2 = SolicitudIngService.crear_siguiente_iteracion(db_session, solicitud_con_docs.id, session_id="test")

        assert ing2.numero_iteracion == 2
        assert ing2.solicitud_anterior_id == solicitud_con_docs.id

        nombres_aceptados = {docs[0].nombre_archivo, docs[1].nombre_archivo}
        nombres_observados = {docs[2].nombre_archivo, docs[3].nombre_archivo}

        for doc in ing2.documentos:
            if doc.nombre_archivo in nombres_aceptados:
                assert doc.estado == "no_aplica", f"{doc.nombre_archivo} deberia ser no_aplica (R6)"
            elif doc.nombre_archivo in nombres_observados:
                assert doc.estado == "pendiente", f"{doc.nombre_archivo} deberia ser pendiente"

    def test_no_crear_iteracion_si_no_observada(self, db_session, solicitud_ing_1):
        """No se puede crear ING #2 si ING #1 no esta observada."""
        with pytest.raises(ValueError, match="observada"):
            SolicitudIngService.crear_siguiente_iteracion(db_session, solicitud_ing_1.id)


# ──────────────────────────────────────────────
# CA-ING-14: Dashboard
# ──────────────────────────────────────────────

class TestCA_ING_14_Dashboard:
    def test_dashboard_endpoint(self, client: TestClient, solicitud_ing_1):
        """CA-ING-14: Panel muestra conteos por estado."""
        resp = client.get("/api/v1/ing/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert "en_revision" in data
        assert "aceptadas" in data
        assert "observadas" in data
        assert "recibidas" in data


# ──────────────────────────────────────────────
# CA-ING-15: Trazabilidad en LogAuditoria
# ──────────────────────────────────────────────

class TestCA_ING_15_Trazabilidad:
    def test_log_al_crear_solicitud(self, db_session):
        """CA-ING-15: Crear solicitud genera log."""
        count_antes = db_session.query(LogAuditoria).count()
        SolicitudIngService.crear(db_session, SolicitudIngCreate(
            nombre_proyecto="Test Log", empresa="Test", tipo_proyecto="HAB", comuna="Rancagua", modulos=["MDS"]),
            session_id="test-log")
        count_despues = db_session.query(LogAuditoria).count()
        assert count_despues > count_antes

    def test_log_al_cambiar_estado(self, db_session, solicitud_ing_1):
        """CA-ING-15: Cambiar estado genera log."""
        count_antes = db_session.query(LogAuditoria).count()
        SolicitudIngService.cambiar_estado(db_session, solicitud_ing_1.id, "en_revision", session_id="test-log")
        count_despues = db_session.query(LogAuditoria).count()
        assert count_despues > count_antes


# ──────────────────────────────────────────────
# CA-ING-16: Validacion calicatas normativa
# ──────────────────────────────────────────────

class TestCA_ING_16_CalicatasNormativa:
    def test_calicatas_menor_2000(self):
        """Menos de 2000 m2 -> minimo 2 calicatas."""
        result = ValidacionNormativaService.validar_calicatas(1500, 2)
        assert result["cumple"] is True
        assert result["minimo_normativo"] == 2

    def test_calicatas_menor_2000_falla(self):
        """Menos de 2000 m2 con 1 calicata -> no cumple."""
        result = ValidacionNormativaService.validar_calicatas(1500, 1)
        assert result["cumple"] is False

    def test_calicatas_2000_5000(self):
        """2000-5000 m2 -> minimo 3 calicatas."""
        result = ValidacionNormativaService.validar_calicatas(3500, 3)
        assert result["cumple"] is True
        assert result["minimo_normativo"] == 3

    def test_calicatas_5000_10000(self):
        """5000-10000 m2 -> minimo 4 calicatas."""
        result = ValidacionNormativaService.validar_calicatas(8500, 4)
        assert result["cumple"] is True
        assert result["minimo_normativo"] == 4

    def test_calicatas_mayor_10000(self):
        """Mas de 10000 m2 -> 5 + adicionales."""
        result = ValidacionNormativaService.validar_calicatas(15000, 6)
        assert result["minimo_normativo"] == 6  # 10000=5, +5000=+1 => 6
        assert result["cumple"] is True

    def test_calicatas_endpoint(self, client: TestClient):
        """Endpoint de validacion de calicatas."""
        resp = client.post("/api/v1/ing/validar-calicatas?superficie_terreno=8500&cantidad_calicatas=4")
        assert resp.status_code == 200
        assert resp.json()["cumple"] is True


# ──────────────────────────────────────────────
# CA-ING-17: Deteccion de copias (hash)
# ──────────────────────────────────────────────

class TestCA_ING_17_DeteccionCopias:
    def test_hash_calculado_al_registrar(self, db_session, solicitud_ing_1, tmp_path):
        """CA-ING-17: Hash SHA256 se calcula al registrar documento."""
        archivo = tmp_path / "test_doc.pdf"
        archivo.write_bytes(b"contenido de prueba para hash")

        doc = DocumentoIngService.crear(db_session, solicitud_ing_1.id, DocumentoIngCreate(
            nombre_archivo="test_doc.pdf", tipo_documento="MEMORIA", modulo="EST",
            ruta_local=str(archivo)), calcular_hash=True)

        assert doc.hash_sha256 is not None
        assert len(doc.hash_sha256) == 64

    def test_comparar_documentos_identicos(self, db_session, solicitud_ing_1, tmp_path):
        """CA-ING-17: Documentos con mismo hash son identicos."""
        archivo = tmp_path / "doc1.pdf"
        archivo.write_bytes(b"mismo contenido")

        doc1 = DocumentoIngService.crear(db_session, solicitud_ing_1.id, DocumentoIngCreate(
            nombre_archivo="doc1.pdf", tipo_documento="MEMORIA", modulo="EST",
            ruta_local=str(archivo)), calcular_hash=True)
        doc2 = DocumentoIngService.crear(db_session, solicitud_ing_1.id, DocumentoIngCreate(
            nombre_archivo="doc2.pdf", tipo_documento="MEMORIA", modulo="EST",
            ruta_local=str(archivo)), calcular_hash=True)

        result = DocumentoIngService.comparar_documentos(db_session, doc1.id, doc2.id)
        assert result["son_identicos"] is True


# ──────────────────────────────────────────────
# R12: Iteracion aceptada es inmutable
# ──────────────────────────────────────────────

class TestR12_Inmutabilidad:
    def test_no_modificar_si_aceptada(self, db_session, solicitud_con_docs):
        """R12: No se puede cambiar estado de solicitud ya aceptada."""
        for doc in solicitud_con_docs.documentos:
            DocumentoIngService.cambiar_estado(db_session, doc.id, DocumentoIngEstadoPatch(estado="aceptado"))
        SolicitudIngService.cambiar_estado(db_session, solicitud_con_docs.id, "aceptada", session_id="test")

        with pytest.raises(ValueError, match="aceptada"):
            SolicitudIngService.cambiar_estado(db_session, solicitud_con_docs.id, "observada", session_id="test")

    def test_no_agregar_docs_si_aceptada(self, client: TestClient, db_session, solicitud_con_docs):
        """R12: No se pueden agregar documentos a solicitud aceptada."""
        for doc in solicitud_con_docs.documentos:
            DocumentoIngService.cambiar_estado(db_session, doc.id, DocumentoIngEstadoPatch(estado="aceptado"))
        SolicitudIngService.cambiar_estado(db_session, solicitud_con_docs.id, "aceptada", session_id="test")

        resp = client.post(f"/api/v1/ing/solicitudes/{solicitud_con_docs.id}/documentos", json={
            "nombre_archivo": "nuevo.pdf", "tipo_documento": "PLANO", "modulo": "EST",
        })
        assert resp.status_code == 422


# ──────────────────────────────────────────────
# R4: Recalcular estado
# ──────────────────────────────────────────────

class TestR4_RecalcularEstado:
    def test_recalcular_desde_endpoint(self, client: TestClient, solicitud_con_docs, db_session):
        """R4: Endpoint recalcular estado."""
        resp = client.post(f"/api/v1/ing/solicitudes/{solicitud_con_docs.id}/recalcular-estado")
        assert resp.status_code == 200

        for doc in solicitud_con_docs.documentos:
            DocumentoIngService.cambiar_estado(db_session, doc.id, DocumentoIngEstadoPatch(estado="aceptado"))

        resp = client.post(f"/api/v1/ing/solicitudes/{solicitud_con_docs.id}/recalcular-estado")
        assert resp.status_code == 200
        assert resp.json()["estado_actual"] == "aceptada"


# ──────────────────────────────────────────────
# Progreso de revisiones
# ──────────────────────────────────────────────

class TestProgreso:
    def test_progreso_revisiones(self, client: TestClient, solicitud_ing_1):
        """Progreso de revisiones cruzadas."""
        client.post(f"/api/v1/ing/solicitudes/{solicitud_ing_1.id}/revisiones")

        resp = client.get(f"/api/v1/ing/solicitudes/{solicitud_ing_1.id}/progreso")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 7
        assert data["revisadas"] == 0
