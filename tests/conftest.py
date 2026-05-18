"""Pytest fixtures for TRAZA test suite."""
import os
import sys
import uuid
import tempfile
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---------------------------------------------------------------------------
# Test database: shared temp file that both app and fixtures use
# ---------------------------------------------------------------------------

TEST_DB_FD, TEST_DB_PATH = tempfile.mkstemp(suffix=".db")
os.close(TEST_DB_FD)
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"

# Override settings BEFORE importing app
from app import config
config.settings.DATABASE_URL = TEST_DATABASE_URL

from app.database import Base, get_db, init_db, engine as app_engine

# Recreate app engine with test DB
_test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

@event.listens_for(_test_engine, "connect")
def _enable_fk(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()

# Replace app's engine
app_engine.dispose()
from app import database as db_module
db_module.engine = _test_engine
db_module.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)

# Create tables
Base.metadata.create_all(bind=_test_engine)
init_db()

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh DB session for each test, clearing all tables."""
    # Clear all tables for test isolation — delete in dependency order (children first)
    # For self-referencing FKs (solicitud_ing.solicitud_anterior_id), delete children first
    from sqlalchemy import text
    with _test_engine.begin() as conn:
        # Disable FK checks just for cleanup, then re-enable
        conn.execute(text("PRAGMA foreign_keys = OFF"))
        conn.execute(text("DELETE FROM revision_cruzada"))
        conn.execute(text("DELETE FROM documento_ing"))
        conn.execute(text("DELETE FROM solicitud_ing"))
        conn.execute(text("DELETE FROM tabla_calicatas_minimas"))
        conn.execute(text("DELETE FROM LogAuditoria"))
        conn.execute(text("DELETE FROM Dictamen"))
        conn.execute(text("DELETE FROM Verificacion"))
        conn.execute(text("DELETE FROM Evidencia"))
        conn.execute(text("DELETE FROM Documento"))
        conn.execute(text("DELETE FROM Proyecto"))
        conn.execute(text("PRAGMA foreign_keys = ON"))
    session = TestSessionLocal()
    # Ensure FK constraints are enabled for this session
    session.execute(text("PRAGMA foreign_keys = ON"))
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Create a TestClient with DB overridden."""
    from fastapi.testclient import TestClient
    from app.main import app

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_proyecto(db_session):
    """Create a sample proyecto."""
    from app.models import Proyecto
    p = Proyecto(
        codigo="RM-2026-0001",
        nombre="Proyecto Test TRAZA",
        tipo_proyecto="CNT",
        ref_comuna="LAS CONDES",
        ref_zona_sismica=2,
        ref_tipo_suelo="II",
        ref_Ao=0.20,
        estado="ACTIVO",
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


@pytest.fixture
def sample_documento(db_session, sample_proyecto):
    """Create a sample documento."""
    from app.models import Documento
    d = Documento(
        proyecto_id=sample_proyecto.id,
        modulo="EST",
        tipo_documento="MEMORIA",
        nombre_archivo="memoria_calculo.pdf",
        ruta_local="/tmp/test_memoria.pdf",
        extraccion_estado="PENDIENTE",
    )
    db_session.add(d)
    db_session.commit()
    db_session.refresh(d)
    return d


@pytest.fixture
def sample_evidencia(db_session, sample_documento):
    """Create a sample evidencia."""
    from app.models import Evidencia
    e = Evidencia(
        documento_id=sample_documento.id,
        campo="zona_sismica",
        valor="2",
        valor_tipo="NUMERIC",
        extractor="seismic_params",
        confidence=0.95,
        validada_manual=True,
    )
    db_session.add(e)
    db_session.commit()
    db_session.refresh(e)
    return e
