"""
Base para todos los verificadores de normativa estructural.

Define el dataclass estandar ResultadoVerificacion que usan todos los
verificadores, asegurando consistencia en el formato de salida.
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ResultadoVerificacion:
    """Resultado estandar de cualquier verificacion normativa.

    Este dataclass garantiza que toda verificacion devuelve la misma
    estructura, facilitando:
      - Almacenamiento en base de datos (tabla Observacion)
      - Generacion de dictamen (score, resumen)
      - Presentacion en UI (colores, iconos, filtros)
      - Trazabilidad (cada resultado se vincula a normativa especifica)

    Attributes:
        verificador_id: Identificador unico del verificador (ej: 'MURO-ALT-001').
        nombre: Nombre corto y descriptivo de la verificacion.
        descripcion: Descripcion detallada de que se verifica.
        resultado: Estado de la verificacion.
            - CUMPLE: Cumple con la norma.
            - NO_CUMPLE: No cumple, requiere observacion.
            - NO_APLICA: No aplica a este proyecto.
            - SIN_EVIDENCIA: No se encontro evidencia en la documentacion.
        severidad: Nivel de gravedad del hallazgo.
            - INFO: Informacion adicional, no es observacion.
            - WARNING: Recomendacion, no bloqueante.
            - ERROR: Observacion que debe corregirse.
            - CRITICAL: Observacion critica, bloqueante para el dictamen.
        mensaje: Mensaje legible para el revisor con detalles del hallazgo.
        datos_utilizados: Valores especificos usados en la verificacion
            (ej: {"altura_muro": 3.5, "altura_max": 4.0}).
    """

    verificador_id: str
    nombre: str
    descripcion: str
    resultado: str  # "CUMPLE", "NO_CUMPLE", "NO_APLICA", "SIN_EVIDENCIA"
    severidad: str  # "INFO", "WARNING", "ERROR", "CRITICAL"
    mensaje: str
    datos_utilizados: dict = field(default_factory=dict)

    def __post_init__(self):
        """Valida que resultado y severidad tengan valores permitidos."""
        resultados_validos = {"CUMPLE", "NO_CUMPLE", "NO_APLICA", "SIN_EVIDENCIA"}
        severidades_validas = {"INFO", "WARNING", "ERROR", "CRITICAL"}

        if self.resultado not in resultados_validos:
            raise ValueError(
                f"Resultado '{self.resultado}' no valido. "
                f"Valores permitidos: {resultados_validos}"
            )
        if self.severidad not in severidades_validas:
            raise ValueError(
                f"Severidad '{self.severidad}' no valida. "
                f"Valores permitidos: {severidades_validas}"
            )
