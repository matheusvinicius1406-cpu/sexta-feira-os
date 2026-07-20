"""
Serialization — a Workflow round-trips losslessly through dict, JSON and YAML.

Because the whole model is Pydantic v2, dict/JSON come for free; YAML is a thin
layer over the same dict. This is what lets a workflow be authored in code, saved
to a file, edited visually and executed by API/CLI — all the same object.
"""
from __future__ import annotations

from typing import Any

import yaml

from app.automation.teia.domain.errors import WorkflowValidationError
from app.automation.teia.domain.graph import Workflow


def to_dict(workflow: Workflow) -> dict[str, Any]:
    return workflow.model_dump(mode="json")


def to_json(workflow: Workflow, *, indent: int = 2) -> str:
    return workflow.model_dump_json(indent=indent)


def to_yaml(workflow: Workflow) -> str:
    return yaml.safe_dump(to_dict(workflow), sort_keys=False, allow_unicode=True)


def from_dict(data: dict[str, Any]) -> Workflow:
    return Workflow.model_validate(data)


def from_json(text: str) -> Workflow:
    return Workflow.model_validate_json(text)


def from_yaml(text: str) -> Workflow:
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise WorkflowValidationError(["conteúdo YAML não é um mapa de workflow"])
    return from_dict(data)
