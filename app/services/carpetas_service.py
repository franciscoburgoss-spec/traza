"""
Servicio de gestion de estructura de carpetas para proyectos (R7).

Crea automaticamente la estructura /PDP/ING/{acronimo}/ con subcarpetas
organizadas por disciplina cuando se genera una nueva solicitud ING.

Estructura generada:
    /PDP/ING/{ACRONIMO}/
    ├── 01_ING/           # Solicitud y documentos de ingreso
    ├── 02_MDS/           # Mecanica de suelos
    ├── 03_EST/           # Estructuras
    ├── 04_HAB/           # Habitabilidad
    ├── 05_URB/           # Urbanizacion
    ├── 06_REV/           # Revisiones y dictamenes
    └── 99_ANEXOS/        # Anexos varios
"""
import os
from typing import List, Optional

from app.config import settings


# Subcarpetas estandar para cada proyecto
SUBCARPETAS_PROYECTO = [
    ("01_ING", "Solicitud y documentos de ingreso"),
    ("02_MDS", "Mecanica de suelos"),
    ("03_EST", "Estructuras"),
    ("04_HAB", "Habitabilidad"),
    ("05_URB", "Urbanizacion"),
    ("06_REV", "Revisiones y dictamenes"),
    ("99_ANEXOS", "Anexos varios"),
]

# Mapping de modulo a subcarpeta para asociar documentos
MODULO_A_CARPETA = {
    "MDS": "02_MDS",
    "EST": "03_EST",
    "HAB": "04_HAB",
    "URB": "05_URB",
}


class EstructuraCarpetasService:
    """Servicio para crear y gestionar la estructura de carpetas de proyectos."""

    @staticmethod
    def _ruta_base() -> str:
        """Retorna la ruta base absoluta para /PDP/ING/."""
        return os.path.join(settings.PDP_ING_DIR, "ING")

    @staticmethod
    def ruta_para_acronimo(acronimo: str) -> str:
        """
        Genera la ruta completa para un proyecto dado su acronimo.

        Ejemplo:
            >>> EstructuraCarpetasService.ruta_para_acronimo("H26RANCA")
            '/abs/path/PDP/ING/H26RANCA'
        """
        return os.path.join(EstructuraCarpetasService._ruta_base(), acronimo)

    @staticmethod
    def ruta_para_modulo(acronimo: str, modulo: str) -> Optional[str]:
        """
        Retorna la ruta de la subcarpeta correspondiente a un modulo.

        Args:
            acronimo: Acronimo del proyecto
            modulo: Codigo de modulo (MDS, EST, HAB, URB)

        Returns:
            Ruta absoluta o None si el modulo no tiene carpeta asignada
        """
        carpeta = MODULO_A_CARPETA.get(modulo.upper())
        if not carpeta:
            return None
        return os.path.join(
            EstructuraCarpetasService.ruta_para_acronimo(acronimo),
            carpeta
        )

    @staticmethod
    def crear_estructura(acronimo: str) -> str:
        """
        Crea la estructura de carpetas completa para un proyecto.

        Args:
            acronimo: Acronimo del proyecto (ej: "H26RANCA")

        Returns:
            Ruta base creada del proyecto

        Raises:
            OSError: Si no se pueden crear las carpetas
        """
        ruta_base = EstructuraCarpetasService.ruta_para_acronimo(acronimo)

        # Crear carpeta raiz del proyecto
        os.makedirs(ruta_base, exist_ok=True)

        # Crear subcarpetas
        for nombre, descripcion in SUBCARPETAS_PROYECTO:
            ruta_sub = os.path.join(ruta_base, nombre)
            os.makedirs(ruta_sub, exist_ok=True)

        return ruta_base

    @staticmethod
    def existe_estructura(acronimo: str) -> bool:
        """Verifica si ya existe la estructura de carpetas para un acronimo."""
        ruta = EstructuraCarpetasService.ruta_para_acronimo(acronimo)
        return os.path.isdir(ruta)

    @staticmethod
    def listar_subcarpetas(acronimo: str) -> List[dict]:
        """
        Lista las subcarpetas existentes para un proyecto.

        Returns:
            Lista de dicts con nombre, ruta y existe
        """
        ruta_base = EstructuraCarpetasService.ruta_para_acronimo(acronimo)
        resultado = []

        for nombre, descripcion in SUBCARPETAS_PROYECTO:
            ruta = os.path.join(ruta_base, nombre)
            resultado.append({
                "nombre": nombre,
                "descripcion": descripcion,
                "ruta": ruta,
                "existe": os.path.isdir(ruta),
            })

        return resultado

    @staticmethod
    def eliminar_estructura(acronimo: str) -> bool:
        """
        Elimina la estructura de carpetas de un proyecto.

        Returns:
            True si se elimino, False si no existia
        """
        import shutil
        ruta = EstructuraCarpetasService.ruta_para_acronimo(acronimo)
        if os.path.isdir(ruta):
            shutil.rmtree(ruta)
            return True
        return False
