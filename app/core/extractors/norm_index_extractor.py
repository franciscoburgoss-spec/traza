"""
Extractor de indice normativo: busca referencias a normas NCh en el texto.

En toda memoria de calculo estructural se hace referencia a normas tecnicas.
Este extractor cataloga QUE normas se citan y en que paginas aparecen,
permitiendo al revisor verificar que se usan las versiones correctas y
que no faltan referencias obligatorias.

Normas tipicamente referenciadas en vivienda social FSEV:
    - NCh 430:2008 - Hormigon armado
    - NCh 433:1996 (Mod. 2012) - Diseno sismico
    - NCh 2361:2001 - Accion del viento
    - NCh 3171:2010 - Acciones de calculo
    - NCh 3417:2016 - Itemizacion general de proyectos
    - NCh 853:2007 - Acero para hormigon armado
    - NCh 1198:2006 - Madera
    - NCh 350:2016 - Instalaciones sanitarias
    - NCh 4:2003 - Gas
    - NCh 2:1983 - Electricas
    - NCh 1146:2013 - Telecomunicaciones
"""

import re
import logging
from typing import Optional

from .base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


class NormIndexExtractor(BaseExtractor):
    """Extrae referencias a normas NCh y otras normativas tecnicas.

    Escanea el texto buscando patrones como 'NCh 430', 'NCh433:2008',
    'NCh-2361', etc. y devuelve un indice con la pagina donde aparece
cada referencia.
    """

    EXTRACTOR_NAME: str = "NormIndexExtractor"

    # Patron principal para normas NCh
    PATRON_NCH: re.Pattern = re.compile(
        r"NCh\s*(\d{2,4})\s*[:\-/]?\s*(\d{0,4})",
        re.IGNORECASE,
    )

    # Patron para normas ISO
    PATRON_ISO: re.Pattern = re.compile(
        r"ISO\s+(\d{4,5})\s*[:\-/]?\s*(\d{0,4})",
        re.IGNORECASE,
    )

    # Patron para normas ASTM
    PATRON_ASTM: re.Pattern = re.compile(
        r"ASTM\s+([A-Z]\d{2,4}\s*[\/\-]?\s*\d{0,4})",
        re.IGNORECASE,
    )

    # Patron para normas ACI
    PATRON_ACI: re.Pattern = re.compile(
        r"ACI\s+(\d{2,4}[A-Z]?\s*[\/\-]?\s*\d{0,4})",
        re.IGNORECASE,
    )

    # Normas criticas que DEBEN aparecer en toda memoria de calculo
    NORMAS_CRITICAS: list[str] = [
        "NCh 430",
        "NCh 433",
        "NCh 2361",
        "NCh 3171",
        "NCh 3417",
        "NCh 853",
        "NCh 1198",
    ]

    def can_extract(self, file_path: str) -> bool:
        """Siempre True: trabaja sobre texto directo o archivo."""
        return True

    def extract(self, file_path: str) -> ExtractionResult:
        """Extrae indice normativo desde archivo o texto directo.

        Args:
            file_path: Ruta a archivo de texto, o texto directo.

        Returns:
            ExtractionResult con structured_data = {
                "normas_encontradas": list[dict],
                "normas_criticas_faltantes": list[str],
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
        """Extrae indice normativo desde string.

        Args:
            text: Texto completo de la memoria de calculo.

        Returns:
            ExtractionResult con indice de normas y faltantes criticas.
        """
        if not text or not isinstance(text, str):
            return self._error_result("Texto vacio")

        normas_encontradas: list[dict] = []
        normas_vistas: set[str] = set()
        pagina_actual: int = 1

        lineas = text.splitlines()

        for num_linea, linea in enumerate(lineas, start=1):
            # Detectar salto de pagina
            if linea.startswith("--- Pagina"):
                try:
                    pagina_actual = int(linea.replace("--- Pagina ", "").replace(" ---", "").strip())
                except ValueError:
                    pass

            # Buscar NCh
            for match in self.PATRON_NCH.finditer(linea):
                numero = match.group(1)
                anio = match.group(2)
                norma_str = f"NCh {numero}"
                norma_completa = f"NCh {numero}:{anio}" if anio else norma_str

                if norma_str not in normas_vistas:
                    normas_vistas.add(norma_str)
                    normas_encontradas.append({
                        "norma": norma_completa,
                        "base": norma_str,
                        "pagina": pagina_actual,
                        "linea": num_linea,
                    })

            # Buscar ISO
            for match in self.PATRON_ISO.finditer(linea):
                numero = match.group(1)
                anio = match.group(2)
                norma_completa = f"ISO {numero}:{anio}" if anio else f"ISO {numero}"
                if norma_completa not in normas_vistas:
                    normas_vistas.add(norma_completa)
                    normas_encontradas.append({
                        "norma": norma_completa,
                        "base": f"ISO {numero}",
                        "pagina": pagina_actual,
                        "linea": num_linea,
                    })

            # Buscar ASTM
            for match in self.PATRON_ASTM.finditer(linea):
                norma_completa = f"ASTM {match.group(1)}"
                if norma_completa not in normas_vistas:
                    normas_vistas.add(norma_completa)
                    normas_encontradas.append({
                        "norma": norma_completa,
                        "base": norma_completa,
                        "pagina": pagina_actual,
                        "linea": num_linea,
                    })

            # Buscar ACI
            for match in self.PATRON_ACI.finditer(linea):
                norma_completa = f"ACI {match.group(1)}"
                if norma_completa not in normas_vistas:
                    normas_vistas.add(norma_completa)
                    normas_encontradas.append({
                        "norma": norma_completa,
                        "base": norma_completa,
                        "pagina": pagina_actual,
                        "linea": num_linea,
                    })

        # Identificar normas criticas faltantes
        normas_criticas_faltantes: list[str] = []
        for critica in self.NORMAS_CRITICAS:
            if critica not in normas_vistas:
                normas_criticas_faltantes.append(critica)

        # Calcular confianza
        total_referencias = len(normas_encontradas)
        if total_referencias == 0:
            confidence = 0.1
        elif total_referencias >= len(self.NORMAS_CRITICAS):
            confidence = 0.9
        else:
            confidence = 0.4 + (total_referencias / len(self.NORMAS_CRITICAS)) * 0.5

        structured_data = {
            "normas_encontradas": normas_encontradas,
            "normas_criticas_faltantes": normas_criticas_faltantes,
            "total_referencias": total_referencias,
            "total_normas_unicas": len(normas_vistas),
        }

        return ExtractionResult(
            raw_text=text[:1000] if len(text) > 1000 else text,
            structured_data=structured_data,
            confidence=round(confidence, 2),
            extractor_name=self.EXTRACTOR_NAME,
            page_count=0,
            metadata={
                "normas_criticas_esperadas": len(self.NORMAS_CRITICAS),
                "normas_criticas_encontradas": len(self.NORMAS_CRITICAS) - len(normas_criticas_faltantes),
            },
        )

    def _error_result(self, mensaje: str) -> ExtractionResult:
        """Crea un ExtractionResult de error estandarizado."""
        return ExtractionResult(
            raw_text="",
            structured_data={
                "normas_encontradas": [],
                "normas_criticas_faltantes": self.NORMAS_CRITICAS,
                "total_referencias": 0,
            },
            confidence=0.0,
            extractor_name=self.EXTRACTOR_NAME,
            page_count=0,
            metadata={"error": mensaje},
        )
