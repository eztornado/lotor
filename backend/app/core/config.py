from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Configuración de la aplicación"""

    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "LoTor API"
    VERSION: str = "1.0.0"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # Database
    DATABASE_URL: str = "sqlite:///./lotor.db"

    # ML Models
    MODELS_PATH: str = "./app/ml/models"
    MAX_HISTORY_LENGTH: int = 52  # Semanas de historial a usar

    # El Gordo de la Primitiva Config
    NUM_NUMBERS: int = 5  # Números principales (1-54)
    NUM_KEY_RANGE: int = 10  # Número clave (0-9)
    MAX_NUMBER: int = 54

    # External APIs
    LOTERIAS_API_URL: str = "https://www.loteriasyapuestas.es"

    # Cache
    CACHE_TTL: int = 3600  # 1 hora

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Obtener configuración cacheada"""
    return Settings()


settings = get_settings()
