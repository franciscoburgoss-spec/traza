"""
Extractor de parametros sismicos desde texto ya extraido de PDF.

Extrae: zona_sismica (1, 2, 3), Ao (aceleracion sismica en g),
tipo_suelo (I, II, III) usando expresiones regulares sobre el texto.

Trabaja sobre el texto ya extraido por PDFExtractor, NO abre archivos
directamente. Esto permite que el revisor tambien pegue texto manualmente
si la extraccion automatica falla.

Referencias normativas:
    - NCh 433:1996 (Mod. 2012) - Diseno sismico
    - DS 61 - Ordenanza general de urbanismo y construcciones
"""

import re
import logging
from typing import Optional

from .base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


class SeismicExtractor(BaseExtractor):
    """Extrae parametros de diseno sismico desde texto de memoria de calculo.

    El texto de entrada puede provenir de PDFExtractor o ser ingresado
    manualmente por el revisor.
    """

    EXTRACTOR_NAME: str = "SeismicExtractor"

    # Patrones regex para cada parametro sismico
    PATRON_ZONA: list[re.Pattern] = [
        re.compile(r"zona\s*s[ií]smica\s*[:=]?\s*(\d)", re.IGNORECASE),
        re.compile(r"Z\s*[=:]\s*(\d)", re.IGNORECASE),
        re.compile(r"zona\s*[:=]?\s*(\d)", re.IGNORECASE),
        re.compile(r"Zona\s+S[ií]smica\s+([I]{1,3}|1|2|3)", re.IGNORECASE),
    ]

    PATRON_AO: list[re.Pattern] = [
        re.compile(r"A[o0]\s*[=:]\s*([0-9]+\.?[0-9]*)", re.IGNORECASE),
        re.compile(r"aceleraci[oó]n\s*[^0-9]*([0-9]+\.?[0-9]*)\s*[gG]?", re.IGNORECASE),
        re.compile(r"A[o0]\s+[^0-9]*([0-9]+\.?[0-9]*)\s*[gG]", re.IGNORECASE),
        re.compile(r"coeficiente\s*s[ií]smico\s*[^0-9]*([0-9]+\.?[0-9]*)", re.IGNORECASE),
    ]

    PATRON_SUELO: list[re.Pattern] = [
        re.compile(r"tipo\s*de\s*suelo\s*[:=]?\s*([I]{1,3})", re.IGNORECASE),
        re.compile(r"suelo\s*tipo\s*[:=]?\s*([I]{1,3})", re.IGNORECASE),
        re.compile(r"Ds\s*61[^0-9]*([I]{1,3})", re.IGNORECASE),
        re.compile(r"perfil\s*de\s*suelo\s*[:=]?\s*([I]{1,3})", re.IGNORECASE),
        re.compile(r"estrato\s*tipo\s*[:=]?\s*([I]{1,3})", re.IGNORECASE),
    ]

    # Valores validos segun normativa
    ZONAS_VALIDAS: list[int] = [1, 2, 3]
    TIPOS_SUELO_VALIDOS: list[str] = ["I", "II", "III"]
    AO_POR_ZONA: dict[int, float] = {1: 0.20, 2: 0.30, 3: 0.40}

    def can_extract(self, file_path: str) -> bool:
        """Este extractor trabaja sobre texto, no sobre archivos.

        Siempre retorna True porque puede procesar cualquier string.
        El metodo extract() recibe una ruta pero intenta leer el archivo
        como texto plano si es necesario.

        Args:
            file_path: Ruta al archivo (no usada directamente, solo para
                       compatibilidad con BaseExtractor).

        Returns:
            Siempre True.
        """
        return True

    def extract(self, file_path: str) -> ExtractionResult:
        """Extrae parametros sismicos desde un archivo de texto o ruta.

        Si file_path es una ruta existente, lee el contenido. Si no,
        trata el string como texto directo.

        Args:
            file_path: Ruta a archivo de texto, o texto directo.

        Returns:
            ExtractionResult con structured_data = {
                "zona_sismica": int | None,
                "Ao": float | None,
                "tipo_suelo": str | None,
            }
        """
        import os

        # Leer texto: si es archivo, leerlo; si no, usar el string directo
        if os.path.isfile(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
            except UnicodeDecodeError:
                try:
                    with open(file_path, "r", encoding="latin-1") as f:
                        text = f.read()
                except Exception as e:
                    return self._error_result(f"No se pudo leer archivo: {e}")
            except Exception as e:
                return self._error_result(f"Error leyendo archivo: {e}")
        else:
            text = file_path

        return self.extract_from_text(text)

    def extract_from_text(self, text: str) -> ExtractionResult:
        """Extrae parametros sismicos directamente desde un string.

        Este es el metodo principal para uso programatico. Permite que
        el revisor pegue texto manualmente sin pasar por archivos.

        Args:
            text: Texto de la memoria de calculo (de PDFExtractor o manual).

        Returns:
            ExtractionResult con los parametros sismicos detectados.
        """
        if not text or not isinstance(text, str):
            return self._error_result("Texto vacio o invalido")

        zona = self._buscar_zona(text)
        ao = self._buscar_ao(text)
        suelo = self._buscar_tipo_suelo(text)

        # Calcular confianza: +0.3 por cada parametro encontrado, con maximo 0.9
        params_encontrados = sum(p is not None for p in [zona, ao, suelo])
        confidence = min(0.9, 0.1 + params_encontrados * 0.3)

        # Validar consistencia zona vs Ao
        metadata: dict[str, any] = {"params_encontrados": params_encontrados}
        if zona is not None and ao is not None:
            ao_esperado = self.AO_POR_ZONA.get(zona)
            if ao_esperado and abs(ao - ao_esperado) > 0.05:
                metadata["advertencia"] = (
                    f"Ao={ao} no coincide con valor esperado para Zona {zona} "
                    f"(esperado: {ao_esperado}). Revisar manualmente."
                )
                confidence = max(0.3, confidence - 0.2)

        structured_data: dict[str, any] = {
            "zona_sismica": zona,
            "Ao": ao,
            "tipo_suelo": suelo,
        }

        return ExtractionResult(
            raw_text=text[:2000] if len(text) > 2000 else text,
            structured_data=structured_data,
            confidence=confidence,
            extractor_name=self.EXTRACTOR_NAME,
            page_count=0,
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Metodos privados de busqueda
    # ------------------------------------------------------------------

    def _buscar_zona(self, text: str) -> Optional[int]:
        """Busca la zona sismica en el texto usando patrones regex."""
        for patron in self.PATRON_ZONA:
            match = patron.search(text)
            if match:
                valor = match.group(1).strip().upper()
                # Convertir romanos o digitos
                if valor in ("I", "II", "III"):
                    zona = {"I": 1, "II": 2, "III": 3}.get(valor)
                else:
                    try:
                        zona = int(valor)
                    except ValueError:
                        continue
                if zona in self.ZONAS_VALIDAS:
                    return zona
        return None

    def _buscar_ao(self, text: str) -> Optional[float]:
        """Busca la aceleracion sismica Ao en el texto."""
        for patron in self.PATRON_AO:
            match = patron.search(text)
            if match:
                try:
                    valor = float(match.group(1))
                    # Validar rango razonable para Chile (0.1 a 0.6 g)
                    if 0.05 <= valor <= 1.0:
                        return round(valor, 3)
                except (ValueError, IndexError):
                    continue
        return None

    def _buscar_tipo_suelo(self, text: str) -> Optional[str]:
        """Busca el tipo de suelo en el texto."""
        for patron in self.PATRON_SUELO:
            match = patron.search(text)
            if match:
                valor = match.group(1).strip().upper()
                if valor in self.TIPOS_SUELO_VALIDOS:
                    return valor
        return None

    def _error_result(self, mensaje: str) -> ExtractionResult:
        """Crea un ExtractionResult de error estandarizado."""
        return ExtractionResult(
            raw_text="",
            structured_data={"zona_sismica": None, "Ao": None, "tipo_suelo": None},
            confidence=0.0,
            extractor_name=self.EXTRACTOR_NAME,
            page_count=0,
            metadata={"error": mensaje},
        )
