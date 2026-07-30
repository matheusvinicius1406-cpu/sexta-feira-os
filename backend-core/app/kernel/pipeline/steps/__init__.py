"""
Pipeline steps — each encapsulates a single kernel initialization concern.

Every step implements BaseStep with:
  - execute(kernel) → async
  - name property
  - timeout property
"""
from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.di import Kernel

logger = logging.getLogger("sexta-feira.pipeline.steps")


class BaseStep(ABC):
    """Base class for all pipeline steps."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Step identifier used for logging and event names."""
        ...

    @property
    def timeout(self) -> float:
        """Maximum execution time before the step is considered failed."""
        return 30.0

    @property
    def critical(self) -> bool:
        """If True, pipeline halts on step failure."""
        return True

    @abstractmethod
    async def execute(self, kernel: Kernel) -> None:
        """Execute the step against the kernel singleton."""
        ...
