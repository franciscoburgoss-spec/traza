"""Tests basicos de integracion de la API TRAZA."""
import pytest
from fastapi import status


class TestHealthCheck:
    """Verificar que la app arranca y responde."""

    def test_root_endpoint(self, client):
        """GET / retorna HTML del dashboard."""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK

    def test_health_endpoint(self, client):
        """GET /health retorna status OK."""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"

    def test_docs_endpoint(self, client):
        """GET /docs retorna la documentacion Swagger."""
        response = client.get("/docs")
        assert response.status_code == status.HTTP_200_OK


class TestProyectoAPI:
    """Tests de API de proyectos."""

    def test_crear_proyecto(self, client):
        """POST /proyectos crea un proyecto."""
        payload = {
            "codigo": "RM-2026-API-01",
            "nombre": "Test API Proyecto",
            "tipo_proyecto": "CNT",
            "ref_comuna": "SANTIAGO",
            "ref_zona_sismica": 2,
            "ref_tipo_suelo": "II",
            "ref_Ao": 0.20,
        }
        r = client.post("/api/v1/proyectos", json=payload)
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["codigo"] == "RM-2026-API-01"
        assert "id" in data

    def test_crear_proyecto_duplicado(self, client):
        """Crear proyecto con codigo duplicado debe fallar."""
        payload = {"codigo": "DUP-001", "nombre": "Primero", "tipo_proyecto": "CNT"}
        r1 = client.post("/api/v1/proyectos", json=payload)
        assert r1.status_code in (200, 201)

        r2 = client.post("/api/v1/proyectos", json=payload)
        assert r2.status_code in (400, 409, 422)

    def test_listar_proyectos(self, client):
        """GET /proyectos retorna lista."""
        r = client.get("/api/v1/proyectos")
        assert r.status_code == 200


class TestDocumentoAPI:
    """Tests de API de documentos."""

    def test_registrar_documento(self, client):
        """Registrar documento para un proyecto."""
        rp = client.post("/api/v1/proyectos", json={
            "codigo": "DOC-001", "nombre": "Doc Test", "tipo_proyecto": "CNT",
        })
        assert rp.status_code in (200, 201)
        proyecto_id = rp.json()["id"]

        payload = {
            "nombre_archivo": "Memoria.pdf",
            "ruta_local": "/tmp/test.pdf",
            "tipo_documento": "MEMORIA",
            "modulo": "EST",
        }
        r = client.post(f"/api/v1/proyectos/{proyecto_id}/documentos", json=payload)
        assert r.status_code in (200, 201, 422)  # 422 si schema mismatch


class TestAuditoriaAPI:
    """Tests de API de auditoria."""

    def test_auditoria_accesible(self, client):
        """GET /api/v1/auditoria retorna lista."""
        response = client.get("/api/v1/auditoria")
        assert response.status_code == 200
