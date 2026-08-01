"""
Cron — a small, exact five-field schedule matcher.

    ┌── minuto (0-59)
    │ ┌── hora (0-23)
    │ │ ┌── dia do mês (1-31)
    │ │ │ ┌── mês (1-12, ou jan..dec)
    │ │ │ │ ┌── dia da semana (0-6, 0=domingo, ou dom..sab / sun..sat)
    │ │ │ │ │
    0 7 * * 1-5      → 07:00, de segunda a sexta

Supports `*`, `n`, `a-b`, `*/passo`, `a-b/passo` and comma lists in every field.

Written here rather than pulled in as a dependency because it is ~100 lines of
pure arithmetic with no I/O, it is covered by tests, and it keeps the kernel's
install surface (and therefore its trust surface) unchanged — the ADR's "mature
library first" rule is about not rebuilding an engine, not about a date match.

Day-of-month and day-of-week follow the classic Vixie cron rule: when BOTH are
restricted, a day matching EITHER fires.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

_MONTHS = {
    "jan": 1, "feb": 2, "fev": 2, "mar": 3, "apr": 4, "abr": 4, "may": 5, "mai": 5,
    "jun": 6, "jul": 7, "aug": 8, "ago": 8, "sep": 9, "set": 9, "oct": 10, "out": 10,
    "nov": 11, "dec": 12, "dez": 12,
}
_WEEKDAYS = {
    "sun": 0, "dom": 0, "mon": 1, "seg": 1, "tue": 2, "ter": 2, "wed": 3, "qua": 3,
    "thu": 4, "qui": 4, "fri": 5, "sex": 5, "sat": 6, "sab": 6,
}

_FIELDS = (
    ("minuto", 0, 59, {}),
    ("hora", 0, 23, {}),
    ("dia", 1, 31, {}),
    ("mês", 1, 12, _MONTHS),
    ("dia da semana", 0, 7, _WEEKDAYS),      # 7 is also Sunday
)

# Readable shorthands, so a workflow can say "@diario" instead of "0 0 * * *".
ALIASES = {
    "@hourly": "0 * * * *",
    "@horario": "0 * * * *",
    "@daily": "0 0 * * *",
    "@diario": "0 0 * * *",
    "@midnight": "0 0 * * *",
    "@weekly": "0 0 * * 0",
    "@semanal": "0 0 * * 0",
    "@monthly": "0 0 1 * *",
    "@mensal": "0 0 1 * *",
    "@yearly": "0 0 1 1 *",
    "@anual": "0 0 1 1 *",
}


class CronError(ValueError):
    """The cron expression could not be parsed."""


def _parse_value(token: str, low: int, high: int, names: dict[str, int], field: str) -> int:
    key = token.strip().lower()
    if key in names:
        return names[key]
    if not key.lstrip("-").isdigit():
        raise CronError(f"campo '{field}': '{token}' não é um número nem um nome conhecido")
    value = int(key)
    if not low <= value <= high:
        raise CronError(f"campo '{field}': {value} fora do intervalo {low}-{high}")
    return value


def _parse_field(
    spec: str, low: int, high: int, names: dict[str, int], field: str
) -> set[int]:
    allowed: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            raise CronError(f"campo '{field}': lista com item vazio")

        body, _, step_text = part.partition("/")
        step = 1
        if _:
            if not step_text.strip().isdigit() or int(step_text) < 1:
                raise CronError(f"campo '{field}': passo '/{step_text}' inválido")
            step = int(step_text)

        body = body.strip()
        if body == "*":
            start, end = low, high
        elif "-" in body[1:]:                       # body[1:] keeps a leading '-' safe
            start_text, _, end_text = body.partition("-")
            start = _parse_value(start_text, low, high, names, field)
            end = _parse_value(end_text, low, high, names, field)
            if start > end:
                raise CronError(f"campo '{field}': intervalo invertido '{body}'")
        else:
            start = _parse_value(body, low, high, names, field)
            end = start if step == 1 else high

        allowed.update(range(start, end + 1, step))

    if not allowed:
        raise CronError(f"campo '{field}': não corresponde a nenhum valor")
    return allowed


@dataclass(frozen=True)
class CronSchedule:
    """A parsed cron expression that can be asked whether an instant matches."""

    expression: str
    minutes: frozenset[int]
    hours: frozenset[int]
    days: frozenset[int]
    months: frozenset[int]
    weekdays: frozenset[int]
    day_restricted: bool
    weekday_restricted: bool

    def matches(self, moment: datetime) -> bool:
        """Does this instant (to the minute) fall on the schedule?"""
        if moment.minute not in self.minutes or moment.hour not in self.hours:
            return False
        if moment.month not in self.months:
            return False

        # Python: Monday=0..Sunday=6. Cron: Sunday=0..Saturday=6.
        weekday = (moment.weekday() + 1) % 7
        day_ok = moment.day in self.days
        weekday_ok = weekday in self.weekdays

        if self.day_restricted and self.weekday_restricted:
            return day_ok or weekday_ok
        if self.day_restricted:
            return day_ok
        if self.weekday_restricted:
            return weekday_ok
        return True

    def describe(self) -> str:
        return f"cron({self.expression})"


def parse_cron(expression: str) -> CronSchedule:
    """Parse a five-field cron expression (or an @alias). Raises CronError."""
    raw = (expression or "").strip()
    if not raw:
        raise CronError("expressão cron vazia")
    resolved = ALIASES.get(raw.lower(), raw)

    parts = resolved.split()
    if len(parts) != 5:
        raise CronError(
            f"'{expression}' tem {len(parts)} campo(s); o cron precisa de 5 "
            f"(minuto hora dia mês dia-da-semana)"
        )

    parsed = [
        _parse_field(part, low, high, names, field)
        for part, (field, low, high, names) in zip(parts, _FIELDS, strict=True)
    ]
    minutes, hours, days, months, weekdays = parsed

    if 7 in weekdays:                       # both 0 and 7 mean Sunday
        weekdays = (weekdays - {7}) | {0}

    return CronSchedule(
        expression=raw,
        minutes=frozenset(minutes),
        hours=frozenset(hours),
        days=frozenset(days),
        months=frozenset(months),
        weekdays=frozenset(weekdays),
        day_restricted=parts[2].strip() != "*",
        weekday_restricted=parts[4].strip() != "*",
    )
