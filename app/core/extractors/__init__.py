"""
Extractores de datos para memorias de calculo estructural.

Exporta la clase base abstracta y los 6 extractores del MVP:
  - PDFExtractor: extraccion de texto crudo desde PDF
  - SeismicExtractor: parametros sismicos (zona, Ao, tipo suelo)
  - NormIndexExtractor: indice de normas NCh referenciadas
  - PlanRefsExtractor: referencias a planos estructurales
  - NCh3417Extractor: verificador de cumplimiento NCh 3417:2016
  - RE7713Extractor: verificador de R.E. 7713 (itemizacion tecnica)
"""

from .base import BaseExtractor, ExtractionResult
from .pdf_extractor import PDFExtractor
from .seismic_extractor import SeismicExtractor
from .norm_index_extractor import NormIndexExtractor
from .plan_refs_extractor import PlanRefsExtractor
from .nch3417_extractor import NCh3417Extractor
from .re7713_extractor import RE7713Extractor

__all__ = [
    "BaseExtractor",
    "ExtractionResult",
    "PDFExtractor",
    "SeismicExtractor",
    "NormIndexExtractor",
    "PlanRefsExtractor",
    "NCh3417Extractor",
    "RE7713Extractor",
]
