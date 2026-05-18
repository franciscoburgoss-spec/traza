"""
Clase abstracta base para todos los extractores de TRAZA.

Define el contrato comun: can_extract() -> bool, extract() -> ExtractionResult.
El campo 'confidence' permite al revisor decidir si el dato extraido es
confiable o si debe revisarlo manualmente.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExtractionResult:
    """Contenedor estandar del resultado de cualquier extractor.

    Attributes:
        raw_text: Texto plano extraido del documento (o vacio si no aplica).
        structured_data: Diccionario con los datos estructurados especificos.
        confidence: Nivel de confianza 0.0-1.0 (>=0.5 se considera valido).
        extractor_name: Nombre identificador del extractor.
        page_count: Cantidad de paginas procesadas.
        metadata: Metadatos adicionales (errores, tiempos, paginas, etc.)
    """

    raw_text: str = ""
    structured_data: dict = field(default_factory=dict)
    confidence: float = 0.0
    extractor_name: str = ""
    page_count: int = 0
    metadata: dict = field(default_factory=dict)


class BaseExtractor(ABC):
    """Clase abstracta que todo extractor debe heredar.

    El workflow es:
        1. can_extract(path) -> True/False (el extractor puede procesar este archivo?)
        2. extract(path) -> ExtractionResult (ejecuta la extraccion)
        3. validate(result) -> bool (el resultado tiene confianza suficiente?)
    """

    @abstractmethod
    def can_extract(self, file_path: str) -> bool:
        """Determina si este extractor puede procesar el archivo.

        Args:
            file_path: Ruta absoluta al archivo.

        Returns:
            True si el extractor sabe manejar este tipo de archivo.
        """
        ...

    @abstractmethod
    def extract(self, file_path: str) -> ExtractionResult:
        """Ejecuta la extraccion sobre el archivo.

        Args:
            file_path: Ruta absoluta al archivo.

        Returns:
            Instancia de ExtractionResult con los datos obtenidos.
        """
        ...

    def validate(self, result: ExtractionResult) -> bool:
        """Valida que el resultado tenga confianza minima aceptable.

        Args:
            result: Resultado de extraccion a validar.

        Returns:
            True si result.confidence >= 0.5.

        Nota:
            El revisor SIEMPRE tiene la ultima palabra. Este umbral solo
            sirve para marcar el dato como 'revisar manualmente'.
        """
        return result.confidence >= 0.5
