"""
Programmatic schema migrations (Alembic).

The kernel brings its own database schema up to date on boot by running the
Alembic migrations — the single source of truth for the schema. This replaces
`create_all`, so schema changes are versioned and reproducible (SQLite locally,
Postgres if you ever grow into it).
"""
import logging
from pathlib import Path

from alembic.config import Config

from alembic import command

logger = logging.getLogger("sexta-feira.migrations")

_BACKEND_ROOT = Path(__file__).resolve().parents[2]  # backend-core/


def _alembic_config() -> Config:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "alembic"))
    return cfg


def run_migrations() -> None:
    """Upgrade the database to the latest revision (no-op if already current)."""
    command.upgrade(_alembic_config(), "head")
    logger.info("Database schema is up to date")
