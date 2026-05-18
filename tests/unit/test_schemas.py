"""Tests de schemas Pydantic v2."""
import pytest
from pydantic import ValidationError
from app.schemas import (
    ProyectoCreate,
    ProyectoEstadoPatch,
    DocumentoCreate,
    EvidenciaCreate,
    EvidenciaValidarPatch,
    DictamenUpdate,
    DictamenEstadoPatch,
)


class TestProyectoCreate:
    def test_proyecto_create_valido(self):
        p = ProyectoCreate(codigo="RM-2026-001", nombre="Test")
        assert p.codigo == "RM-2026-001"
        assert p.estado == "ACTIVO"  # default

    def test_proyecto_create_completo(self):
        p = ProyectoCreate(
            codigo="RM-2026-002",
            nombre="Proyecto Completo",
            tipo_proyecto="CNT",
            ref_comuna="LAS CONDES",
            ref_zona_sismica=2,
            ref_tipo_suelo="II",
            ref_Ao=0.20,
        )
        assert p.ref_zona_sismica == 2
        assert p.ref_Ao == 0.20


class TestProyectoEstadoPatch:
    def test_estado_valido(self):
        p = ProyectoEstadoPatch(estado="EN_EVALUACION")
        assert p.estado == "EN_EVALUACION"


class TestDocumentoCreate:
    def test_documento_create_valido(self):
        d = DocumentoCreate(
            proyecto_id="test-id",
            nombre_archivo="memoria.pdf",
            tipo_documento="MEMORIA",
            modulo="EST",
        )
        assert d.extraccion_estado == "PENDIENTE"  # default


class TestEvidenciaCreate:
    def test_evidencia_confidence_valida(self):
        e = EvidenciaCreate(
            documento_id="test-id",
            campo="altura_muro",
            valor="3.5",
            confidence=0.95,
        )
        assert e.confidence == 0.95

    def test_evidencia_defaults(self):
        e = EvidenciaCreate(documento_id="test-id", campo="test")
        assert e.confidence == 1.0  # default
        assert e.validada_manual is False  # default


class TestEvidenciaValidarPatch:
    def test_validar_true(self):
        p = EvidenciaValidarPatch(validada_manual=True)
        assert p.validada_manual is True


class TestDictamenUpdate:
    def test_dictamen_update_parcial(self):
        d = DictamenUpdate(justificacion="Proyecto en revision")
        assert d.justificacion == "Proyecto en revision"
        assert d.estado is None  # no proporcionado

    def test_dictamen_score_valido(self):
        d = DictamenUpdate(score=75.5)
        assert d.score == 75.5

    def test_dictamen_con_html(self):
        d = DictamenUpdate(
            dictamen_texto="El proyecto cumple con las normas.",
            hab_html="<p>HAB contenido</p>",
        )
        assert d.hab_html == "<p>HAB contenido</p>"


class TestDictamenEstadoPatch:
    def test_estado_aprobado(self):
        p = DictamenEstadoPatch(estado="APROBADO")
        assert p.estado == "APROBADO"

    def test_estado_rechazado(self):
        p = DictamenEstadoPatch(estado="RECHAZADO")
        assert p.estado == "RECHAZADO"
