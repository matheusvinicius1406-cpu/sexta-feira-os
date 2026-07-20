"""Domain errors for the Teia automation platform."""
from __future__ import annotations


class TeiaDomainError(Exception):
    """Base class for all Teia domain errors."""


class WorkflowValidationError(TeiaDomainError):
    """A workflow failed validation. Carries the list of concrete problems."""

    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("; ".join(problems) if problems else "invalid workflow")


class WorkflowCycleError(TeiaDomainError):
    """A topological order was requested on a graph that contains a cycle."""
