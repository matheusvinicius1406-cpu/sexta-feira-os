"""
Cron parsing and matching (Teia triggers).

Pure arithmetic — no DB, no clock of its own. Everything is asserted against
explicit datetimes so a test failure names the exact minute that broke.
"""
from datetime import datetime

import pytest

from app.automation.teia.triggers.cron import CronError, parse_cron


def at(text: str) -> datetime:
    return datetime.fromisoformat(text)


# ---------------------------------------------------------------- parsing


def test_every_field_wildcard_matches_any_minute():
    schedule = parse_cron("* * * * *")
    assert schedule.matches(at("2026-08-01 03:17"))
    assert schedule.matches(at("2026-12-25 23:59"))


def test_fixed_time():
    schedule = parse_cron("30 7 * * *")
    assert schedule.matches(at("2026-08-01 07:30"))
    assert not schedule.matches(at("2026-08-01 07:31"))
    assert not schedule.matches(at("2026-08-01 08:30"))


def test_ranges_and_lists():
    schedule = parse_cron("0 9,17 * * 1-5")          # 09:00 and 17:00, Mon-Fri
    assert schedule.matches(at("2026-08-03 09:00"))   # Monday
    assert schedule.matches(at("2026-08-07 17:00"))   # Friday
    assert not schedule.matches(at("2026-08-08 09:00"))  # Saturday
    assert not schedule.matches(at("2026-08-03 10:00"))


def test_step_values():
    schedule = parse_cron("*/15 * * * *")
    minutes = [m for m in range(60) if schedule.matches(at(f"2026-08-01 05:{m:02d}"))]
    assert minutes == [0, 15, 30, 45]


def test_step_over_a_range():
    schedule = parse_cron("0 8-18/6 * * *")
    hours = [h for h in range(24) if schedule.matches(at(f"2026-08-01 {h:02d}:00"))]
    assert hours == [8, 14]


def test_sunday_is_both_zero_and_seven():
    for expression in ("0 12 * * 0", "0 12 * * 7"):
        schedule = parse_cron(expression)
        assert schedule.matches(at("2026-08-02 12:00"))       # a Sunday
        assert not schedule.matches(at("2026-08-03 12:00"))   # Monday


def test_month_and_weekday_names():
    schedule = parse_cron("0 6 * jan-mar seg")
    assert schedule.matches(at("2026-02-02 06:00"))            # Monday, February
    assert not schedule.matches(at("2026-05-04 06:00"))        # Monday, May


def test_aliases():
    assert parse_cron("@diario").matches(at("2026-08-01 00:00"))
    assert parse_cron("@semanal").matches(at("2026-08-02 00:00"))   # Sunday
    assert parse_cron("@hourly").matches(at("2026-08-01 13:00"))


def test_day_or_weekday_when_both_restricted():
    """Classic Vixie rule: with both day-of-month and weekday set, EITHER fires."""
    schedule = parse_cron("0 0 1 * 0")
    assert schedule.matches(at("2026-09-01 00:00"))    # the 1st (a Tuesday)
    assert schedule.matches(at("2026-08-02 00:00"))    # a Sunday (not the 1st)
    assert not schedule.matches(at("2026-08-04 00:00"))  # neither


# ---------------------------------------------------------------- errors


@pytest.mark.parametrize(
    "expression",
    [
        "",                 # empty
        "0 7 * *",          # four fields
        "0 7 * * * *",      # six fields
        "60 7 * * *",       # minute out of range
        "0 25 * * *",       # hour out of range
        "0 7 * * abc",      # unknown weekday name
        "0 7 * * 5-1",      # inverted range
        "*/0 * * * *",      # zero step
    ],
)
def test_invalid_expressions_are_rejected(expression):
    with pytest.raises(CronError):
        parse_cron(expression)


def test_error_message_names_the_field():
    with pytest.raises(CronError, match="hora"):
        parse_cron("0 99 * * *")
