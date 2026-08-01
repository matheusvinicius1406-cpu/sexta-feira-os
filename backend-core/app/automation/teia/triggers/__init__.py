"""Triggers — what starts an automation (Phase 5)."""
from app.automation.teia.registry import Registry
from app.automation.teia.triggers.cron import (
    ALIASES,
    CronError,
    CronSchedule,
    parse_cron,
)
from app.automation.teia.triggers.manager import Armed, TriggerManager
from app.automation.teia.triggers.types import (
    BUILTIN_TRIGGERS,
    EventTrigger,
    IntervalTrigger,
    ManualTrigger,
    ScheduleTrigger,
    WebhookTrigger,
)


def register_builtin_triggers(registry: Registry) -> Registry:
    """Register every built-in trigger type."""
    for trigger_cls in BUILTIN_TRIGGERS:
        registry.register_trigger(trigger_cls)
    return registry


def trigger_catalogue() -> list[dict]:
    return [
        {
            "type": t.metadata.type,
            "name": t.metadata.name,
            "description": t.metadata.description,
            "config_schema": t.config_model.model_json_schema(),
        }
        for t in BUILTIN_TRIGGERS
    ]


__all__ = [
    "ALIASES",
    "Armed",
    "BUILTIN_TRIGGERS",
    "CronError",
    "CronSchedule",
    "EventTrigger",
    "IntervalTrigger",
    "ManualTrigger",
    "ScheduleTrigger",
    "TriggerManager",
    "WebhookTrigger",
    "parse_cron",
    "register_builtin_triggers",
    "trigger_catalogue",
]
