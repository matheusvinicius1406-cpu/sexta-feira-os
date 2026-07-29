"""
Teia — the Python-First automation platform (see docs/jarvis/architecture/
AUTOMATION_PLATFORM.md and ADR-0013).

Phase 1 delivers the DOMAIN CORE only: the workflow graph, the Node/Trigger type
contracts, an in-memory Registry and JSON/YAML serialization — no execution engine
yet (that is Phase 2). Everything here is pure Python with full typing, so the
domain is testable in isolation and free of infrastructure concerns.
"""
