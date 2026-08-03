"""
The kernel must still be able to log after it migrates its own schema.

`run_migrations()` runs from the FastAPI lifespan, before the startup pipeline.
Alembic's env applies `alembic.ini`'s logging section through `fileConfig`,
which by default DISABLES every logger that already exists and drops the root
level to WARNING. The effect was total and completely silent: from the migration
line onward the kernel printed nothing — not the pipeline steps, not a failing
step, not `logger.error("Kernel startup failed")`, not the warning that says an
auth bypass is active.

Nothing raised, no test failed, and every diagnostic the kernel writes about its
own boot went to a disabled logger. That is why this is enforced.
"""
from __future__ import annotations

import logging

from app.db.migrations import run_migrations


def test_app_loggers_still_emit_after_migrating(caplog):
    """A logger created BEFORE the migration must still work after it."""
    logger = logging.getLogger("sexta-feira.pipeline.steps")
    logger.info("antes da migração")

    run_migrations()

    assert not logger.disabled, (
        "o logger do pipeline foi desabilitado pelo fileConfig do Alembic — "
        "o kernel fica mudo pelo resto do processo"
    )
    with caplog.at_level(logging.INFO, logger="sexta-feira.pipeline.steps"):
        logger.info("depois da migração")
    assert "depois da migração" in caplog.text


def test_root_level_is_not_lowered_by_alembic():
    """alembic.ini sets root to WARNING; that must not outlive the call."""
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    run_migrations()

    assert root.level == logging.INFO, (
        f"nível da raiz virou {logging.getLevelName(root.level)} depois da migração — "
        f"todo INFO do kernel (inclusive os passos do boot) é descartado"
    )


def test_root_handlers_are_left_alone():
    """The host's handlers must survive too.

    `alembic.ini` declares its own console handler, and applying it REPLACES
    whatever the process had — which is how this bug first showed itself: the
    kernel's own output kept working while pytest's capture handler vanished,
    so the two disagreed about whether logging worked at all.
    """
    root = logging.getLogger()
    marker = logging.NullHandler()
    root.addHandler(marker)
    try:
        run_migrations()
        assert marker in root.handlers, (
            "run_migrations() trocou os handlers da raiz — quem chamou perdeu a "
            "própria saída de log sem ser avisado"
        )
    finally:
        root.removeHandler(marker)


def test_a_logger_created_after_migrating_also_works(caplog):
    """The bug hit loggers that existed beforehand; prove new ones are fine too."""
    run_migrations()
    logger = logging.getLogger("sexta-feira.teste.pos-migracao")
    with caplog.at_level(logging.WARNING, logger="sexta-feira.teste.pos-migracao"):
        logger.warning("kernel ainda fala")
    assert "kernel ainda fala" in caplog.text
