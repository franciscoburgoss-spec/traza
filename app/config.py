"""Configuracion centralizada via Pydantic Settings."""
import os
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    DATABASE_URL: str = Field(default="sqlite:///./traza.db")
    DEBUG: bool = Field(default=False)
    SESSION_PREFIX: str = Field(default="local")
    # R7: Ruta base para estructura de carpetas de proyectos
    RUTA_BASE_PDP: str = Field(default="./PDP")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def TEMPLATES_DIR(self) -> str:
        import os
        return os.path.join(os.path.dirname(__file__), "templates")

    @property
    def STATIC_DIR(self) -> str:
        import os
        return os.path.join(os.path.dirname(__file__), "static")

    @property
    def PDP_ING_DIR(self) -> str:
        """Ruta base para estructura de carpetas /PDP/ING/ (R7)."""
        return os.path.abspath(self.RUTA_BASE_PDP)


settings = Settings()


def get_settings() -> Settings:
    """Factory para obtener settings (compatible con Depends)."""
    return settings
