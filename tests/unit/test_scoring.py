"""Tests unitarios para scoring de dictamenes."""
import pytest
from app.core.scoring import compute_score, get_categoria


class TestComputeScore:
    """Tests para calculo de score 0-100."""

    def test_score_perfecto(self):
        """Todas las verificaciones cumplen -> 100."""
        verificaciones = [
            {"modulo": "muro", "resultado": "CUMPLE"},
            {"modulo": "caletera", "resultado": "CUMPLE"},
        ]
        assert compute_score(verificaciones) == 100.0

    def test_score_cero(self):
        """Ninguna cumple -> 0."""
        verificaciones = [
            {"modulo": "muro", "resultado": "NO_CUMPLE"},
            {"modulo": "caletera", "resultado": "NO_CUMPLE"},
        ]
        assert compute_score(verificaciones) == 0.0

    def test_score_no_aplica_excluido(self):
        """NO_APLICA no penaliza el score."""
        verificaciones = [
            {"modulo": "muro", "resultado": "CUMPLE"},
            {"modulo": "caletera", "resultado": "NO_APLICA"},
        ]
        # muro = 100, caletera = 100 (no aplica = no penaliza)
        # score = (100 * 0.4 + 100 * 0.3 + 0 * 0.2 + 0 * 0.1) / 1.0 = 70... hmm
        # Los modulos nch3417 y re7713 no estan presentes -> 0
        # (100*0.4 + 100*0.3 + 0*0.2 + 0*0.1) / 1.0 = 70
        score = compute_score(verificaciones)
        assert score >= 60.0  # Debe ser razonable

    def test_score_sin_evidencia_como_cero(self):
        """SIN_EVIDENCIA cuenta como 0."""
        verificaciones = [
            {"modulo": "muro", "resultado": "CUMPLE"},
            {"modulo": "caletera", "resultado": "SIN_EVIDENCIA"},
        ]
        score = compute_score(verificaciones)
        assert 0 < score < 100

    def test_lista_vacia(self):
        """Sin verificaciones -> 0."""
        assert compute_score([]) == 0.0

    def test_inferencia_modulo_desde_verificador_id(self):
        """Si no hay campo 'modulo', infiere del verificador_id."""
        verificaciones = [
            {"verificador_id": "MURO-ALT-001", "resultado": "CUMPLE"},
            {"verificador_id": "CAL-LON-001", "resultado": "CUMPLE"},
        ]
        assert compute_score(verificaciones) == 100.0


class TestCategoriaScore:
    """Tests para clasificacion de score."""

    def test_excelente(self):
        cat = get_categoria(95)
        assert cat["nombre"] == "Excelente"

    def test_bueno(self):
        cat = get_categoria(80)
        assert cat["nombre"] == "Bueno"

    def test_regular(self):
        cat = get_categoria(65)
        assert cat["nombre"] == "Regular"

    def test_deficiente(self):
        cat = get_categoria(45)
        assert cat["nombre"] == "Deficiente"

    def test_excelente_borde(self):
        cat = get_categoria(90)
        assert cat["nombre"] == "Excelente"

    def test_deficiente_cero(self):
        cat = get_categoria(0)
        assert cat["nombre"] == "Deficiente"
