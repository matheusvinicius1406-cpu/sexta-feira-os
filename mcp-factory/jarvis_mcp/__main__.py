"""Launcher: ``python -m jarvis_mcp <server>`` starts one MCP server over stdio.

Examples:
    python -m jarvis_mcp filesystem
    python -m jarvis_mcp core
    python -m jarvis_mcp --list
"""
from __future__ import annotations

import importlib
import sys

from .servers import BUILDERS


def _usage() -> str:
    names = ", ".join(sorted(BUILDERS))
    return f"usage: python -m jarvis_mcp <server>\n  servers: {names}\n  --list  show servers and exit"


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(_usage())
        return 0
    if argv[0] == "--list":
        for name in sorted(BUILDERS):
            print(name)
        return 0

    name = argv[0]
    if name not in BUILDERS:
        print(f"unknown server '{name}'\n\n{_usage()}", file=sys.stderr)
        return 2

    module = importlib.import_module(BUILDERS[name])
    server = module.build()
    server.run()  # blocks, serving MCP over stdio
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
