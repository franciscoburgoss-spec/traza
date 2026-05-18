"""
Verificadores de normativa para componentes HAB (muros y caletas).

Exporta las funciones puras de verificacion y el dataclass base
para resultados de verificacion.
"""

from .base import ResultadoVerificacion
from .muro import (
    verificar_altura_muro,
    verificar_drenaje_muro,
    verificar_fc_muro,
    verificar_estabilidad_vuelco,
    verificar_muro_completo,
)
from .caletera import (
    verificar_longitud_minima,
    verificar_ancho_corona,
    verificar_pendiente_maxima,
    verificar_espesor_minimo,
    verificar_caletera_completo,
)

__all__ = [
    "ResultadoVerificacion",
    # Muro
    "verificar_altura_muro",
    "verificar_drenaje_muro",
    "verificar_fc_muro",
    "verificar_estabilidad_vuelco",
    "verificar_muro_completo",
    # Caletera
    "verificar_longitud_minima",
    "verificar_ancho_corona",
    "verificar_pendiente_maxima",
    "verificar_espesor_minimo",
    "verificar_caletera_completa",
]
