"""
WebSearch — Jarvis acessa a internet e busca informações.

Provides web search, page scraping, and content extraction.
All requests go through httpx with sensible timeouts and user-agent.
"""
from __future__ import annotations

import logging
import re
from urllib.parse import quote_plus, urlparse

import httpx

logger = logging.getLogger("sexta-feira.websearch")

# DuckDuckGo HTML search (no API key needed)
DDG_SEARCH_URL = "https://html.duckduckgo.com/html/"
# Fallback: Google search
GOOGLE_SEARCH_URL = "https://www.google.com/search"
# User agent to avoid blocks
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
DEFAULT_TIMEOUT = 15.0
MAX_CONTENT_LENGTH = 12000  # chars to return per page


class WebSearchResult:
    """A single search result."""

    def __init__(self, title: str, url: str, snippet: str):
        self.title = title
        self.url = url
        self.snippet = snippet

    def to_dict(self) -> dict:
        return {"title": self.title, "url": self.url, "snippet": self.snippet}


class WebSearch:
    """
    Web search and content extraction engine.
    
    Uses DuckDuckGo HTML search (privacy-first, no tracking).
    Falls back to scraping pages for full content.
    """

    def __init__(self):
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(DEFAULT_TIMEOUT),
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    # ── Search ───────────────────────────────────────────────

    async def search(
        self,
        query: str,
        max_results: int = 5,
        region: str = "br-pt",
    ) -> list[WebSearchResult]:
        """
        Search the web using DuckDuckGo.
        
        Args:
            query: Search query
            max_results: Max results to return
            region: Region code (br-pt for Brazil)
            
        Returns:
            List of WebSearchResult with title, url, snippet
        """
        results = []

        try:
            # DuckDuckGo HTML search
            response = await self._client.post(
                DDG_SEARCH_URL,
                data={"q": query, "kl": region},
            )
            response.raise_for_status()
            html = response.text

            # Parse results from HTML
            # DuckDuckGo uses class="result__a" for links
            links = re.findall(
                r'class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
                html, re.DOTALL
            )
            snippets = re.findall(
                r'class="result__snippet"[^>]*>(.*?)</(?:a|span|div)',
                html, re.DOTALL
            )

            for i, (url, title) in enumerate(links[:max_results]):
                # Clean up DuckDuckGo redirect URLs
                if "uddg=" in url:
                    from urllib.parse import unquote
                    match = re.search(r'uddg=([^&]+)', url)
                    if match:
                        url = unquote(match.group(1))

                # Clean HTML tags from title
                clean_title = re.sub(r'<[^>]+>', '', title).strip()
                snippet = ""
                if i < len(snippets):
                    snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()

                results.append(WebSearchResult(
                    title=clean_title,
                    url=url,
                    snippet=snippet,
                ))

        except Exception as e:
            logger.warning("DuckDuckGo search failed: %s", e)
            # Try Google as fallback
            try:
                results = await self._search_google(query, max_results)
            except Exception as e2:
                logger.warning("Google fallback also failed: %s", e2)

        return results

    async def _search_google(
        self, query: str, max_results: int = 5
    ) -> list[WebSearchResult]:
        """Fallback search using Google."""
        results = []
        response = await self._client.get(
            GOOGLE_SEARCH_URL,
            params={"q": query, "hl": "pt-BR", "num": max_results},
        )
        response.raise_for_status()
        html = response.text

        # Basic Google result parsing
        blocks = re.findall(
            r'<div class="[^"]*"><a href="(/url\?q=([^&"]+)[^"]*)"[^>]*>'
            r'<h3[^>]*>(.*?)</h3>.*?</a>.*?<span[^>]*>(.*?)</span>',
            html, re.DOTALL
        )

        for url_path, url, title, snippet in blocks[:max_results]:
            clean_title = re.sub(r'<[^>]+>', '', title).strip()
            clean_snippet = re.sub(r'<[^>]+>', '', snippet).strip()
            results.append(WebSearchResult(
                title=clean_title,
                url=url,
                snippet=clean_snippet,
            ))

        return results

    # ── Page content extraction ──────────────────────────────

    async def fetch_page(
        self,
        url: str,
        max_chars: int = MAX_CONTENT_LENGTH,
        extract_text: bool = True,
    ) -> dict:
        """
        Fetch and extract readable content from a URL.
        
        Returns:
            {
                "url": str,
                "title": str,
                "content": str,  # extracted text
                "success": bool,
                "error": str | None,
            }
        """
        try:
            response = await self._client.get(url)
            response.raise_for_status()
            html = response.text

            # Extract title
            title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else ""

            if not extract_text:
                return {
                    "url": url,
                    "title": title,
                    "content": html[:max_chars],
                    "success": True,
                    "error": None,
                }

            # Extract readable text (strip scripts, styles, tags)
            content = self._extract_text(html)
            if len(content) > max_chars:
                content = content[:max_chars] + f"\n\n[...truncado em {max_chars} caracteres]"

            return {
                "url": url,
                "title": title,
                "content": content,
                "success": True,
                "error": None,
            }

        except Exception as e:
            return {
                "url": url,
                "title": "",
                "content": "",
                "success": False,
                "error": str(e),
            }

    @staticmethod
    def _extract_text(html: str) -> str:
        """Extract readable text from HTML, stripping scripts, styles, and tags."""
        # Remove script and style blocks
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)

        # Remove HTML comments
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

        # Replace block elements with newlines
        text = re.sub(r"<(?:br|p|div|h[1-6]|li|tr)[^>]*>", "\n", text, flags=re.IGNORECASE)

        # Remove remaining tags
        text = re.sub(r"<[^>]+>", "", text)

        # Decode HTML entities
        text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        text = text.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")

        # Collapse whitespace
        lines = [line.strip() for line in text.splitlines()]
        lines = [line for line in lines if line]  # Remove empty lines
        return "\n".join(lines)

    # ── Combined search + fetch ──────────────────────────────

    async def search_and_fetch(
        self,
        query: str,
        max_results: int = 3,
        fetch_top: bool = True,
    ) -> dict:
        """
        Search and optionally fetch the top result's full content.
        
        Returns:
            {
                "query": str,
                "results": [WebSearchResult],
                "top_content": dict | None,
            }
        """
        results = await self.search(query, max_results=max_results)
        top_content = None

        if fetch_top and results:
            top_content = await self.fetch_page(results[0].url)

        return {
            "query": query,
            "results": [r.to_dict() for r in results],
            "top_content": top_content,
        }
