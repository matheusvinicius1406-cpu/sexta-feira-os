"""Ponte com o vault Obsidian: importa, exporta, observa e recupera notas."""
from __future__ import annotations

# Subfolder where the KERNEL's own writes to the vault live (auto-learned
# facts, see exporter.py::export_auto_learned_fact). Shared between exporter
# (writes here) and importer/watcher/recall (must skip it): without the skip,
# the watcher re-imports the kernel's own notes as duplicate source="obsidian"
# nodes on its very next poll — the kernel re-learning what it just wrote.
BRAIN_FOLDER = "__sexta__"
