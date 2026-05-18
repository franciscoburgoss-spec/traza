"""Tests unitarios para verificadores de muro de contencion HAB."""
import pytest
from app.core.verificadores.muro import (
    verificar_altura_muro,
    verificar_drenaje_muro,
    verificar_fc_muro,
    verificar_estabilidad_vuelco,
    verificar_muro_completo,
)


class TestAlturaMuro:
    """MURO-ALT-001: Verificacion de altura de muro."""

    def test_altura_cumple(self):
        """Altura 3.0m <= 4.0m -> CUMPLE."""
        r = verificar_altura_muro({"altura_muro": 3.0})
        assert r.resultado == "CUMPLE"
        assert r.severidad == "INFO"

    def test_altura_warning(self):
        """Altura 4.5m -> WARNING (> 4.0m)."""
        r = verificar_altura_muro({"altura_muro": 4.5})
        assert r.resultado == "NO_CUMPLE"
        assert r.severidad == "WARNING"

    def test_altura_error(self):
        """Altura 7.0m -> ERROR (> 6.0m)."""
        r = verificar_altura_muro({"altura_muro": 7.0})
        assert r.resultado == "NO_CUMPLE"
        assert r.severidad == "ERROR"

    def test_altura_limite_4m(self):
        """Altura exactamente 4.0m -> CUMPLE."""
        r = verificar_altura_muro({"altura_muro": 4.0})
        assert r.resultado == "CUMPLE"

    def test_sin_altura(self):
        """Sin dato de altura -> SIN_EVIDENCIA."""
        r = verificar_altura_muro({})
        assert r.resultado == "SIN_EVIDENCIA"


class TestDrenajeMuro:
    """MURO-DRE-001: Verificacion de drenaje de muro."""

    def test_drenaje_ok_altura_baja(self):
        """Altura 1.5m sin drenaje -> CUMPLE (no requiere)."""
        r = verificar_drenaje_muro({"altura_muro": 1.5, "tiene_drenaje": False})
        assert r.resultado == "CUMPLE"

    def test_drenaje_ok_con_drenaje(self):
        """Altura 3.0m con drenaje -> CUMPLE."""
        r = verificar_drenaje_muro({"altura_muro": 3.0, "tiene_drenaje": True})
        assert r.resultado == "CUMPLE"

    def test_drenaje_falla(self):
        """Altura 3.0m sin drenaje -> ERROR."""
        r = verificar_drenaje_muro({"altura_muro": 3.0, "tiene_drenaje": False})
        assert r.resultado == "NO_CUMPLE"
        assert r.severidad == "ERROR"

    def test_drenaje_limite_2m(self):
        """Altura 2.0m sin drenaje -> CUMPLE (limite no excluyente)."""
        r = verificar_drenaje_muro({"altura_muro": 2.0, "tiene_drenaje": False})
        assert r.resultado == "CUMPLE"


class TestFcmuro:
    """MURO-FC-001: Verificacion de resistencia del hormigon."""

    def test_fc_cumple(self):
        """fc = 25 MPa >= 20 MPa -> CUMPLE."""
        r = verificar_fc_muro({"fc": 25.0})
        assert r.resultado == "CUMPLE"

    def test_fc_falla(self):
        """fc = 15 MPa < 20 MPa -> ERROR."""
        r = verificar_fc_muro({"fc": 15.0})
        assert r.resultado == "NO_CUMPLE"
        assert r.severidad == "ERROR"

    def test_fc_exacto_20(self):
        """fc = 20 MPa exacto -> CUMPLE."""
        r = verificar_fc_muro({"fc": 20.0})
        assert r.resultado == "CUMPLE"

    def test_fc_sin_dato(self):
        """Sin fc -> SIN_EVIDENCIA."""
        r = verificar_fc_muro({})
        assert r.resultado == "SIN_EVIDENCIA"


class TestEstabilidadVuelco:
    """MURO-VOL-001: Verificacion de estabilidad al vuelco."""

    def test_fos_cumple(self):
        """FOS = 1.8 >= 1.5 -> CUMPLE."""
        r = verificar_estabilidad_vuelco({"fos_vuelco": 1.8})
        assert r.resultado == "CUMPLE"
        assert r.severidad == "INFO"

    def test_fos_falla(self):
        """FOS = 1.2 < 1.3 -> CRITICAL."""
        r = verificar_estabilidad_vuelco({"fos_vuelco": 1.2})
        assert r.resultado == "NO_CUMPLE"
        assert r.severidad == "CRITICAL"

    def test_fos_exacto_15(self):
        """FOS = 1.5 exacto -> CUMPLE."""
        r = verificar_estabilidad_vuelco({"fos_vuelco": 1.5})
        assert r.resultado == "CUMPLE"

    def test_fos_warning(self):
        """FOS = 1.4 -> WARNING (entre 1.3 y 1.5)."""
        r = verificar_estabilidad_vuelco({"fos_vuelco": 1.4})
        assert r.resultado == "NO_CUMPLE"
        assert r.severidad == "WARNING"

    def test_fos_sin_dato(self):
        """Sin FOS -> SIN_EVIDENCIA."""
        r = verificar_estabilidad_vuelco({})
        assert r.resultado == "SIN_EVIDENCIA"
        assert r.severidad == "CRITICAL"


class TestMuroCompleto:
    """Verificacion completa de muro."""

    def test_muro_perfecto(self):
        """Todos los parametros cumplen -> 4x CUMPLE."""
        datos = {
            "altura_muro": 3.0,
            "tiene_drenaje": True,
            "fc": 25.0,
            "fos_vuelco": 1.8,
        }
        resultados = verificar_muro_completo(datos)
        assert len(resultados) == 4
        assert all(r.resultado == "CUMPLE" for r in resultados)

    def test_muro_deficiente(self):
        """Todos los parametros fallan -> al menos algunos NO_CUMPLE."""
        datos = {
            "altura_muro": 7.0,
            "tiene_drenaje": False,
            "fc": 15.0,
            "fos_vuelco": 1.2,
        }
        resultados = verificar_muro_completo(datos)
        assert all(r.resultado == "NO_CUMPLE" for r in resultados)

    def test_muro_datos_incompletos(self):
        """Datos incompletos -> resultados parciales sin crash."""
        resultados = verificar_muro_completo({})
        assert len(resultados) == 4
        # Algunos son SIN_EVIDENCIA
        assert any(r.resultado == "SIN_EVIDENCIA" for r in resultados)
