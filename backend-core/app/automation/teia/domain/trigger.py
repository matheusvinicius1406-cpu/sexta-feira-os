"""
Trigger — the contract that starts a workflow execution (a Python class).

Like Node, a Trigger *type* declares metadata and a Pydantic config schema.
Concrete triggers (webhook, schedule, event-bus bridge, file-watch…) and the
machinery that arms them arrive in Phase 5; Phase 1 fixes the contract.
"""
from __future__ import annotations

from abc import ABC
from typing import ClassVar

from pydantic import BaseModel, Field

from app.automation.teia.domain.node import EmptyConfig


class TriggerMetadata(BaseModel):
    """Static description of a trigger type."""

    type: str = Field(..., min_length=1)               # "schedule", "webhook", "event"
    name: str = Field(..., min_length=1)
    version: str = "1.0.0"
    category: str = "trigger"
    description: str = ""


class Trigger(ABC):
    """Base class for all trigger types.

    A trigger produces workflow executions from the outside world (time, HTTP,
    kernel events, files). Phase 1 only fixes the type contract; arming/dispatch
    is Phase 5.
    """

    metadata: ClassVar[TriggerMetadata]
    config_model: ClassVar[type[BaseModel]] = EmptyConfig

    def validate_config(self, config: dict) -> BaseModel:
        return self.config_model.model_validate(config or {})
