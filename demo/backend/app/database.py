# backend/app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

# Для SQLite нужен флаг check_same_thread=False
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=settings.DEBUG,  # логирует SQL запросы в режиме DEBUG
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """
    Dependency для FastAPI — открывает сессию БД на время запроса,
    гарантированно закрывает после.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
