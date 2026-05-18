"""Tests unitarios para verificadores de caletera HAB."""
import pytest
from app.core.verificadores.caletera import (
    verificar_longitud_minima,
    verificar_ancho_corona,
    verificar_pendiente_maxima,
    verificar_espesor_minimo,
    verificar_caletera_completo,
)


class TestLongitudCaletera:
    """CAL-LON-001: Verificacion de longitud minima."""

    def test_longitud_cumple(self):
        r = verificar_longitud_minima({"longitud_caletera": 50.0})
        assert r.resultado == "CUMPLE"

    def test_longitud_falla(self):
        r = verificar_longitud_minima({"longitud_caletera": 10.0})
        assert r.resultado == "NO_CUMPLE"

    def test_longitud_exacto_20(self):
        r = verificar_longitud_minima({"longitud_caletera": 20.0})
        assert r.resultado == "CUMPLE"

    def test_longitud_sin_dato(self):
        r = verificar_longitud_minima({})
        assert r.resultado == "SIN_EVIDENCIA"


class TestAnchoCorona:
    """CAL-ANC-001: Verificacion de ancho de corona."""

    def test_ancho_cumple(self):
        r = verificar_ancho_corona({"ancho_corona": 4.0})
        assert r.resultado == "CUMPLE"

    def test_ancho_warning(self):
        """2.5 <= ancho < 3.0 -> WARNING."""
        r = verificar_ancho_corona({"ancho_corona": 2.7})
        assert r.resultado == "NO_CUMPLE"
        assert r.severidad == "WARNING"

    def test_ancho_falla(self):
        r = verificar_ancho_corona({"ancho_corona": 2.0})
        assert r.resultado == "NO_CUMPLE"
        assert r.severidad == "ERROR"

    def test_ancho_sin_dato(self):
        r = verificar_ancho_corona({})
        assert r.resultado == "SIN_EVIDENCIA"


class TestPendienteMaxima:
    """CAL-PEN-001: Verificacion de pendiente longitudinal."""

    def test_pendiente_cumple(self):
        r = verificar_pendiente_maxima({"pendiente": 5.0})
        assert r.resultado == "CUMPLE"

    def test_pendiente_warning(self):
        """8% < pendiente <= 12% -> WARNING."""
        r = verificar_pendiente_maxima({"pendiente": 10.0})
        assert r.resultado == "NO_CUMPLE"
        assert r.severidad == "WARNING"

    def test_pendiente_error(self):
        """pendiente > 12% -> ERROR."""
        r = verificar_pendiente_maxima({"pendiente": 15.0})
        assert r.resultado == "NO_CUMPLE"
        assert r.severidad == "ERROR"

    def test_pendiente_exacto_8(self):
        r = verificar_pendiente_maxima({"pendiente": 8.0})
        assert r.resultado == "CUMPLE"

    def test_pendiente_sin_dato(self):
        r = verificar_pendiente_maxima({})
        assert r.resultado == "SIN_EVIDENCIA"


class TestEspesorMinimo:
    """CAL-ESP-001: Verificacion de espesor de capa."""

    def test_espesor_cumple(self):
        r = verificar_espesor_minimo({"espesor": 20.0})
        assert r.resultado == "CUMPLE"

    def test_espesor_warning(self):
        """10 <= espesor < 15 -> WARNING."""
        r = verificar_espesor_minimo({"espesor": 12.0})
        assert r.resultado == "NO_CUMPLE"
        assert r.severidad == "WARNING"

    def test_espesor_error(self):
        r = verificar_espesor_minimo({"espesor": 8.0})
        assert r.resultado == "NO_CUMPLE"
        assert r.severidad == "ERROR"

    def test_espesor_exacto_15(self):
        r = verificar_espesor_minimo({"espesor": 15.0})
        assert r.resultado == "CUMPLE"

    def test_espesor_sin_dato(self):
        r = verificar_espesor_minimo({})
        assert r.resultado == "SIN_EVIDENCIA"


class TestCaleteraCompleta:
    """Verificacion completa de caletera."""

    def test_caletera_perfecta(self):
        datos = {
            "longitud_caletera": 50.0,
            "ancho_corona": 4.0,
            "pendiente": 5.0,
            "espesor": 20.0,
        }
        resultados = verificar_caletera_completo(datos)
        assert len(resultados) == 4
        assert all(r.resultado == "CUMPLE" for r in resultados)

    def test_caletera_deficiente(self):
        datos = {
            "longitud_caletera": 10.0,
            "ancho_corona": 2.0,
            "pendiente": 15.0,
            "espesor": 5.0,
        }
        resultados = verificar_caletera_completo(datos)
        assert all(r.resultado == "NO_CUMPLE" for r in resultados)

    def test_caletera_datos_incompletos(self):
        resultados = verificar_caletera_completo({})
        assert len(resultados) == 4
        assert any(r.resultado == "SIN_EVIDENCIA" for r in resultados)
