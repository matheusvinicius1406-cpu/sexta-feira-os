"""Service-layer behavior: filesystem, memory, documentation, testing, security, github."""
import pytest

from jarvis_mcp.core.errors import GuardViolation, NotFound, PermissionDenied, ValidationError
from jarvis_mcp.services.documentation import DocumentationService
from jarvis_mcp.services.filesystem import FilesystemService
from jarvis_mcp.services.github import GitHubService
from jarvis_mcp.services.memory import MemoryService
from jarvis_mcp.services.security import SecurityService
from jarvis_mcp.services.testing import TestingService


# --- filesystem -----------------------------------------------------------
def test_fs_read_allowed(factory):
    svc = FilesystemService(factory.context("architect"))
    out = svc.read_file("backend-core/app.py")
    assert "hello" in out["content"]


def test_fs_read_blocked_sensitive(factory):
    svc = FilesystemService(factory.context("architect"))
    with pytest.raises(GuardViolation):
        svc.read_file("backend-core/.env")


def test_fs_search_finds_and_excludes_sensitive(factory):
    svc = FilesystemService(factory.context("architect"))
    res = svc.search("supersecret")  # lives only in .env
    assert res["count"] == 0  # sensitive file never searched


def test_fs_requires_capability(factory):
    svc = FilesystemService(factory.context("qa"))  # qa has fs.read but not fs.search
    with pytest.raises(PermissionDenied):
        svc.search("hello")


# --- memory ---------------------------------------------------------------
def test_memory_roundtrip(factory):
    svc = MemoryService(factory.context("architect"), factory.config.memory_store)
    svc.remember("decision", "Use TOML config", "stdlib tomllib, zero deps", tags=["config"])
    recent = svc.recent("decision")
    assert recent["count"] == 1
    found = svc.search("tomllib")
    assert found["count"] == 1


def test_memory_write_denied_without_capability(factory):
    svc = MemoryService(factory.context("qa"), factory.config.memory_store)
    with pytest.raises(PermissionDenied):
        svc.remember("note", "x", "y")


def test_memory_rejects_unknown_kind(factory):
    svc = MemoryService(factory.context("architect"), factory.config.memory_store)
    with pytest.raises(ValidationError):
        svc.remember("bogus", "x", "y")


# --- documentation --------------------------------------------------------
def test_create_and_list_adr(factory):
    svc = DocumentationService(factory.context("architect"))
    first = svc.create_adr("Record architecture decisions")
    assert first["number"] == 1
    second = svc.create_adr("Choose MCP stack")
    assert second["number"] == 2
    assert svc.list_adrs()["count"] == 2


def test_append_section_missing_doc(factory):
    svc = DocumentationService(factory.context("architect"))
    with pytest.raises(NotFound):
        svc.append_section("docs/nope.md", "H", "B")


# --- testing --------------------------------------------------------------
def test_testing_runs_allowlisted_command(factory):
    svc = TestingService(factory.context("qa"))
    res = svc.run("echo ok", "python")
    assert res["passed"] and "ok" in res["stdout"]


def test_testing_rejects_unlisted_command(factory):
    svc = TestingService(factory.context("qa"))
    with pytest.raises(GuardViolation):
        svc.run("python -m evil", "python")


def test_testing_rejects_unknown_area(factory):
    svc = TestingService(factory.context("qa"))
    with pytest.raises(ValidationError):
        svc.run("echo ok", "nowhere")


# --- security -------------------------------------------------------------
def test_security_flags_unpinned_deps(factory):
    svc = SecurityService(factory.context("security"))
    res = svc.scan_dependencies()
    pkgs = {d["package"]: d["pinned"] for d in res["dependencies"]}
    assert pkgs["fastapi==0.115.0"] is True
    assert pkgs["requests"] is False


def test_security_validate_command(factory):
    svc = SecurityService(factory.context("security"))
    assert svc.validate_command("python -m pytest")["safe"] is True
    assert svc.validate_command("rm -rf /")["safe"] is False


def test_security_audit_permissions_shape(factory):
    svc = SecurityService(factory.context("security"))
    res = svc.audit_permissions()
    assert "github.merge" in res["critical_capabilities"]


# --- github (offline: slug parsing only) ----------------------------------
def test_github_slug_parsing():
    assert GitHubService.parse_slug("https://github.com/o/r.git") == "o/r"
    assert GitHubService.parse_slug("git@github.com:o/r.git") == "o/r"
    assert GitHubService.parse_slug("https://gitlab.com/o/r") is None
