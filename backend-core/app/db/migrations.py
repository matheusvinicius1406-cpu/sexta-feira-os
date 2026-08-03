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
    """Upgrade the database to the latest revision (no-op if already current).

    The root log level is saved and restored around the upgrade. `alembic.ini`
    carries its own logging section — sensible for the `alembic` CLI, wrong in
    here — and applying it drops the root logger to WARNING. Running migrations
    on boot therefore used to silence the kernel's own INFO logging for the rest
    of the process: the startup pipeline ran, steps succeeded or failed, and not
    one line of it was ever printed.

    `alembic/env.py` stops fileConfig from DISABLING the app's loggers; this
    restores the LEVEL it lowers and the HANDLERS it swaps out. Migrating the
    schema is not a reason to reconfigure the host process's logging, so this
    function leaves it exactly as it found it.
    """
    root = logging.getLogger()
    level_before = root.level
    handlers_before = root.handlers[:]
    try:
        command.upgrade(_alembic_config(), "head")
    finally:
        root.setLevel(level_before)
        root.handlers[:] = handlers_before
    logger.info("Database schema is up to date")
