"""
The trigger types — what can start an automation.

Each is a `Trigger` subclass: metadata plus a Pydantic config schema, exactly like
a node. They are declarative; `TriggerManager` is what actually arms them.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.automation.teia.domain.trigger import Trigger, TriggerMetadata
from app.automation.teia.triggers.cron import CronError, parse_cron


class ManualConfig(BaseModel):
    pass


class ManualTrigger(Trigger):
    """Runs only when the owner (or the brain) asks for it."""

    metadata = TriggerMetadata(
        type="manual", name="Manual",
        description="Executa quando você pede — pela API, pela voz ou pelo CLI.",
    )
    config_model = ManualConfig


class ScheduleConfig(BaseModel):
    cron: str = Field(..., min_length=1, description="ex.: '0 7 * * 1-5' ou '@diario'")
    fuso: str = Field(default="", description="IANA, ex.: America/Sao_Paulo (vazio = local)")

    @field_validator("cron")
    @classmethod
    def _valid_cron(cls, value: str) -> str:
        try:
            parse_cron(value)
        except CronError as e:
            raise ValueError(str(e)) from e
        return value


class ScheduleTrigger(Trigger):
    """Fires on a cron schedule, to the minute."""

    metadata = TriggerMetadata(
        type="agenda", name="Agenda (cron)",
        description="Executa em horários definidos por uma expressão cron.",
    )
    config_model = ScheduleConfig


class IntervalConfig(BaseModel):
    segundos: int = Field(..., ge=30, le=86400, description="mínimo 30s")


class IntervalTrigger(Trigger):
    """Fires every N seconds — for watchdogs and pollers."""

    metadata = TriggerMetadata(
        type="intervalo", name="Intervalo",
        description="Executa repetidamente a cada N segundos.",
    )
    config_model = IntervalConfig


class EventConfig(BaseModel):
    tipo: str = Field(
        ..., min_length=1,
        description="tipo do evento, ou prefixo com '*' (ex.: 'agendamento.*')",
    )


class EventTrigger(Trigger):
    """Fires when a matching event lands on the kernel's EventBus.

    This is what makes automations reactive: `usuario.acordou`,
    `agendamento.venceu`, `meta.concluida` — anything the kernel publishes.
    """

    metadata = TriggerMetadata(
        type="evento", name="Evento do kernel",
        description="Executa quando um evento do barramento casa com o padrão.",
    )
    config_model = EventConfig


class WebhookConfig(BaseModel):
    caminho: str = Field(..., min_length=1, description="ex.: 'captura-rapida'")
    segredo: str = Field(
        default="",
        description="se preenchido, exige o header X-Teia-Secret com este valor",
    )

    @field_validator("caminho")
    @classmethod
    def _clean(cls, value: str) -> str:
        cleaned = value.strip().strip("/")
        if not cleaned or "/" in cleaned:
            raise ValueError("o caminho deve ser um único segmento, sem '/'")
        return cleaned


class WebhookTrigger(Trigger):
    """Fires on POST /api/v1/automations/webhook/{caminho}."""

    metadata = TriggerMetadata(
        type="webhook", name="Webhook",
        description="Executa quando algo chama a URL de webhook da automação.",
    )
    config_model = WebhookConfig


BUILTIN_TRIGGERS = [
    ManualTrigger, ScheduleTrigger, IntervalTrigger, EventTrigger, WebhookTrigger,
]
