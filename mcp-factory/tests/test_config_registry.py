"""Config loading and the server/agent registry."""
import pytest

from jarvis_mcp.core.errors import ConfigError
from jarvis_mcp.core.registry import SERVERS


def test_config_loads_agents(factory):
    assert set(factory.config.agents) == {"architect", "qa", "security"}
    assert "fs.read" in factory.config.agent("architect").capabilities


def test_unknown_agent_raises(factory):
    with pytest.raises(ConfigError):
        factory.config.agent("nobody")


def test_registry_lists_all_eight_servers(factory):
    names = {s["name"] for s in factory.registry.servers()}
    assert names == {s.name for s in SERVERS}
    assert len(names) == 8


def test_context_defaults_and_validates_agent(factory):
    ctx = factory.context("architect")
    assert ctx.agent == "architect"
    with pytest.raises(ConfigError):
        factory.context("ghost")
