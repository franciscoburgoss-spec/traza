"""
Verificador de R.E. 7713 - Itemizacion tecnica de proyectos de vivienda social.

La R.E. 7713 de FRANCISCO BURGOS S. establece los requisitos de itemizacion tecnica
para proyectos de vivienda social FSEV. Este verificador ejecuta ~15 checks
sobre el texto de la memoria de calculo para validar que contenga los
elementos de itemizacion requeridos.

Checks realizados:
  1: Itemizacion completa presente
  2: Antecedentes generales del proyecto
  3: Descripcion de la estructura
  4: Suelo y cimentacion
  5: Muros y cerramientos
  6: Techumbre y cubierta
  7: Instalaciones (sanitario, electrico, gas)
  8: Pavimentos exteriores y caletas
  9: Muros de contencion
  10: Accesibilidad universal
  11: Sustentabilidad y eficiencia energetica
  12: Especificaciones tecnicas de materiales
  13: Presupuesto itemizado
  14: Planos de conjunto y detalles
  15: Programa de construccion
"""

import re
import logging

from .base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


class RE7713Extractor(BaseExtractor):
    """Verifica cumplimiento de R.E. 7713 (itemizacion tecnica FRANCISCO BURGOS S.).

    Esta resolucion exige que los proyectos FSEV presenten una itemizacion
tecnica completa. Este extractor verifica la existencia de las secciones
    requeridas en la memoria de calculo y/o documentacion tecnica.
    """

    EXTRACTOR_NAME: str = "RE7713Extractor"
    NORMA: str = "R.E. 7713"

    def can_extract(self, file_path: str) -> bool:
        """Siempre True: trabaja sobre texto."""
        return True

    def extract(self, file_path: str) -> ExtractionResult:
        """Ejecuta los ~15 checks de R.E. 7713.

        Args:
            file_path: Ruta a archivo de texto, o texto directo.

        Returns:
            ExtractionResult con structured_data = {
                "checks": list[dict],
                "checks_aprobados": int,
                "checks_fallidos": int,
                "score_porcentaje": float,
            }
        """
        import os

        if os.path.isfile(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
            except UnicodeDecodeError:
                with open(file_path, "r", encoding="latin-1") as f:
                    text = f.read()
            except Exception as e:
                return self._error_result(f"Error leyendo archivo: {e}")
        else:
            text = file_path

        return self.extract_from_text(text)

    def extract_from_text(self, text: str) -> ExtractionResult:
        """Ejecuta los checks sobre el texto directamente.

        Args:
            text: Texto de la memoria de calculo o documentacion tecnica.

        Returns:
            ExtractionResult con resultado consolidado.
        """
        if not text or not isinstance(text, str):
            return self._error_result("Texto vacio o invalido")

        checks = self._ejecutar_checks(text)
        checks_aprobados = sum(1 for c in checks if c["cumple"])
        checks_fallidos = len(checks) - checks_aprobados
        score_porcentaje = round((checks_aprobados / len(checks)) * 100, 1) if checks else 0.0

        if score_porcentaje >= 80:
            confidence = 0.9
        elif score_porcentaje >= 50:
            confidence = 0.6
        else:
            confidence = 0.3

        structured_data = {
            "norma": self.NORMA,
            "checks": checks,
            "checks_aprobados": checks_aprobados,
            "checks_fallidos": checks_fallidos,
            "total_checks": len(checks),
            "score_porcentaje": score_porcentaje,
        }

        return ExtractionResult(
            raw_text=text[:500] if len(text) > 500 else text,
            structured_data=structured_data,
            confidence=confidence,
            extractor_name=self.EXTRACTOR_NAME,
            page_count=0,
            metadata={
                "checks_criticos_fallidos": sum(
                    1 for c in checks if not c["cumple"] and c["severidad"] == "ERROR"
                ),
            },
        )

    def _ejecutar_checks(self, text: str) -> list[dict]:
        """Ejecuta los 15 checks de itemizacion R.E. 7713.

        Args:
            text: Texto de la documentacion tecnica.

        Returns:
            Lista de dicts con resultado de cada check.
        """
        checks = []

        # Check 1: Itemizacion completa presente
        checks.append(self._check_itemizacion_completa(text))

        # Check 2: Antecedentes generales
        checks.append(self._check_antecedentes(text))

        # Check 3: Descripcion de la estructura
        checks.append(self._check_descripcion_estructura(text))

        # Check 4: Suelo y cimentacion
        checks.append(self._check_suelo_cimentacion(text))

        # Check 5: Muros y cerramientos
        checks.append(self._check_muros_cerramientos(text))

        # Check 6: Techumbre y cubierta
        checks.append(self._check_techumbre(text))

        # Check 7: Instalaciones
        checks.append(self._check_instalaciones(text))

        # Check 8: Pavimentos exteriores y caletas
        checks.append(self._check_pavimentos_caletas(text))

        # Check 9: Muros de contencion
        checks.append(self._check_muros_contencion(text))

        # Check 10: Accesibilidad universal
        checks.append(self._check_accesibilidad(text))

        # Check 11: Sustentabilidad
        checks.append(self._check_sustentabilidad(text))

        # Check 12: Especificaciones tecnicas de materiales
        checks.append(self._check_especificaciones_materiales(text))

        # Check 13: Presupuesto itemizado
        checks.append(self._check_presupuesto(text))

        # Check 14: Planos de conjunto y detalles
        checks.append(self._check_planos(text))

        # Check 15: Programa de construccion
        checks.append(self._check_programa_construccion(text))

        return checks

    # ------------------------------------------------------------------
    # Checks individuales
    # ------------------------------------------------------------------

    def _check_itemizacion_completa(self, text: str) -> dict:
        """Check 1: Itemizacion completa presente."""
        patrones = [
            r"(itemizaci[oó]n)",
            r"(ítems?\s+t[ée]cnicos?)",
            r"(partidas?\s+t[ée]cnicas?)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "RE7713-001",
            "descripcion": "Itemizacion tecnica completa",
            "cumple": encontrado,
            "severidad": "ERROR" if not encontrado else "INFO",
            "mensaje": (
                "Se detecta itemizacion tecnica." if encontrado
                else "No se detecta itemizacion tecnica. Obligatoria segun R.E. 7713."
            ),
        }

    def _check_antecedentes(self, text: str) -> dict:
        """Check 2: Antecedentes generales del proyecto."""
        patrones = [
            r"(antecedentes\s+generales)",
            r"(datos\s+generales)",
            r"(identificaci[oó]n\s+del\s+proyecto)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "RE7713-002",
            "descripcion": "Antecedentes generales del proyecto",
            "cumple": encontrado,
            "severidad": "ERROR" if not encontrado else "INFO",
            "mensaje": (
                "Se detectan antecedentes generales." if encontrado
                else "No se detectan antecedentes generales. Item obligatorio R.E. 7713."
            ),
        }

    def _check_descripcion_estructura(self, text: str) -> dict:
        """Check 3: Descripcion de la estructura."""
        patrones = [
            r"(descripci[oó]n\s+de\s+la\s+estructura)",
            r"(tipolog[ií]a\s+estructural)",
            r"(sistema\s+constructivo)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "RE7713-003",
            "descripcion": "Descripcion de la estructura",
            "cumple": encontrado,
            "severidad": "ERROR" if not encontrado else "INFO",
            "mensaje": (
                "Se detecta descripcion de la estructura." if encontrado
                else "No se detecta descripcion de la estructura. Item obligatorio R.E. 7713."
            ),
        }

    def _check_suelo_cimentacion(self, text: str) -> dict:
        """Check 4: Suelo y cimentacion."""
        patrones = [
            r"(estudio\s+de\s+suelo)",
            r"(cimentaci[oó]n)",
            r"(geotecnia)",
            r"(mec[áa]nica\s+de\s+suelos)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "RE7713-004",
            "descripcion": "Suelo y cimentacion (estudio geotecnico)",
            "cumple": encontrado,
            "severidad": "ERROR" if not encontrado else "INFO",
            "mensaje": (
                "Se detecta informacion de suelo/cimentacion." if encontrado
                else "No se detecta estudio de suelo ni cimentacion. Obligatorio segun R.E. 7713."
            ),
        }

    def _check_muros_cerramientos(self, text: str) -> dict:
        """Check 5: Muros y cerramientos."""
        patrones = [
            r"(muro\s+de\s+alba[ñn]iler[ií]a)",
            r"(cerramiento)",
            r"(tabique)",
            r"(divisorio)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "RE7713-005",
            "descripcion": "Muros y cerramientos",
            "cumple": encontrado,
            "severidad": "WARNING" if not encontrado else "INFO",
            "mensaje": (
                "Se detectan muros y cerramientos." if encontrado
                else "No se detectan muros/cerramientos. Verificar si aplica al proyecto."
            ),
        }

    def _check_techumbre(self, text: str) -> dict:
        """Check 6: Techumbre y cubierta."""
        patrones = [
            r"(techumbre)",
            r"(cubierta)",
            r"(techo)",
            r"(tejas?|planchas?|fierro)\s*(ondulado)?",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "RE7713-006",
            "descripcion": "Techumbre y cubierta",
            "cumple": encontrado,
            "severidad": "ERROR" if not encontrado else "INFO",
            "mensaje": (
                "Se detecta descripcion de techumbre/cubierta." if encontrado
                else "No se detecta techumbre ni cubierta. Obligatorio segun R.E. 7713."
            ),
        }

    def _check_instalaciones(self, text: str) -> dict:
        """Check 7: Instalaciones (sanitario, electrico, gas)."""
        patrones = [
            r"(instalaciones?\s+sanitarias?)",
            r"(instalaciones?\s+el[ée]ctricas?)",
            r"(instalaci[oó]n\s+de\s+gas)",
            r"(NCh\s*350|NCh\s*4[\s:]|NCh\s*2[\s:])",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "RE7713-007",
            "descripcion": "Instalaciones (sanitario, electrico, gas)",
            "cumple": encontrado,
            "severidad": "ERROR" if not encontrado else "INFO",
            "mensaje": (
                "Se detectan instalaciones." if encontrado
                else "No se detectan instalaciones. Obligatorio segun R.E. 7713."
            ),
        }

    def _check_pavimentos_caletas(self, text: str) -> dict:
        """Check 8: Pavimentos exteriores y caletas."""
        patrones = [
            r"(pavimento)",
            r"(caletera)",
            r"(acceso\s+vehicular)",
            r"(estacionamiento)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "RE7713-008",
            "descripcion": "Pavimentos exteriores y caletas",
            "cumple": encontrado,
            "severidad": "WARNING" if not encontrado else "INFO",
            "mensaje": (
                "Se detectan pavimentos o caletas." if encontrado
                else "No se detectan pavimentos/caletas. Verificar si el proyecto las incluye."
            ),
        }

    def _check_muros_contencion(self, text: str) -> dict:
        """Check 9: Muros de contencion."""
        patrones = [
            r"(muro\s+de\s+contenci[oó]n)",
            r"(muro\s+de\s+encauzamiento)",
            r"(muro\s+de\s+escollera)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "RE7713-009",
            "descripcion": "Muros de contencion",
            "cumple": encontrado,
            "severidad": "INFO",
            "mensaje": (
                "Se detectan muros de contencion." if encontrado
                else "No se detectan muros de contencion. Verificar si el proyecto los incluye."
            ),
        }

    def _check_accesibilidad(self, text: str) -> dict:
        """Check 10: Accesibilidad universal."""
        patrones = [
            r"(accesibilidad)",
            r"(universal)\s*(design)?",
            r"(discapacidad)",
            r"(rampa)",
            r"(NCh\s*3539)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "RE7713-010",
            "descripcion": "Accesibilidad universal",
            "cumple": encontrado,
            "severidad": "WARNING" if not encontrado else "INFO",
            "mensaje": (
                "Se detecta accesibilidad universal." if encontrado
                else "No se detecta accesibilidad universal. Recomendable verificar segun NCh 3539."
            ),
        }

    def _check_sustentabilidad(self, text: str) -> dict:
        """Check 11: Sustentabilidad y eficiencia energetica."""
        patrones = [
            r"(sustentabilidad)",
            r"(eficiencia\s+energ[ée]tica)",
            r"(certificaci[oó]n\s+energ[ée]tica)",
            r"(aislaci[oó]n\s+t[ée]rmica)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "RE7713-011",
            "descripcion": "Sustentabilidad y eficiencia energetica",
            "cumple": encontrado,
            "severidad": "INFO",
            "mensaje": (
                "Se detecta sustentabilidad/eficiencia energetica." if encontrado
                else "No se detecta sustentabilidad. Item recomendable segun R.E. 7713."
            ),
        }

    def _check_especificaciones_materiales(self, text: str) -> dict:
        """Check 12: Especificaciones tecnicas de materiales."""
        patrones = [
            r"(especificaciones?\s+t[ée]cnicas?)",
            r"(especificaci[oó]n\s+de\s+materiales)",
            r"(materiales\s+a\s+emplear)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "RE7713-012",
            "descripcion": "Especificaciones tecnicas de materiales",
            "cumple": encontrado,
            "severidad": "ERROR" if not encontrado else "INFO",
            "mensaje": (
                "Se detectan especificaciones de materiales." if encontrado
                else "No se detectan especificaciones de materiales. Obligatorio R.E. 7713."
            ),
        }

    def _check_presupuesto(self, text: str) -> dict:
        """Check 13: Presupuesto itemizado."""
        patrones = [
            r"(presupuesto)",
            r"(costo\s+total)",
            r"(valor\s+total)",
            r"( UF)",
            r"( CLP)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "RE7713-013",
            "descripcion": "Presupuesto itemizado",
            "cumple": encontrado,
            "severidad": "ERROR" if not encontrado else "INFO",
            "mensaje": (
                "Se detecta presupuesto itemizado." if encontrado
                else "No se detecta presupuesto. Obligatorio segun R.E. 7713."
            ),
        }

    def _check_planos(self, text: str) -> dict:
        """Check 14: Planos de conjunto y detalles."""
        patrones = [
            r"(plano\s+de\s+conjunto)",
            r"(plano\s+de\s+ubicaci[oó]n)",
            r"(plano\s+de\s+emplazamiento)",
            r"(plano\s+[ASE]-\d+)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "RE7713-014",
            "descripcion": "Planos de conjunto, ubicacion y detalles",
            "cumple": encontrado,
            "severidad": "ERROR" if not encontrado else "INFO",
            "mensaje": (
                "Se detectan planos de conjunto/detalles." if encontrado
                else "No se detectan planos. Obligatorio segun R.E. 7713."
            ),
        }

    def _check_programa_construccion(self, text: str) -> dict:
        """Check 15: Programa de construccion."""
        patrones = [
            r"(programa\s+de\s+construcci[oó]n)",
            r"(cronograma)",
            r"(plazo\s+de\s+ejecuci[oó]n)",
            r"(plazo\s+de\s+construcci[oó]n)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "RE7713-015",
            "descripcion": "Programa de construccion / cronograma",
            "cumple": encontrado,
            "severidad": "WARNING" if not encontrado else "INFO",
            "mensaje": (
                "Se detecta programa de construccion." if encontrado
                else "No se detecta programa de construccion. Recomendable segun R.E. 7713."
            ),
        }

    def _error_result(self, mensaje: str) -> ExtractionResult:
        """Crea un ExtractionResult de error estandarizado."""
        return ExtractionResult(
            raw_text="",
            structured_data={
                "norma": self.NORMA,
                "checks": [],
                "checks_aprobados": 0,
                "checks_fallidos": 0,
                "total_checks": 15,
                "score_porcentaje": 0.0,
            },
            confidence=0.0,
            extractor_name=self.EXTRACTOR_NAME,
            page_count=0,
            metadata={"error": mensaje},
        )
