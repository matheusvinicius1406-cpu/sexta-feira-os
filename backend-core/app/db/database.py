"""
Local database setup. Everything lives in a single SQLite file on YOUR disk
(./data/sexta_feira_os.db). This file is your second brain — never commit it.
"""
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

DATABASE_URL = settings.database_url

# Make sure the local ./data directory exists for the SQLite file.
if DATABASE_URL.startswith("sqlite"):
    db_path = DATABASE_URL.split("sqlite:///")[-1]
    Path(db_path).resolve().parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=settings.database_echo,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
