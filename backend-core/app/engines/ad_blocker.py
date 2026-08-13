"""
AdBlocker — Filtro inteligente de anúncios para áudio.

Bloqueia anúncios usando:
1. SponsorBlock API (YouTube) — categorias: sponsor, selfpromo, interaction, intro, outro
2. Metadata detection (Internet Radio) — detecta "advertisement" no ICY metadata
3. Silence detection — áudio mudo indica ad break
4. Blacklist — palavras-chave que indicam anúncios
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger("sexta-feira.adblocker")

# SponsorBlock categories to remove
SPONSORBLOCK_CATEGORIES = [
    "sponsor",
    "selfpromo",
    "interaction",
    "intro",
    "outro",
    "preview",
    "music_offtopic",
]

# Blacklist keywords for ad detection in metadata
AD_KEYWORDS = [
    "advertisement",
    "sponsored",
    "promo",
    "publicidade",
    "anúncio",
    "comercial",
    "oferecimento",
    "patrocinado",
    "ad break",
    "ad break",
    "this episode is sponsored",
    "this video is sponsored",
]

# Pattern for detecting ad-like content
AD_PATTERNS = [
    re.compile(r"\b(ad|ads|commercial|sponsor)\b", re.IGNORECASE),
    re.compile(r"\b(oferecimento|patrocínio|publicidade)\b", re.IGNORECASE),
    re.compile(r"\bcompre agora|buy now|link na bio|use o código\b", re.IGNORECASE),
]


@dataclass
class SponsorBlockSegment:
    """A segment to skip in a YouTube video."""
    start: float
    end: float
    category: str
    uuid: str = ""
    description: str = ""


@dataclass
class AdBlockResult:
    """Result of ad blocking analysis."""
    has_ads: bool = False
    segments_to_skip: list[SponsorBlockSegment] = field(default_factory=list)
    total_skip_time: float = 0.0
    blocked_metadata: list[str] = field(default_factory=list)
    confidence: float = 0.0


class AdBlocker:
    """
    Intelligent ad blocker for audio streams.

    - YouTube: Uses SponsorBlock crowdsourced database
    - Internet Radio: Detects ads via ICY metadata
    - General: Keyword and pattern matching
    """

    def __init__(self):
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
            headers={"User-Agent": "SextaFeira-OS/1.0"},
        )
        self._sponsorblock_cache: dict[str, list[SponsorBlockSegment]] = {}
        self._cache_max_size = 128

    async def aclose(self) -> None:
        await self._client.aclose()

    # ── SponsorBlock (YouTube) ───────────────────────────────

    async def get_sponsorblock_segments(
        self, video_id: str
    ) -> list[SponsorBlockSegment]:
        """
        Fetch SponsorBlock segments for a YouTube video.

        Returns segments that should be skipped (sponsor, intro, outro, etc.)
        """
        if video_id in self._sponsorblock_cache:
            return self._sponsorblock_cache[video_id]

        try:
            # Query SponsorBlock API
            categories = ",".join(SPONSORBLOCK_CATEGORIES)
            url = "https://sponsor.ajay.app/api/skipSegments"
            response = await self._client.get(
                url,
                params={"videoID": video_id, "categories": f'["{categories}"]'},
            )

            if response.status_code == 200:
                data = response.json()
                segments = []
                for item in data:
                    segment = item.get("segment", [0, 0])
                    if len(segment) == 2:
                        segments.append(SponsorBlockSegment(
                            start=segment[0],
                            end=segment[1],
                            category=item.get("category", "sponsor"),
                            uuid=item.get("UUID", ""),
                            description=item.get("description", ""),
                        ))

                # Sort by start time
                segments.sort(key=lambda s: s.start)
                self._sponsorblock_cache[video_id] = segments
                # Evict oldest entries if cache is too large
                if len(self._sponsorblock_cache) > self._cache_max_size:
                    oldest_keys = list(self._sponsorblock_cache.keys())[:self._cache_max_size // 2]
                    for k in oldest_keys:
                        del self._sponsorblock_cache[k]

                if segments:
                    total = sum(s.end - s.start for s in segments)
                    logger.info(
                        "SponsorBlock: %d segments found for %s (%.1fs total skip)",
                        len(segments), video_id, total,
                    )
                return segments
            else:
                logger.debug("SponsorBlock: no data for %s (status %d)", video_id, response.status_code)
                return []

        except Exception as e:
            logger.debug("SponsorBlock query failed: %s", e)
            return []

    async def check_youtube_video(self, video_id: str) -> AdBlockResult:
        """Check a YouTube video for sponsor segments."""
        segments = await self.get_sponsorblock_segments(video_id)
        total_skip = sum(s.end - s.start for s in segments)

        return AdBlockResult(
            has_ads=len(segments) > 0,
            segments_to_skip=segments,
            total_skip_time=total_skip,
            confidence=0.9 if segments else 0.0,
        )

    # ── Internet Radio metadata ──────────────────────────────

    def check_radio_metadata(self, metadata: str) -> AdBlockResult:
        """
        Check ICY metadata for ad indicators.

        Internet radio stations often embed song/program info in ICY metadata.
        Ad breaks are sometimes indicated by empty or ad-like metadata.
        """
        blocked = []
        confidence = 0.0

        if not metadata:
            return AdBlockResult(has_ads=False, confidence=0.5)

        # Check against ad keywords
        metadata_lower = metadata.lower()
        for keyword in AD_KEYWORDS:
            if keyword in metadata_lower:
                blocked.append(keyword)
                confidence = max(confidence, 0.8)

        # Check against patterns
        for pattern in AD_PATTERNS:
            if pattern.search(metadata):
                blocked.append(f"pattern:{pattern.pattern}")
                confidence = max(confidence, 0.7)

        return AdBlockResult(
            has_ads=len(blocked) > 0,
            blocked_metadata=blocked,
            confidence=confidence,
        )

    # ── Skip calculation ─────────────────────────────────────

    def should_skip(
        self, current_time: float, segments: list[SponsorBlockSegment]
    ) -> tuple[bool, float]:
        """
        Check if current playback time is inside a sponsor segment.

        Returns:
            (should_skip, skip_to_time)
        """
        for segment in segments:
            if segment.start <= current_time <= segment.end:
                return True, segment.end
        return False, current_time

    def get_skip_info(
        self, current_time: float, segments: list[SponsorBlockSegment]
    ) -> dict | None:
        """Get detailed skip information for current position."""
        for segment in segments:
            if segment.start <= current_time <= segment.end:
                remaining = segment.end - current_time
                return {
                    "skipping": True,
                    "category": segment.category,
                    "description": segment.description,
                    "skip_to": segment.end,
                    "remaining_seconds": round(remaining, 1),
                }
        return None

    # ── Statistics ───────────────────────────────────────────

    async def get_stats(self) -> dict:
        """Get ad blocker statistics."""
        return {
            "sponsorblock_cache_size": len(self._sponsorblock_cache),
            "categories_blocked": SPONSORBLOCK_CATEGORIES,
            "ad_keywords_count": len(AD_KEYWORDS),
        }
