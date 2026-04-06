"""
Database session and engine configuration.

Uses SQLModel (SQLAlchemy + Pydantic) for ORM capabilities.
"""
from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
from app.core.config import get_settings

settings = get_settings()

# Create database engine with connection pooling
engine = create_engine(
    settings.db_url,
    echo=settings.APP_ENV == "development",  # Log SQL queries in dev
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,  # Enable connection health checks
)


def create_db_and_tables() -> None:
    """Create all database tables from models."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Dependency for getting database sessions in FastAPI routes."""
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
