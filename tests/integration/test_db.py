"""Tests de integracion con base de datos."""
import pytest
from sqlalchemy.exc import IntegrityError
from app.models import Proyecto, Documento, Evidencia, Dictamen, LogAuditoria


class TestProyectoCRUD:
    """CRUD basico de Proyecto."""

    def test_crear_proyecto(self, db_session):
        p = Proyecto(codigo="DB-TEST-001", nombre="Test DB", tipo_proyecto="CNT")
        db_session.add(p)
        db_session.commit()
        assert p.id is not None
        assert p.estado == "ACTIVO"

    def test_codigo_unico(self, db_session):
        p1 = Proyecto(codigo="UNIQUE-001", nombre="Primero")
        db_session.add(p1)
        db_session.commit()

        p2 = Proyecto(codigo="UNIQUE-001", nombre="Duplicado")
        db_session.add(p2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_listar_proyectos(self, db_session, sample_proyecto):
        proyectos = db_session.query(Proyecto).all()
        assert len(proyectos) >= 1

    def test_estado_default(self, db_session):
        p = Proyecto(codigo="DEFAULT-001", nombre="Estado Default")
        db_session.add(p)
        db_session.commit()
        assert p.estado == "ACTIVO"


class TestDocumentoCRUD:
    """CRUD de Documento vinculado a Proyecto."""

    def test_crear_documento(self, db_session, sample_proyecto):
        d = Documento(
            proyecto_id=sample_proyecto.id,
            nombre_archivo="test.pdf",
            modulo="EST",
        )
        db_session.add(d)
        db_session.commit()
        assert d.id is not None
        assert d.extraccion_estado == "PENDIENTE"

    def test_documento_sin_proyecto(self, db_session):
        """Documento con proyecto_id inexistente falla por FK."""
        d = Documento(
            proyecto_id="no-existe",
            nombre_archivo="test.pdf",
            modulo="EST",
        )
        db_session.add(d)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()


class TestEvidenciaCRUD:
    """CRUD de Evidencia vinculada a Documento."""

    def test_crear_evidencia(self, db_session, sample_documento):
        e = Evidencia(
            documento_id=sample_documento.id,
            campo="altura_muro",
            valor="3.5",
            extractor="manual",
        )
        db_session.add(e)
        db_session.commit()
        assert e.id is not None
        assert e.confidence == 1.0  # default

    def test_validacion_evidencia(self, db_session, sample_evidencia):
        assert sample_evidencia.validada_manual is True


class TestDictamenCRUD:
    """CRUD de Dictamen."""

    def test_crear_dictamen(self, db_session, sample_proyecto):
        d = Dictamen(
            proyecto_id=sample_proyecto.id,
            score=75.0,
            estado="EN_PROCESO",
        )
        db_session.add(d)
        db_session.commit()
        assert d.id is not None
        assert d.editable is True  # default

    def test_dictamen_unico_por_proyecto(self, db_session, sample_proyecto):
        d1 = Dictamen(proyecto_id=sample_proyecto.id, score=50.0)
        db_session.add(d1)
        db_session.commit()

        d2 = Dictamen(proyecto_id=sample_proyecto.id, score=80.0)
        db_session.add(d2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()


class TestLogAuditoria:
    """Logs de auditoria."""

    def test_crear_log(self, db_session, sample_proyecto):
        log = LogAuditoria(
            entidad_tipo="proyecto",
            entidad_id=sample_proyecto.id,
            accion="CREAR",
            detalle_json='{"codigo": "RM-2026-0001"}',
            session_id="test-session-001",
        )
        db_session.add(log)
        db_session.commit()
        assert log.id is not None

    def test_logs_por_session(self, db_session):
        for i in range(3):
            log = LogAuditoria(
                entidad_tipo="proyecto",
                entidad_id=f"test-{i}",
                accion="CREAR",
                session_id="session-abc",
            )
            db_session.add(log)
        db_session.commit()

        logs = db_session.query(LogAuditoria).filter_by(session_id="session-abc").all()
        assert len(logs) == 3
