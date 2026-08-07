"""
PluginMarketplaceClient — discovers and downloads plugins from a remote registry.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("sexta-feira.plugins.marketplace")


@dataclass
class MarketplaceEntry:
    """A plugin listing from the marketplace."""
    plugin_id: str
    display_name: str
    version: str
    author: str
    description: str
    download_url: str
    checksum: str
    dependencies: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)


class PluginMarketplaceClient:
    """Client for discovering and downloading plugins from a remote registry."""

    DEFAULT_REGISTRY = "https://plugins.sexta-feira.local"

    def __init__(self, registry_url: str | None = None) -> None:
        self._registry_url = registry_url or self.DEFAULT_REGISTRY
        self._cache: dict[str, MarketplaceEntry] = {}

    async def list_available(self) -> list[MarketplaceEntry]:
        """List all available plugins from the marketplace."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self._registry_url}/api/v1/plugins") as resp:
                    data = await resp.json()
                    entries = [MarketplaceEntry(**item) for item in data.get("plugins", [])]
                    self._cache = {e.plugin_id: e for e in entries}
                    return entries
        except ImportError:
            logger.warning("aiohttp not installed — cannot query marketplace")
            return []
        except Exception as exc:
            logger.warning("Marketplace unavailable: %s", exc)
            return []

    async def download(self, plugin_id: str, target_dir: str | Path) -> Path | None:
        """Download a plugin from the marketplace to a local directory."""
        entry = self._cache.get(plugin_id)
        if not entry:
            return None

        target = Path(target_dir) / f"{plugin_id}.py"
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(entry.download_url) as resp:
                    content = await resp.text()
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content)
                    logger.info("Downloaded plugin '%s' to %s", plugin_id, target)
                    return target
        except ImportError:
            logger.warning("aiohttp not installed — cannot download plugin")
            return None
        except Exception as exc:
            logger.warning("Failed to download plugin '%s': %s", plugin_id, exc)
            return None

    def search(self, query: str) -> list[MarketplaceEntry]:
        """Search cached marketplace entries."""
        q = query.lower()
        return [
            e for e in self._cache.values()
            if q in e.plugin_id.lower() or q in e.display_name.lower()
            or q in e.description.lower()
        ]
