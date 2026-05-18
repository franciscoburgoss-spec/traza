"""
Extractor de texto desde archivos PDF usando PyMuPDF (fitz).

Este es el extractor de primer nivel: extrae texto crudo, metadata
y conteo de paginas. Es 100% offline y maneja errores graceful
para PDF corruptos, protegidos o sin texto extraible.

Como revisor estructural, este modulo me da el texto base sobre el cual
trabajan todos los demas extractores. Si falla aqui, todo el pipeline falla.
"""

import os
import logging
from typing import Optional

from .base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


class PDFExtractor(BaseExtractor):
    """Extrae texto, metadata y conteo de paginas desde archivos PDF.

    Funciona 100% offline usando PyMuPDF (fitz). No realiza llamadas
    a ninguna API externa ni servicio en la nube.
    """

    EXTRACTOR_NAME: str = "PDFExtractor"

    def can_extract(self, file_path: str) -> bool:
        """Verifica que el archivo existe y tiene extension .pdf (case-insensitive).

        Args:
            file_path: Ruta absoluta al archivo.

        Returns:
            True si el archivo existe y termina en .pdf
        """
        if not file_path or not isinstance(file_path, str):
            return False
        return (
            os.path.isfile(file_path)
            and file_path.lower().endswith(".pdf")
        )

    def extract(self, file_path: str) -> ExtractionResult:
        """Extrae texto y metadata del PDF usando fitz (PyMuPDF).

        El proceso es:
            1. Abrir el PDF con fitz.open()
            2. Extraer texto pagina por pagina
            3. Extraer metadata del documento
            4. Calcular confianza segun resultado

        Args:
            file_path: Ruta absoluta al archivo PDF.

        Returns:
            ExtractionResult con raw_text, metadata y nivel de confianza.
            Confidence: 0.8 si extraccion completa, 0.5 si parcial, 0.1 si fallo total.
        """
        if not self.can_extract(file_path):
            logger.warning("PDFExtractor.can_extract() = False para %s", file_path)
            return ExtractionResult(
                raw_text="",
                structured_data={},
                confidence=0.0,
                extractor_name=self.EXTRACTOR_NAME,
                page_count=0,
                metadata={"error": "Archivo no existe o no es PDF"},
            )

        try:
            # Importacion lazy para evitar fallo si fitz no esta instalado
            import fitz  # type: ignore[import-untyped]
        except ImportError:
            logger.error("PyMuPDF (fitz) no esta instalado. Instalar con: pip install pymupdf")
            return ExtractionResult(
                raw_text="",
                structured_data={},
                confidence=0.0,
                extractor_name=self.EXTRACTOR_NAME,
                page_count=0,
                metadata={"error": "PyMuPDF no instalado"},
            )

        raw_text_parts: list[str] = []
        metadata: dict[str, any] = {}
        page_count: int = 0
        confidence: float = 0.0
        paginas_con_texto: int = 0
        paginas_sin_texto: int = 0

        try:
            doc = fitz.open(file_path)
            page_count = len(doc)

            # Extraer metadata del PDF
            meta = doc.metadata
            if meta:
                metadata["title"] = meta.get("title", "")
                metadata["author"] = meta.get("author", "")
                metadata["subject"] = meta.get("subject", "")
                metadata["creator"] = meta.get("creator", "")
                metadata["producer"] = meta.get("producer", "")
                metadata["format"] = meta.get("format", "")
                metadata["encryption"] = meta.get("encryption", "")

            # Extraer texto pagina por pagina
            for page_num in range(page_count):
                try:
                    page = doc.load_page(page_num)
                    text = page.get_text()
                    if text and text.strip():
                        raw_text_parts.append(f"--- Pagina {page_num + 1} ---\n{text}")
                        paginas_con_texto += 1
                    else:
                        paginas_sin_texto += 1
                except Exception as page_err:
                    logger.warning("Error extrayendo pagina %d de %s: %s", page_num, file_path, page_err)
                    paginas_sin_texto += 1

            doc.close()

            # Calcular confianza
            raw_text = "\n\n".join(raw_text_parts)
            if page_count == 0:
                confidence = 0.1
                metadata["error"] = "PDF sin paginas"
            elif paginas_con_texto == page_count:
                confidence = 0.8
                metadata["estado"] = "extraccion_completa"
            elif paginas_con_texto > 0:
                confidence = 0.5
                metadata["estado"] = "extraccion_parcial"
                metadata["paginas_con_texto"] = paginas_con_texto
                metadata["paginas_sin_texto"] = paginas_sin_texto
            else:
                confidence = 0.1
                metadata["estado"] = "extraccion_fallida"
                metadata["error"] = "Ninguna pagina contiene texto extraible (PDF escaneado o imagen)"

            return ExtractionResult(
                raw_text=raw_text,
                structured_data={"page_count": page_count, "paginas_con_texto": paginas_con_texto},
                confidence=confidence,
                extractor_name=self.EXTRACTOR_NAME,
                page_count=page_count,
                metadata=metadata,
            )

        except Exception as e:
            logger.error("Error abriendo o procesando PDF %s: %s", file_path, str(e))
            return ExtractionResult(
                raw_text="",
                structured_data={},
                confidence=0.1,
                extractor_name=self.EXTRACTOR_NAME,
                page_count=0,
                metadata={"error": f"Excepcion al procesar PDF: {str(e)}"},
            )
