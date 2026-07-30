"""
Engine interfaces for Sexta-Feira OS Kernel.

Each cognitive capability (memory, cognition, decision, etc.) is
an Engine with a standard lifecycle and health check.

Every Engine in Python has an exact C# counterpart in
apps/maui/CognitiveHUD/Services/IEngine.cs
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class IEngine(ABC):
    """Contract that every Kernel engine must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique engine identifier (e.g. 'Memory', 'Cognition')."""
        ...

    @abstractmethod
    async def initialize(self) -> None:
        """Start the engine: load models, connect to services, etc."""
        ...

    @abstractmethod
    async def health(self) -> bool:
        """Return True if the engine is operational."""
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """Gracefully stop the engine and release resources."""
        ...
