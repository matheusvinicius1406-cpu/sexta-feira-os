"""PathGuard and CommandGuard — the security-critical core."""
import pytest

from jarvis_mcp.core.errors import GuardViolation
from jarvis_mcp.core.guard import CommandGuard


def test_reads_allowed_file(factory):
    p = factory.path_guard.resolve_safe("backend-core/app.py")
    assert p.name == "app.py"


def test_blocks_path_outside_allowlist(factory):
    with pytest.raises(GuardViolation):
        factory.path_guard.resolve_safe("secret_stuff/passwords.txt")


def test_blocks_traversal_escape(factory):
    with pytest.raises(GuardViolation):
        factory.path_guard.resolve_safe("../../etc/passwd")


def test_blocks_sensitive_env_even_in_allowed_dir(factory):
    with pytest.raises(GuardViolation):
        factory.path_guard.resolve_safe("backend-core/.env")


def test_blocks_key_files(factory):
    with pytest.raises(GuardViolation):
        factory.path_guard.resolve_safe("src/server.key")


def test_is_sensitive_matches_nested_env(factory):
    assert factory.path_guard.is_sensitive("backend-core/sub/.env")
    assert factory.path_guard.is_sensitive("a/b/c.key")
    assert not factory.path_guard.is_sensitive("backend-core/app.py")


def test_command_guard_allows_exact():
    g = CommandGuard(("python -m pytest",))
    assert g.validate("python -m pytest") == ["python", "-m", "pytest"]


def test_command_guard_allows_extra_args():
    g = CommandGuard(("python -m pytest",))
    assert g.validate("python -m pytest tests/test_x.py")[-1] == "tests/test_x.py"


def test_command_guard_rejects_unlisted():
    g = CommandGuard(("python -m pytest",))
    with pytest.raises(GuardViolation):
        g.validate("python -m evil")


def test_command_guard_blocks_dangerous_token_even_if_prefixed():
    g = CommandGuard(("python -m pytest",))
    with pytest.raises(GuardViolation):
        g.validate("python -m pytest; rm -rf /")


def test_command_guard_blocks_network_egress():
    g = CommandGuard(("curl something",))  # even if someone allow-lists it
    with pytest.raises(GuardViolation):
        g.validate("curl http://evil")
