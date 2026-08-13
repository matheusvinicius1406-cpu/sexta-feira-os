"""
The decisions the optimizer makes from its measurements.

The probes themselves need a live Ollama and minutes of CPU, so what is pinned
here is the judgement applied to the numbers — which is where a tuner is
actually wrong. A knee-finder that always returns the biggest rung, or a thread
picker that always takes every core, produces confident output and no insight.
"""
from __future__ import annotations

from app.brain.engine import tuned_options
from app.brain.optimizer import ContextPoint, ThreadPoint, _best_threads, _knee


def ctx(tokens: int, ms: float) -> ContextPoint:
    return ContextPoint(tokens=tokens, prefill_s=tokens * ms / 1000, ms_per_token=ms)


# ---------------------------------------------------------------- num_ctx


def test_the_knee_is_where_cost_per_token_jumps():
    """Flat up to 2048, then it blows up: 2048 is the useful window."""
    points = [ctx(256, 10.0), ctx(512, 10.2), ctx(1024, 10.5), ctx(2048, 11.0), ctx(4096, 24.0)]
    assert _knee(points) == 2048


def test_a_machine_that_stays_flat_gets_the_largest_window():
    points = [ctx(256, 10.0), ctx(512, 10.1), ctx(1024, 10.0), ctx(2048, 10.3)]
    assert _knee(points) == 2048


def test_a_machine_that_degrades_immediately_gets_the_smallest():
    points = [ctx(256, 10.0), ctx(512, 30.0), ctx(1024, 62.0)]
    assert _knee(points) == 256


def test_no_measurements_recommend_nothing():
    """Zero means "unmeasured", and unmeasured must not become a setting."""
    assert _knee([]) == 0


# ---------------------------------------------------------------- num_thread


def test_a_clear_winner_wins():
    points = [ThreadPoint(1, 4.0), ThreadPoint(2, 7.5), ThreadPoint(3, 8.0), ThreadPoint(4, 12.0)]
    assert _best_threads(points, cores=4, notes=[]) == 4


def test_a_near_tie_leaves_a_core_for_the_system():
    """3 threads at 97% of 4 is the better setting on a machine that is also
    serving HTTP, a database and speech synthesis."""
    points = [ThreadPoint(1, 4.0), ThreadPoint(2, 7.0), ThreadPoint(3, 9.7), ThreadPoint(4, 10.0)]
    notes: list[str] = []
    assert _best_threads(points, cores=4, notes=notes) == 3
    assert notes, "a escolha por 3 threads não foi explicada"


def test_using_every_core_wins_when_it_actually_wins():
    """A 20% gain is worth the contention; the tie-break must not eat it."""
    points = [ThreadPoint(3, 8.0), ThreadPoint(4, 10.0)]
    assert _best_threads(points, cores=4, notes=[]) == 4


def test_single_core_machine_is_handled():
    assert _best_threads([ThreadPoint(1, 3.0)], cores=1, notes=[]) == 1


def test_no_measurements_recommend_nothing_for_threads():
    assert _best_threads([], cores=4, notes=[]) == 0


# ---------------------------------------------------------------- applying them


def test_unmeasured_knobs_are_omitted_not_sent_as_zero():
    """Ollama reads `num_thread: 0` as an instruction, not as an absence.

    Sending it would pin an unprofiled machine to a bad setting, which is worse
    than never having run the optimizer.
    """
    options = tuned_options(temperature=0.7, num_predict=512)
    assert "num_ctx" not in options
    assert "num_thread" not in options
    assert options["temperature"] == 0.7


def test_measured_knobs_are_applied(monkeypatch):
    from app.brain import engine

    monkeypatch.setattr(engine.settings, "brain_num_ctx", 2048)
    monkeypatch.setattr(engine.settings, "brain_num_thread", 3)

    options = tuned_options(temperature=0.7)
    assert options["num_ctx"] == 2048
    assert options["num_thread"] == 3
    assert options["temperature"] == 0.7
