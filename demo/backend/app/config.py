# backend/app/config.py
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # Приложение
    APP_NAME: str = "TaskFlow"
    DEBUG: bool = True

    # База данных
    DATABASE_URL: str = "sqlite:///./taskflow.db"

    # JWT
    SECRET_KEY: str = "change-me-in-production-please"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 часов

    class Config:
        env_file = ".env"


settings = Settings()
