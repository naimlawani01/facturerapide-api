"""
Configuration de l'application FactureRapide.
Gestion centralisée de toutes les variables d'environnement.
"""

from functools import lru_cache
from typing import Optional, List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configuration principale de l'application.
    Les valeurs sont chargées depuis les variables d'environnement ou le fichier .env
    """
    
    # Configuration de l'application
    APP_NAME: str = "FactureRapide"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # Configuration du serveur
    HOST: str = "0.0.0.0"
    
    # Configuration de la base de données
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/facturerapide"
    DATABASE_URL_SYNC: str = "postgresql+psycopg://postgres:postgres@localhost:5432/facturerapide"
    
    # Configuration JWT
    SECRET_KEY: str = "your-super-secret-key-change-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Configuration CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Configuration PDF
    PDF_STORAGE_PATH: str = "./storage/invoices"
    PDF_RECEIPTS_PATH: str = "./storage/receipts"
    
    # Configuration Email (optionnel)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: str = "noreply@facturerapide.com"
    
    # URLs
    FRONTEND_URL: str = "http://localhost:3000"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT.lower() == "development"


@lru_cache()
def get_settings() -> Settings:
    """
    Retourne une instance unique des paramètres (singleton pattern).
    Utilise le cache LRU pour éviter de recharger les variables à chaque appel.
    """
    return Settings()


# Instance globale des paramètres
settings = get_settings()
