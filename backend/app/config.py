import os
from pathlib import Path
from pydantic_settings import BaseSettings

# Build paths inside the project relative to backend root
BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    APP_NAME: str = "AI Support Ticket Triage & Auto-Reply Copilot"
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    DATABASE_URL: str = f"sqlite:///{BACKEND_DIR / 'tickets.db'}"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = str(BACKEND_DIR / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()

