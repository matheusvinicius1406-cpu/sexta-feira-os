"""
The boot-time check that says which configured models Ollama does not have.

Written after `nomic-embed-text` turned out to be missing from a running kernel.
Nothing announced it. Every memory write logged
`Embedding failed (stored without vector): 404` in the middle of normal use and
carried on, so memories were persisted with no vector and semantic recall
returned nothing — no error surfaced, answers were merely worse.

The matcher below is the whole check, and it has to be right in both directions:
a false alarm at every boot trains the owner to ignore the warning, which is the
same as not having one.
"""
from __future__ import annotations

from app.kernel.pipeline.steps.core_steps import model_present

INSTALLED = {"qwen3-vl:4b", "nomic-embed-text:latest"}


def test_exact_tag_matches():
    assert model_present("qwen3-vl:4b", INSTALLED)


def test_untagged_name_matches_the_installed_tag():
    """Config says `nomic-embed-text`; Ollama lists `nomic-embed-text:latest`.

    A plain membership test calls this missing and warns about a model that is
    right there.
    """
    assert model_present("nomic-embed-text", INSTALLED)
    assert model_present("qwen3-vl", INSTALLED), "nome sem tag deve casar com qwen3-vl:4b"


def test_a_different_tag_is_not_a_match():
    """The dangerous false negative: treating any tag as good enough.

    Having qwen3-vl:2b does not mean qwen3-vl:4b is present — the kernel would
    stay quiet and then fail at the first request with a 404 from Ollama.
    """
    assert not model_present("qwen3-vl:2b", INSTALLED)
    assert not model_present("qwen3-vl:8b", INSTALLED)


def test_absent_models_are_reported():
    assert not model_present("mistral", INSTALLED)
    assert not model_present("nomic-embed-text", set())


def test_the_models_the_old_split_brain_used_are_no_longer_required():
    """The two-model era is over; neither may be reported as still needed."""
    assert not model_present("llava:7b", INSTALLED)
    assert not model_present("qwen2.5:3b", INSTALLED)


def test_nothing_installed_means_nothing_present():
    for name in ("qwen3-vl:4b", "nomic-embed-text"):
        assert not model_present(name, set())
