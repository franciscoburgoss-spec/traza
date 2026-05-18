"""
Extractor de referencias a planos estructurales.

En toda memoria de calculo se hace referencia a planos que forman parte
del proyecto estructural. Este extractor identifica esas referencias para:
  1. Validar que los planos citados existen en el expediente
  2. Verificar la coherencia entre memoria de calculo y planos
  3. Generar un indice cruzado memoria-planos

Patrones tipicos de referencia a planos:
  - "Plano E-01", "Plano SE-05", "Plano E-1"
  - "Detalle SE-03", "Detalle E-12"
  - "Ver Plano E-02"
  - "E-01", "SE-05" (en contexto de planos)
"""

import re
import logging
from typing import Optional

from .base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


class PlanRefsExtractor(BaseExtractor):
    """Extrae referencias a planos estructurales del texto.

    Identifica planos de arquitectura (A-), estructura (E-), servicios (SE-),
    sanitario (S-), electrico (T-), etc.
    """

    EXTRACTOR_NAME: str = "PlanRefsExtractor"

    # Patrones para referencias a planos
    PATRONES: list[re.Pattern] = [
        # "Plano E-01", "Plano SE-05", "Plano A-12"
        re.compile(r"[Pp]lano\s+([A-Z]{1,3}\s*[-]?\s*\d{1,4}[A-Z]?)", re.IGNORECASE),
        # "Detalle E-03", "Detalle SE-12"
        re.compile(r"[Dd]etalle\s+([A-Z]{1,3}\s*[-]?\s*\d{1,4}[A-Z]?)", re.IGNORECASE),
        # "Ver plano E-01", "ver plano SE-05"
        re.compile(r"[Vv]er\s+[Pp]lano\s+([A-Z]{1,3}\s*[-]?\s*\d{1,4}[A-Z]?)", re.IGNORECASE),
        # "plano E-01" (sin mayuscula)
        re.compile(r"plano\s+([A-Z]{1,3}\s*[-]?\s*\d{1,4}[A-Z]?)", re.IGNORECASE),
        # Referencia directa: "E-01", "SE-05" (cuando aparece junto a "plano" o "estructura")
        re.compile(r"(?:plano|estructura|estructural)\s*[,:]?\s*([A-Z]{1,3}\s*[-]?\s*\d{1,4}[A-Z]?)", re.IGNORECASE),
        # "conforme al plano E-01"
        re.compile(r"conforme\s+al\s+[Pp]lano\s+([A-Z]{1,3}\s*[-]?\s*\d{1,4}[A-Z]?)", re.IGNORECASE),
        # "segun plano E-01"
        re.compile(r"seg[uú]n\s+[Pp]lano\s+([A-Z]{1,3}\s*[-]?\s*\d{1,4}[A-Z]?)", re.IGNORECASE),
    ]

    # Patron adicional para capturar todas las referencias tipo XX-NNN
    PATRON_GENERAL: re.Pattern = re.compile(
        r"\b([A-Z]{1,3})\s*[-]?\s*(\d{1,4})\s*([A-Z]?)\b"
    )

    # Prefijos de planos tipicos en vivienda social
    PREFIJOS_PLANO: list[str] = ["E", "SE", "A", "S", "T", "M", "ME"]

    def can_extract(self, file_path: str) -> bool:
        """Siempre True: trabaja sobre texto."""
        return True

    def extract(self, file_path: str) -> ExtractionResult:
        """Extrae referencias a planos desde archivo o texto.

        Args:
            file_path: Ruta a archivo de texto, o texto directo.

        Returns:
            ExtractionResult con structured_data = {
                "planos_encontrados": list[dict],
                "planos_unicos": list[str],
                "total_referencias": int,
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
        """Extrae referencias a planos desde string.

        Args:
            text: Texto completo de la memoria de calculo.

        Returns:
            ExtractionResult con lista de planos referenciados.
        """
        if not text or not isinstance(text, str):
            return self._error_result("Texto vacio")

        planos_encontrados: list[dict] = []
        planos_vistos: set[str] = set()
        pagina_actual: int = 1

        lineas = text.splitlines()

        for num_linea, linea in enumerate(lineas, start=1):
            # Detectar salto de pagina
            if linea.startswith("--- Pagina"):
                try:
                    pagina_actual = int(linea.replace("--- Pagina ", "").replace(" ---", "").strip())
                except ValueError:
                    pass

            # Buscar con patrones especificos
            for patron in self.PATRONES:
                for match in patron.finditer(linea):
                    plano_id = match.group(1).replace(" ", "").replace("-", "")
                    plano_id_normalizado = self._normalizar_plano_id(plano_id)

                    if plano_id_normalizado and plano_id_normalizado not in planos_vistos:
                        planos_vistos.add(plano_id_normalizado)
                        planos_encontrados.append({
                            "plano_id": plano_id_normalizado,
                            "contexto": linea.strip()[:120],
                            "pagina": pagina_actual,
                            "linea": num_linea,
                        })

        # Calcular confianza
        total_referencias = len(planos_encontrados)
        if total_referencias == 0:
            confidence = 0.1
        elif total_referencias >= 5:
            confidence = 0.9
        else:
            confidence = 0.3 + (total_referencias / 5) * 0.6

        # Contar por tipo de plano
        conteo_por_prefijo: dict[str, int] = {}
        for plano in planos_encontrados:
            prefijo = ""
            for char in plano["plano_id"]:
                if char.isalpha():
                    prefijo += char
                else:
                    break
            if prefijo:
                conteo_por_prefijo[prefijo] = conteo_por_prefijo.get(prefijo, 0) + 1

        structured_data = {
            "planos_encontrados": planos_encontrados,
            "planos_unicos": sorted(list(planos_vistos)),
            "total_referencias": total_referencias,
            "conteo_por_tipo": conteo_por_prefijo,
        }

        return ExtractionResult(
            raw_text=text[:500] if len(text) > 500 else text,
            structured_data=structured_data,
            confidence=round(confidence, 2),
            extractor_name=self.EXTRACTOR_NAME,
            page_count=0,
            metadata={
                "total_planos_unicos": len(planos_vistos),
                "tipos_encontrados": list(conteo_por_prefijo.keys()),
            },
        )

    def _normalizar_plano_id(self, plano_id: str) -> Optional[str]:
        """Normaliza un ID de plano al formato estandar.

        Args:
            plano_id: ID crudo extraido del texto.

        Returns:
            ID normalizado o None si no es un plano valido.
        """
        if not plano_id:
            return None

        plano_id = plano_id.strip().upper()

        # Validar que tenga prefijo de plano conocido
        for prefijo in self.PREFIJOS_PLANO:
            if plano_id.startswith(prefijo):
                # Extraer parte numerica
                numero = plano_id[len(prefijo):]
                if numero and numero.isdigit():
                    return f"{prefijo}-{numero}"

        # Si no coincide con prefijos conocidos pero tiene letras + numeros
        letras = ""
        numeros = ""
        for char in plano_id:
            if char.isalpha():
                letras += char
            elif char.isdigit():
                numeros += char

        if letras and numeros:
            return f"{letras}-{numeros}"

        return None

    def _error_result(self, mensaje: str) -> ExtractionResult:
        """Crea un ExtractionResult de error estandarizado."""
        return ExtractionResult(
            raw_text="",
            structured_data={
                "planos_encontrados": [],
                "planos_unicos": [],
                "total_referencias": 0,
            },
            confidence=0.0,
            extractor_name=self.EXTRACTOR_NAME,
            page_count=0,
            metadata={"error": mensaje},
        )
