"""Per-agent permission model and critical-capability approval gate."""
import pytest

from jarvis_mcp.core.errors import ApprovalRequired, ConfigError, PermissionDenied


def test_granted_capability_allows(factory):
    d = factory.permissions.authorize("architect", "fs.read")
    assert d.allowed


def test_ungranted_capability_denied(factory):
    with pytest.raises(PermissionDenied):
        factory.permissions.authorize("qa", "memory.write")


def test_critical_capability_requires_approval_even_if_listed(factory):
    # github.merge is critical and granted to nobody -> ApprovalRequired
    with pytest.raises(ApprovalRequired):
        factory.permissions.authorize("architect", "github.merge")


def test_unknown_agent_raises(factory):
    with pytest.raises(ConfigError):
        factory.permissions.authorize("ghost", "fs.read")


def test_evaluate_is_side_effect_free(factory):
    d = factory.permissions.evaluate("qa", "testing.run")
    assert d.allowed and d.reason == "granted"
    d2 = factory.permissions.evaluate("qa", "github.write")
    assert not d2.allowed
