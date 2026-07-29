"""Audit log: append-only, secret redaction, and authorization recording."""
from jarvis_mcp.core.audit import AuditLog, redact
from jarvis_mcp.core.errors import PermissionDenied


def test_records_are_appended(tmp_path):
    log = AuditLog(tmp_path / "a.log")
    log.record(agent="architect", action="fs.read", target="x.py")
    log.record(agent="qa", action="testing.run", target="pytest")
    assert len(log.tail(10)) == 2


def test_redacts_secret_values():
    out = redact({"GITHUB_TOKEN": "abc123", "path": "ok"})
    assert out["GITHUB_TOKEN"] == "***"
    assert out["path"] == "ok"
    assert "***" in redact("authorization=Bearer sk-secret")


def test_context_authorize_writes_allow_entry(factory):
    ctx = factory.context("architect")
    ctx.authorize("fs.read", "backend-core/app.py")
    last = factory.audit.tail(1)[0]
    assert last["decision"] == "allow" and last["agent"] == "architect"


def test_context_authorize_writes_deny_entry(factory):
    ctx = factory.context("qa")
    try:
        ctx.authorize("memory.write", "note")
    except PermissionDenied:
        pass
    last = factory.audit.tail(1)[0]
    assert last["decision"] == "deny"
