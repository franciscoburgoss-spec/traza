"""
Verificador de cumplimiento NCh 3417:2016 - Itemizacion general de proyectos.

La NCh 3417:2016 establece el contenido minimo que debe tener la documentacion
tecnica de un proyecto de construccion. Este verificador ejecuta 22 checks
sobre el texto de la memoria de calculo estructural para validar que contenga
todos los elementos exigidos.

Los checks evaluan:
  1-3: Estructura general del documento (portada, indice, refs normativas)
  4-8: Descripcion del proyecto y parametros de diseno
  9-13: Cargas, combinaciones y estados limite
  14-18: Elementos estructurales y verificaciones
  19-22: Documentacion complementaria y firmas

Cada check retorna un dict estandarizado con la informacion del hallazgo.
El extractor luego consolida todos los checks en un ExtractionResult.
"""

import re
import logging
from typing import Optional

from .base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


class NCh3417Extractor(BaseExtractor):
    """Verifica cumplimiento de NCh 3417:2016 sobre memoria de calculo.

    La norma exige que la memoria de calculo contenga elementos minimos
    de documentacion tecnica. Este extractor ejecuta 22 checks de contenido.

    Nota: Estos checks buscan la EXISTENCIA de secciones/topics en el texto.
    No validan el contenido tecnico (eso lo hacen los verificadores de muro
    y caletera), solo verifican que el documento contenga las secciones
    requeridas por la norma.
    """

    EXTRACTOR_NAME: str = "NCh3417Extractor"
    NORMA: str = "NCh 3417:2016"

    def can_extract(self, file_path: str) -> bool:
        """Siempre True: trabaja sobre texto."""
        return True

    def extract(self, file_path: str) -> ExtractionResult:
        """Ejecuta los 22 checks de NCh 3417:2016 sobre el archivo o texto.

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
        """Ejecuta los 22 checks sobre el texto directamente.

        Args:
            text: Texto completo de la memoria de calculo.

        Returns:
            ExtractionResult con el resultado consolidado de los 22 checks.
        """
        if not text or not isinstance(text, str):
            return self._error_result("Texto vacio o invalido")

        checks = self._ejecutar_checks(text)
        checks_aprobados = sum(1 for c in checks if c["cumple"])
        checks_fallidos = len(checks) - checks_aprobados
        score_porcentaje = round((checks_aprobados / len(checks)) * 100, 1) if checks else 0.0

        # Calcular confianza basada en cantidad de checks aprobados
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

        # Determinar severidad global
        checks_criticos_fallidos = sum(
            1 for c in checks
            if not c["cumple"] and c["severidad"] in ("ERROR", "CRITICAL")
        )

        return ExtractionResult(
            raw_text=text[:500] if len(text) > 500 else text,
            structured_data=structured_data,
            confidence=confidence,
            extractor_name=self.EXTRACTOR_NAME,
            page_count=0,
            metadata={
                "checks_criticos_fallidos": checks_criticos_fallidos,
                "checks_warning_fallidos": sum(
                    1 for c in checks if not c["cumple"] and c["severidad"] == "WARNING"
                ),
            },
        )

    def _ejecutar_checks(self, text: str) -> list[dict]:
        """Ejecuta los 22 checks de contenido.

        Args:
            text: Texto de la memoria de calculo.

        Returns:
            Lista de dicts con resultado de cada check.
        """
        checks = []

        # ============================================================
        # BLOQUE 1: Estructura general del documento (checks 1-3)
        # ============================================================

        # Check 1: Portada con titulo del proyecto
        checks.append(self._check_portada(text))

        # Check 2: Indice general
        checks.append(self._check_indice(text))

        # Check 3: Referencias normativas
        checks.append(self._check_refs_normativas(text))

        # ============================================================
        # BLOQUE 2: Descripcion del proyecto (checks 4-8)
        # ============================================================

        # Check 4: Descripcion del proyecto
        checks.append(self._check_descripcion_proyecto(text))

        # Check 5: Parametros de diseno sismico
        checks.append(self._check_parametros_sismicos(text))

        # Check 6: Combinaciones de carga
        checks.append(self._check_combinaciones_carga(text))

        # Check 7: Verificacion de estabilidad
        checks.append(self._check_estabilidad(text))

        # Check 8: Descripcion del sistema estructural
        checks.append(self._check_sistema_estructural(text))

        # ============================================================
        # BLOQUE 3: Cargas y estados limite (checks 9-13)
        # ============================================================

        # Check 9: Cargas permanentes
        checks.append(self._check_cargas_permanentes(text))

        # Check 10: Cargas de uso (sobrecargas)
        checks.append(self._check_cargas_uso(text))

        # Check 11: Cargas de viento
        checks.append(self._check_cargas_viento(text))

        # Check 12: Cargas sismicas
        checks.append(self._check_cargas_sismicas(text))

        # Check 13: Estados limite de servicio (ELS)
        checks.append(self._check_estados_limite_servicio(text))

        # ============================================================
        # BLOQUE 4: Elementos estructurales (checks 14-18)
        # ============================================================

        # Check 14: Cimentacion
        checks.append(self._check_cimentacion(text))

        # Check 15: Muros
        checks.append(self._check_muros(text))

        # Check 16: Vigas y losas
        checks.append(self._check_vigas_losas(text))

        # Check 17: Dimensionamiento de elementos
        checks.append(self._check_dimensionamiento(text))

        # Check 18: Detalles constructivos
        checks.append(self._check_detalles_constructivos(text))

        # ============================================================
        # BLOQUE 5: Documentacion complementaria (checks 19-22)
        # ============================================================

        # Check 19: Especificaciones tecnicas
        checks.append(self._check_especificaciones(text))

        # Check 20: Planos de detalle
        checks.append(self._check_planos_detalle(text))

        # Check 21: Memoria de calculo firmada
        checks.append(self._check_firma_memoria(text))

        # Check 22: Anexos y adjuntos
        checks.append(self._check_anexos(text))

        return checks

    # ------------------------------------------------------------------
    # Metodos de check individuales
    # ------------------------------------------------------------------

    def _check_portada(self, text: str) -> dict:
        """Check 1: Portada con titulo del proyecto."""
        patrones = [
            r"(memoria\s+de\s+c[áa]lculo)",
            r"(c[áa]lculo\s+estructural)",
            r"(proyecto\s*:?\s*[A-Z])",
            r"(vivienda\s+social)",
            r"(FSEV)",
            r"(Fondo\s+Solidario)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "NCh3417-001",
            "descripcion": "Portada con titulo del proyecto",
            "cumple": encontrado,
            "severidad": "WARNING" if not encontrado else "INFO",
            "mensaje": (
                "Se detecta portada/titulo del proyecto." if encontrado
                else "No se detecta portada ni titulo claro del proyecto. Verificar que exista pagina de portada."
            ),
        }

    def _check_indice(self, text: str) -> dict:
        """Check 2: Indice general del documento."""
        patrones = [
            r"(índice|indice)\s*(general)?",
            r"(contenido)\s*",
            r"(\d+\.\s+[A-Z][a-zA-Z\s]{5,})",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "NCh3417-002",
            "descripcion": "Indice general",
            "cumple": encontrado,
            "severidad": "WARNING" if not encontrado else "INFO",
            "mensaje": (
                "Se detecta indice general en el documento." if encontrado
                else "No se detecta indice general. La NCh 3417 exige indice de contenidos."
            ),
        }

    def _check_refs_normativas(self, text: str) -> dict:
        """Check 3: Referencias normativas."""
        patron = re.compile(r"NCh\s*\d{2,4}", re.IGNORECASE)
        matches = patron.findall(text)
        encontrado = len(matches) >= 3
        return {
            "check_id": "NCh3417-003",
            "descripcion": "Referencias normativas (NCh 430, 433, etc.)",
            "cumple": encontrado,
            "severidad": "ERROR" if not encontrado else "INFO",
            "mensaje": (
                f"Se detectan {len(set(matches))} normas referenciadas." if encontrado
                else "No se detectan referencias a normas NCh. Se requieren al menos NCh 430, NCh 433 y NCh 2361."
            ),
        }

    def _check_descripcion_proyecto(self, text: str) -> dict:
        """Check 4: Descripcion del proyecto."""
        patrones = [
            r"(descripci[oó]n\s+del\s+proyecto)",
            r"(antecedentes\s+generales)",
            r"(objeto\s+del\s+proyecto)",
            r"(alcance\s+del\s+proyecto)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "NCh3417-004",
            "descripcion": "Descripcion del proyecto / antecedentes generales",
            "cumple": encontrado,
            "severidad": "ERROR" if not encontrado else "INFO",
            "mensaje": (
                "Se detecta descripcion del proyecto." if encontrado
                else "No se detecta descripcion del proyecto. Item obligatorio segun NCh 3417."
            ),
        }

    def _check_parametros_sismicos(self, text: str) -> dict:
        """Check 5: Parametros de diseno sismico."""
        patrones = [
            r"(par[áa]metros?\s+s[ií]smicos?)",
            r"(zona\s+s[ií]smica)",
            r"(A[o0]\s*[=:])",
            r"(tipo\s+de\s+suelo)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "NCh3417-005",
            "descripcion": "Parametros de diseno sismico (zona, Ao, tipo suelo)",
            "cumple": encontrado,
            "severidad": "CRITICAL" if not encontrado else "INFO",
            "mensaje": (
                "Se detectan parametros de diseno sismico." if encontrado
                else "No se detectan parametros de diseno sismico. PARAMETRO CRITICO para Chile."
            ),
        }

    def _check_combinaciones_carga(self, text: str) -> dict:
        """Check 6: Combinaciones de carga."""
        patrones = [
            r"(combinaciones?\s+de\s+carga)",
            r"(estado\s+l[ií]mite\s+último)",
            r"(1\.4D\s*\+|\s*1\.2D)",
            r"(factor\s+de\s+carga)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "NCh3417-006",
            "descripcion": "Combinaciones de carga",
            "cumple": encontrado,
            "severidad": "ERROR" if not encontrado else "INFO",
            "mensaje": (
                "Se detectan combinaciones de carga." if encontrado
                else "No se detectan combinaciones de carga. Obligatorio segun NCh 3171 y NCh 430."
            ),
        }

    def _check_estabilidad(self, text: str) -> dict:
        """Check 7: Verificacion de estabilidad."""
        patrones = [
            r"(estabilidad)",
            r"(factor\s+de\s+seguridad)",
            r"(F\.?O\.?S\.?|fos)",
            r"(vuelco|deslizamiento|hundimiento)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "NCh3417-007",
            "descripcion": "Verificacion de estabilidad (vuelco, deslizamiento)",
            "cumple": encontrado,
            "severidad": "ERROR" if not encontrado else "INFO",
            "mensaje": (
                "Se detecta verificacion de estabilidad." if encontrado
                else "No se detecta verificacion de estabilidad. Obligatorio para elementos de contencion."
            ),
        }

    def _check_sistema_estructural(self, text: str) -> dict:
        """Check 8: Descripcion del sistema estructural."""
        patrones = [
            r"(sistema\s+estructural)",
            r"(tipolog[ií]a\s+estructural)",
            r"(muro\s+de\s+mamposter[ií]a)",
            r"(hormig[oó]n\s+armado)",
            r"(estructura\s+met[áa]lica)",
            r"(madera)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "NCh3417-008",
            "descripcion": "Descripcion del sistema estructural",
            "cumple": encontrado,
            "severidad": "ERROR" if not encontrado else "INFO",
            "mensaje": (
                "Se detecta descripcion del sistema estructural." if encontrado
                else "No se detecta descripcion del sistema estructural. Item obligatorio segun NCh 3417."
            ),
        }

    def _check_cargas_permanentes(self, text: str) -> dict:
        """Check 9: Cargas permanentes."""
        patrones = [
            r"(cargas?\s+permanentes?)",
            r"(peso\s+propio)",
            r"(carga\s+muerta)",
            r"(dead\s+load)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "NCh3417-009",
            "descripcion": "Cargas permanentes (peso propio)",
            "cumple": encontrado,
            "severidad": "ERROR" if not encontrado else "INFO",
            "mensaje": (
                "Se detectan cargas permanentes." if encontrado
                else "No se detectan cargas permanentes. Obligatorio segun NCh 3171."
            ),
        }

    def _check_cargas_uso(self, text: str) -> dict:
        """Check 10: Cargas de uso (sobrecargas)."""
        patrones = [
            r"(cargas?\s+de\s+uso)",
            r"(sobrecarga)",
            r"(live\s+load)",
            r"(sc\s*[=:])",
            r"(q\s*[=:])",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "NCh3417-010",
            "descripcion": "Cargas de uso (sobrecargas)",
            "cumple": encontrado,
            "severidad": "ERROR" if not encontrado else "INFO",
            "mensaje": (
                "Se detectan cargas de uso." if encontrado
                else "No se detectan cargas de uso (sobrecargas). Obligatorio segun NCh 3171."
            ),
        }

    def _check_cargas_viento(self, text: str) -> dict:
        """Check 11: Cargas de viento."""
        patrones = [
            r"(viento)",
            r"(NCh\s*2361)",
            r"(presi[oó]n\s+de\s+viento)",
            r"(wind\s+load)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "NCh3417-011",
            "descripcion": "Cargas de viento",
            "cumple": encontrado,
            "severidad": "WARNING" if not encontrado else "INFO",
            "mensaje": (
                "Se detectan cargas de viento." if encontrado
                else "No se detectan cargas de viento. Verificar si aplica (zona de viento)."
            ),
        }

    def _check_cargas_sismicas(self, text: str) -> dict:
        """Check 12: Cargas sismicas."""
        patrones = [
            r"(s[ií]smo)",
            r"(carga\s+s[ií]smica)",
            r"(espectro\s+de\s+respuesta)",
            r"(an[áa]lisis\s+s[ií]smico)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "NCh3417-012",
            "descripcion": "Cargas sismicas / analisis sismico",
            "cumple": encontrado,
            "severidad": "CRITICAL" if not encontrado else "INFO",
            "mensaje": (
                "Se detectan cargas sismicas / analisis sismico." if encontrado
                else "No se detecta analisis sismico. OBLIGATORIO en Chile para toda estructura."
            ),
        }

    def _check_estados_limite_servicio(self, text: str) -> dict:
        """Check 13: Estados limite de servicio."""
        patrones = [
            r"(estado\s+l[ií]mite\s+de\s+servicio)",
            r"(E\.?L\.?S\.?|ELS)",
            r"(deformaci[oó]n)",
            r"(flecha)\s*(m[áa]xima)?",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "NCh3417-013",
            "descripcion": "Estados limite de servicio (deformaciones, fisuracion)",
            "cumple": encontrado,
            "severidad": "ERROR" if not encontrado else "INFO",
            "mensaje": (
                "Se detectan estados limite de servicio." if encontrado
                else "No se detectan estados limite de servicio. Obligatorio segun NCh 430."
            ),
        }

    def _check_cimentacion(self, text: str) -> dict:
        """Check 14: Cimentacion."""
        patrones = [
            r"(cimentaci[oó]n)",
            r"(zapata)",
            r"(pilote)",
            r"(fundaci[oó]n)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "NCh3417-014",
            "descripcion": "Descripcion de cimentacion",
            "cumple": encontrado,
            "severidad": "ERROR" if not encontrado else "INFO",
            "mensaje": (
                "Se detecta descripcion de cimentacion." if encontrado
                else "No se detecta descripcion de cimentacion. Obligatorio segun NCh 3417."
            ),
        }

    def _check_muros(self, text: str) -> dict:
        """Check 15: Muros estructurales."""
        patrones = [
            r"(muro\s+de\s+contenci[oó]n)",
            r"(muro\s+estructural)",
            r"(mamposter[ií]a)",
            r"(muro\s+de\s+hormig[oó]n)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "NCh3417-015",
            "descripcion": "Muros (contencion o estructurales)",
            "cumple": encontrado,
            "severidad": "WARNING" if not encontrado else "INFO",
            "mensaje": (
                "Se detectan muros en el calculo." if encontrado
                else "No se detectan muros. Verificar si el proyecto incluye muros de contencion."
            ),
        }

    def _check_vigas_losas(self, text: str) -> dict:
        """Check 16: Vigas y losas."""
        patrones = [
            r"(viga)",
            r"(losa)",
            r"(viga\s+de\s+cimentaci[oó]n)",
            r"( losa\s+de\s+entrepiso)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "NCh3417-016",
            "descripcion": "Vigas y losas",
            "cumple": encontrado,
            "severidad": "WARNING" if not encontrado else "INFO",
            "mensaje": (
                "Se detectan vigas y/o losas." if encontrado
                else "No se detectan vigas ni losas. Verificar tipologia estructural."
            ),
        }

    def _check_dimensionamiento(self, text: str) -> dict:
        """Check 17: Dimensionamiento de elementos."""
        patrones = [
            r"(dimensionamiento)",
            r"(dise[ñn]o\s+de)",
            r"(armadura)",
            r"(refuerzo)",
            r"(estribos)",
            r"(armado)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "NCh3417-017",
            "descripcion": "Dimensionamiento de elementos (armaduras, refuerzo)",
            "cumple": encontrado,
            "severidad": "ERROR" if not encontrado else "INFO",
            "mensaje": (
                "Se detecta dimensionamiento de elementos." if encontrado
                else "No se detecta dimensionamiento de elementos. Obligatorio segun NCh 3417."
            ),
        }

    def _check_detalles_constructivos(self, text: str) -> dict:
        """Check 18: Detalles constructivos."""
        patrones = [
            r"(detalle\s+constructivo)",
            r"(juntas?\s+de\s+dilataci[oó]n)",
            r"(junta\s+de\s+construcci[oó]n)",
            r"(recubrimiento)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "NCh3417-018",
            "descripcion": "Detalles constructivos (juntas, recubrimiento)",
            "cumple": encontrado,
            "severidad": "WARNING" if not encontrado else "INFO",
            "mensaje": (
                "Se detectan detalles constructivos." if encontrado
                else "No se detectan detalles constructivos. Recomendable segun NCh 3417."
            ),
        }

    def _check_especificaciones(self, text: str) -> dict:
        """Check 19: Especificaciones tecnicas."""
        patrones = [
            r"(especificaciones?\s+t[ée]cnicas?)",
            r"(especificaci[oó]n\s+t[ée]cnica)",
            r"(materiales\s+a\s+emplear)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "NCh3417-019",
            "descripcion": "Especificaciones tecnicas de materiales",
            "cumple": encontrado,
            "severidad": "WARNING" if not encontrado else "INFO",
            "mensaje": (
                "Se detectan especificaciones tecnicas." if encontrado
                else "No se detectan especificaciones tecnicas. Recomendable segun NCh 3417."
            ),
        }

    def _check_planos_detalle(self, text: str) -> dict:
        """Check 20: Planos de detalle."""
        patrones = [
            r"(plano\s+de\s+detalle)",
            r"(detalle\s+estructural)",
            r"(plano\s+[SE]-\d+)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "NCh3417-020",
            "descripcion": "Planos de detalle referenciados",
            "cumple": encontrado,
            "severidad": "WARNING" if not encontrado else "INFO",
            "mensaje": (
                "Se detectan planos de detalle." if encontrado
                else "No se detectan planos de detalle. Verificar que existan planos E- y SE-."
            ),
        }

    def _check_firma_memoria(self, text: str) -> dict:
        """Check 21: Memoria de calculo firmada."""
        patrones = [
            r"(firma)",
            r"(ing\.|ingeniero)",
            r"(c[áa]lculo\s+realizado)",
            r"(revis[oó])",
            r"(autor)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "NCh3417-021",
            "descripcion": "Memoria de calculo firmada / responsable",
            "cumple": encontrado,
            "severidad": "WARNING" if not encontrado else "INFO",
            "mensaje": (
                "Se detecta firma o responsable del calculo." if encontrado
                else "No se detecta firma ni responsable del calculo. Verificar documento firmado."
            ),
        }

    def _check_anexos(self, text: str) -> dict:
        """Check 22: Anexos y adjuntos."""
        patrones = [
            r"(anexo)",
            r"(adjunto)",
            r"(ap[ée]ndice)",
        ]
        encontrado = any(re.search(p, text, re.IGNORECASE) for p in patrones)
        return {
            "check_id": "NCh3417-022",
            "descripcion": "Anexos y documentacion complementaria",
            "cumple": encontrado,
            "severidad": "INFO",
            "mensaje": (
                "Se detectan anexos o documentacion complementaria." if encontrado
                else "No se detectan anexos. Verificar si se requieren (geotecnia, ensayos, etc.)."
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
                "total_checks": 22,
                "score_porcentaje": 0.0,
            },
            confidence=0.0,
            extractor_name=self.EXTRACTOR_NAME,
            page_count=0,
            metadata={"error": mensaje},
        )
