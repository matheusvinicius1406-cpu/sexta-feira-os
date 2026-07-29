"""Alembic environment — wired to the app's models and .env-driven URL."""
from logging.config import fileConfig
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

from alembic import context

# Load .env so DATABASE_URL is available, exactly like the app does.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# Import metadata + settings from the app (single source of truth).
from app.core.config import settings  # noqa: E402
from app.db.database import Base  # noqa: E402
from app.models import models  # noqa: E402,F401  (registers all tables on Base)

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,  # SQLite needs batch mode for ALTER
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
