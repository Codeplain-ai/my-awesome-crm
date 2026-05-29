import os
from pydantic_settings import BaseSettings

class Settings:
    """Lazy-loaded settings to prevent import-time failures."""
    
    @property
    def CRM_API_KEY(self) -> str | None:
        return os.environ.get("CRM_API_KEY")

    @property
    def CRM_PORT(self) -> int:
        return int(os.environ.get("CRM_PORT", "8000"))

    @property
    def CRM_DB_PATH(self) -> str:
        return os.environ.get("CRM_DB_PATH", "crm.db")

    @property
    def DATABASE_URL(self) -> str:
        return f"sqlite:///{self.CRM_DB_PATH}"

settings = Settings()