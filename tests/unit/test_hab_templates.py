"""Tests unitarios para plantillas HAB."""
import pytest
from app.core.hab_templates import render_hab_html, PLANTILLA_MURO, PLANTILLA_CALETERA


class TestRenderHABMuro:
    """Tests de renderizado de HAB para muro de contencion."""

    def test_render_muro_completo(self):
        datos = PLANTILLA_MURO.copy()
        datos["altura_muro"] = 3.0
        datos["fc"] = 25.0
        datos["tiene_drenaje"] = True
        html = render_hab_html("muro", datos)
        assert html is not None
        assert len(html) > 100
        assert "Muro de contencion" in html or "hab-muro" in html

    def test_render_muro_datos_incompletos_no_crash(self):
        """Renderizar con datos incompletos no debe fallar."""
        html = render_hab_html("muro", {})
        assert html is not None
        assert isinstance(html, str)


class TestRenderHABCaletera:
    """Tests de renderizado de HAB para caletera."""

    def test_render_caletera_completa(self):
        datos = PLANTILLA_CALETERA.copy()
        datos["longitud_caletera"] = 50.0
        datos["ancho_corona"] = 4.0
        html = render_hab_html("caletera", datos)
        assert html is not None
        assert len(html) > 100
        assert "Caletera" in html or "hab-caletera" in html

    def test_render_caletera_datos_incompletos_no_crash(self):
        html = render_hab_html("caletera", {})
        assert html is not None
        assert isinstance(html, str)


class TestRenderTipoInvalido:
    """Tests de manejo de tipo invalido."""

    def test_tipo_invalido_lanza_error(self):
        """Tipo invalido debe lanzar ValueError."""
        with pytest.raises(ValueError):
            render_hab_html("tipo_inexistente", {})

    def test_tipo_case_sensitive(self):
        """Los tipos son case sensitive."""
        with pytest.raises(ValueError):
            render_hab_html("MURO", {})
        with pytest.raises(ValueError):
            render_hab_html("Caletera", {})
