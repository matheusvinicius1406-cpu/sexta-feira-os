"""
Node — the contract every automation step implements (a Python class).

A Node *type* declares its metadata (type id, ports, category, version…) and a
Pydantic `Config` schema, validates its configuration, and implements the async
`execute`. Concrete node types (HTTP, transform, if/branch…) arrive in Phase 2
and via plugins; Phase 1 fixes the contract and the metadata model.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel, Field, field_validator

from app.automation.teia.domain.execution import ExecutionContext, NodeInput, NodeOutput


class NodeMetadata(BaseModel):
    """Static description of a node type."""

    type: str = Field(..., min_length=1)               # unique id: "http_request"
    name: str = Field(..., min_length=1)               # human label
    version: str = "1.0.0"
    category: str = "general"
    description: str = ""
    inputs: list[str] = Field(default_factory=lambda: ["main"])
    outputs: list[str] = Field(default_factory=lambda: ["main"])

    @field_validator("inputs", "outputs")
    @classmethod
    def _non_empty_unique(cls, ports: list[str]) -> list[str]:
        if len(ports) != len(set(ports)):
            raise ValueError("port names must be unique")
        if any(not p.strip() for p in ports):
            raise ValueError("port names must be non-empty")
        return ports


class EmptyConfig(BaseModel):
    """Default config schema for nodes that take no configuration."""


class Node(ABC):
    """Base class for all node types.

    Subclasses set `metadata` and (optionally) override `config_model`, then
    implement `execute`. The type is registered by class in the Registry; the
    engine instantiates it per execution (Phase 2).
    """

    metadata: ClassVar[NodeMetadata]
    config_model: ClassVar[type[BaseModel]] = EmptyConfig

    def validate_config(self, config: dict) -> BaseModel:
        """Parse/validate a node's configuration against its schema.

        Raises pydantic.ValidationError on bad config; returns the parsed model.
        """
        return self.config_model.model_validate(config or {})

    @abstractmethod
    async def execute(self, context: ExecutionContext, inputs: NodeInput) -> NodeOutput:
        """Run the node. Implemented by concrete node types (Phase 2+)."""
        raise NotImplementedError
