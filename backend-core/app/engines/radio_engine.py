"""
RadioEngine — Jarvis toca rádio e música.

Features:
1. Internet Radio — 30,000+ estações via Radio Browser API
2. YouTube Music — Streaming via yt-dlp + SponsorBlock ad blocking
3. Local Files — Reprodução de arquivos de áudio locais
4. Smart Search — Busca por gênero, artista, idioma, país
5. Queue Management — Fila de reprodução com skip automático de ads

Architecture:
- Server-side: Busca, filtragem, metadata, ad blocking
- Client-side: Reprodução de áudio (Android app, web player)
- The server returns stream URLs; the client plays them
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import StrEnum

import httpx

from app.engines.ad_blocker import AdBlocker, AdBlockResult

logger = logging.getLogger("sexta-feira.radio")

# Radio Browser API endpoints
RADIO_BROWSER_API = "https://de1.api.radio-browser.info/json"

# Default presets
DEFAULT_STATIONS = [
    {
        "name": "Sexta-Feira FM",
        "url": "https://stream.zeno.fm/0rka3etzzfhv",
        "country": "Brazil",
        "language": "Portuguese",
        "tags": ["brazilian", "pop", "hits"],
    },
    {
        "name": "Radio Rock",
        "url": "https://stream.zeno.fm/rock1",
        "country": "Brazil",
        "language": "Portuguese",
        "tags": ["rock", "metal", "alternative"],
    },
    {
        "name": "Sertanejo Hits",
        "url": "https://stream.zeno.fm/sertanejo1",
        "country": "Brazil",
        "language": "Portuguese",
        "tags": ["sertanejo", "brazilian", "country"],
    },
]


class StreamType(StrEnum):
    INTERNET_RADIO = "radio"
    YOUTUBE = "youtube"
    SOUNDCLOUD = "soundcloud"
    DEEZER = "deezer"
    LOCAL_FILE = "local"


@dataclass
class RadioStation:
    """An internet radio station."""
    name: str
    url: str
    homepage: str = ""
    country: str = ""
    language: str = ""
    tags: list[str] = field(default_factory=list)
    codec: str = ""
    bitrate: int = 0
    click_count: int = 0
    favicon: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "url": self.url,
            "homepage": self.homepage,
            "country": self.country,
            "language": self.language,
            "tags": self.tags,
            "codec": self.codec,
            "bitrate": self.bitrate,
            "click_count": self.click_count,
            "favicon": self.favicon,
        }


@dataclass
class Track:
    """A track (YouTube, local file, or radio station)."""
    id: str
    title: str
    artist: str = ""
    stream_url: str = ""
    duration: float = 0.0
    stream_type: StreamType = StreamType.INTERNET_RADIO
    thumbnail: str = ""
    ad_check: AdBlockResult | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "artist": self.artist,
            "stream_url": self.stream_url,
            "duration": self.duration,
            "stream_type": self.stream_type.value,
            "thumbnail": self.thumbnail,
            "has_ads": self.ad_check.has_ads if self.ad_check else False,
            "skip_segments": len(self.ad_check.segments_to_skip) if self.ad_check else 0,
        }


@dataclass
class RadioState:
    """Current radio playback state."""
    current_track: Track | None = None
    queue: list[Track] = field(default_factory=list)
    queue_index: int = -1
    is_playing: bool = False
    volume: float = 0.8
    shuffle: bool = False
    repeat: bool = False
    ad_blocker_enabled: bool = True

    def to_dict(self) -> dict:
        return {
            "current_track": self.current_track.to_dict() if self.current_track else None,
            "queue_length": len(self.queue),
            "queue_index": self.queue_index,
            "is_playing": self.is_playing,
            "volume": self.volume,
            "shuffle": self.shuffle,
            "repeat": self.repeat,
            "ad_blocker_enabled": self.ad_blocker_enabled,
        }


class RadioEngine:
    """
    Jarvis Radio Engine — toca rádio e música com filtro de anúncios.

    Server-side: busca estações, YouTube, metadata, ad blocking
    Client-side: recebe URLs de stream e reproduce
    """

    def __init__(self):
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(15.0),
            headers={"User-Agent": "SextaFeira-OS/1.0"},
        )
        self.ad_blocker = AdBlocker()
        self._state = RadioState()
        self._station_cache: list[RadioStation] = []

    async def aclose(self) -> None:
        await self._client.aclose()
        await self.ad_blocker.aclose()

    # ── Internet Radio ───────────────────────────────────────

    async def search_stations(
        self,
        query: str = "",
        country: str = "",
        language: str = "",
        tags: list[str] | None = None,
        limit: int = 20,
    ) -> list[RadioStation]:
        """
        Search internet radio stations via Radio Browser API.

        Args:
            query: Search term (name, tag)
            country: Filter by country code (BR, US, etc.)
            language: Filter by language (portuguese, english)
            tags: Filter by tags (rock, pop, sertanejo)
            limit: Max results

        Returns:
            List of RadioStation objects
        """
        try:
            params = {
                "limit": limit,
                "order": "clickcount",
                "reverse": "true",
            }

            if query:
                params["name"] = query
            if country:
                params["countrycode"] = country.upper()
            if language:
                params["language"] = language
            if tags:
                params["tag"] = "+".join(tags)

            response = await self._client.get(
                f"{RADIO_BROWSER_API}/stations/search",
                params=params,
            )
            response.raise_for_status()

            stations = []
            for item in response.json()[:limit]:
                station = RadioStation(
                    name=item.get("name", ""),
                    url=item.get("url_resolved", item.get("url", "")),
                    homepage=item.get("homepage", ""),
                    country=item.get("country", ""),
                    language=item.get("language", ""),
                    tags=item.get("tags", "").split(",") if item.get("tags") else [],
                    codec=item.get("codec", ""),
                    bitrate=item.get("bitrate", 0),
                    click_count=item.get("clickcount", 0),
                    favicon=item.get("favicon", ""),
                )
                if station.url:
                    stations.append(station)

            logger.info("Radio Browser: found %d stations for query '%s'", len(stations), query)
            return stations

        except Exception as e:
            logger.warning("Radio Browser search failed: %s", e)
            return []

    async def get_popular_stations(
        self, country: str = "BR", limit: int = 10
    ) -> list[RadioStation]:
        """Get most popular stations by country."""
        return await self.search_stations(country=country, limit=limit)

    async def get_stations_by_genre(
        self, genre: str, limit: int = 10
    ) -> list[RadioStation]:
        """Get stations by genre/tag."""
        return await self.search_stations(tags=[genre], limit=limit)

    # ── YouTube Music ────────────────────────────────────────

    async def search_youtube(
        self, query: str, limit: int = 5
    ) -> list[Track]:
        """
        Search YouTube Music using ytmusicapi (fast, structured metadata).
        Falls back to yt-dlp if ytmusicapi is unavailable.
        """
        # Try ytmusicapi first (structured search, no download)
        try:
            def _search():
                from ytmusicapi import YTMusic
                ytm = YTMusic()
                results = ytm.search(query, filter="songs", limit=limit)
                tracks = []
                for item in results:
                    if item.get("videoId"):
                        tracks.append(Track(
                            id=item["videoId"],
                            title=item.get("title", ""),
                            artist=item.get("artists", [{}])[0].get("name", "") if item.get("artists") else "",
                            duration=float(item.get("duration_seconds", 0) or 0),
                            stream_type=StreamType.YOUTUBE,
                            thumbnail=item.get("thumbnails", [{}])[-1].get("url", "") if item.get("thumbnails") else "",
                        ))
                return tracks

            tracks = await asyncio.get_event_loop().run_in_executor(None, _search)
            if tracks:
                logger.info("YouTube Music (ytmusicapi): found %d results for '%s'", len(tracks), query)
                return tracks
        except ImportError:
            logger.debug("ytmusicapi not installed, falling back to yt-dlp")
        except Exception as e:
            logger.debug("ytmusicapi search failed: %s, falling back to yt-dlp", e)

        # Fallback: yt-dlp search
        try:
            import yt_dlp

            def _yt_search():
                ydl_opts = {
                    "format": "bestaudio/best",
                    "quiet": True,
                    "no_warnings": True,
                    "extract_flat": True,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    search_url = f"ytsearch{limit}:{query}"
                    result = ydl.extract_info(search_url, download=False)
                    return result.get("entries") or []

            entries = await asyncio.get_event_loop().run_in_executor(None, _yt_search)
            tracks = []
            for entry in entries[:limit]:
                tracks.append(Track(
                    id=entry.get("id", ""),
                    title=entry.get("title", ""),
                    artist=entry.get("uploader", ""),
                    duration=entry.get("duration", 0),
                    stream_type=StreamType.YOUTUBE,
                    thumbnail=entry.get("thumbnail", ""),
                ))
            logger.info("YouTube search (yt-dlp): found %d results for '%s'", len(tracks), query)
            return tracks

        except ImportError:
            logger.warning("yt-dlp not installed. Run: pip install yt-dlp")
            return []
        except Exception as e:
            logger.warning("YouTube search failed: %s", e)
            return []

    async def get_youtube_stream_url(self, video_id: str) -> str | None:
        """Get the direct audio stream URL for a YouTube video."""

        def _extract():
            import yt_dlp
            ydl_opts = {
                "format": "bestaudio/best",
                "quiet": True,
                "no_warnings": True,
            }
            url = f"https://www.youtube.com/watch?v={video_id}"
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info.get("url")

        try:
            return await asyncio.get_event_loop().run_in_executor(None, _extract)
        except Exception as e:
            logger.warning("YouTube stream extraction failed for %s: %s", video_id, e)
            return None

    async def get_youtube_with_ad_check(self, video_id: str) -> Track | None:
        """Get YouTube track with SponsorBlock ad check."""
        stream_url = await self.get_youtube_stream_url(video_id)
        if not stream_url:
            return None

        # Check for sponsor segments
        ad_check = await self.ad_blocker.check_youtube_video(video_id)

        return Track(
            id=video_id,
            title=f"YouTube: {video_id}",
            stream_url=stream_url,
            stream_type=StreamType.YOUTUBE,
            ad_check=ad_check,
        )

    # ── Deezer (free 30s previews, no API key needed) ──────────

    async def search_deezer(self, query: str, limit: int = 5) -> list[Track]:
        """
        Search Deezer via their public API (no auth required).
        Returns tracks with 30-second preview MP3s.
        """
        try:
            url = f"https://api.deezer.com/search?q={query}&limit={limit}"
            response = await self._client.get(url)
            response.raise_for_status()
            data = response.json().get("data", [])

            tracks = []
            for item in data:
                preview_url = item.get("preview", "")
                if not preview_url:
                    continue
                tracks.append(Track(
                    id=f"deezer-{item.get('id', '')}",
                    title=item.get("title", ""),
                    artist=item.get("artist", {}).get("name", ""),
                    stream_url=preview_url,
                    duration=float(item.get("duration", 30)),
                    stream_type=StreamType.DEEZER,
                    thumbnail=item.get("album", {}).get("cover_medium", ""),
                ))

            logger.info("Deezer search: found %d results for '%s'", len(tracks), query)
            return tracks

        except Exception as e:
            logger.warning("Deezer search failed: %s", e)
            return []

    # ── SoundCloud (via yt-dlp fallback) ──────────────────────

    async def search_soundcloud(self, query: str, limit: int = 5) -> list[Track]:
        """
        Search SoundCloud via yt-dlp (scsearch: prefix).
        Returns tracks with stream URLs (extracts fully, not flat).
        """
        try:
            import yt_dlp

            def _search():
                ydl_opts = {
                    "format": "bestaudio/best",
                    "quiet": True,
                    "no_warnings": True,
                    "extract_flat": True,  # Fast search — stream_url extracted lazily
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    result = ydl.extract_info(f"scsearch{limit}:{query}", download=False)
                    return result.get("entries") or []

            entries = await asyncio.get_event_loop().run_in_executor(None, _search)
            tracks = []
            for entry in entries[:limit]:
                tracks.append(Track(
                    id=entry.get("webpage_url", entry.get("id", "")),
                    title=entry.get("title", ""),
                    artist=entry.get("uploader", ""),
                    stream_url="",  # Extracted lazily via get_stream_url()
                    duration=entry.get("duration", 0),
                    stream_type=StreamType.SOUNDCLOUD,
                    thumbnail=entry.get("thumbnail", ""),
                ))

            logger.info("SoundCloud search: found %d results for '%s'", len(tracks), query)
            return tracks

        except ImportError:
            logger.warning("yt-dlp not installed for SoundCloud search")
            return []
        except Exception as e:
            logger.warning("SoundCloud search failed: %s", e)
            return []

    # ── Queue Management ─────────────────────────────────────

    def add_to_queue(self, track: Track) -> int:
        """Add a track to the queue. Returns the queue position."""
        self._state.queue.append(track)
        return len(self._state.queue) - 1

    def add_many_to_queue(self, tracks: list[Track]) -> int:
        """Add multiple tracks. Returns how many were added."""
        self._state.queue.extend(tracks)
        return len(tracks)

    def get_queue(self) -> list[dict]:
        """Get the current queue."""
        return [t.to_dict() for t in self._state.queue]

    def clear_queue(self) -> None:
        """Clear the queue."""
        self._state.queue.clear()
        self._state.queue_index = -1

    def skip(self) -> Track | None:
        """Skip to the next track in the queue."""
        if not self._state.queue:
            return None

        self._state.queue_index += 1

        if self._state.queue_index >= len(self._state.queue):
            if self._state.repeat:
                self._state.queue_index = 0
            else:
                self._state.is_playing = False
                return None

        self._state.current_track = self._state.queue[self._state.queue_index]
        return self._state.current_track

    def previous(self) -> Track | None:
        """Go to the previous track."""
        if not self._state.queue:
            return None

        self._state.queue_index -= 1
        if self._state.queue_index < 0:
            self._state.queue_index = 0

        self._state.current_track = self._state.queue[self._state.queue_index]
        return self._state.current_track

    # ── Playback Control ─────────────────────────────────────

    def get_state(self) -> dict:
        """Get current radio state."""
        return self._state.to_dict()

    def set_volume(self, volume: float) -> None:
        """Set volume (0.0 to 1.0)."""
        self._state.volume = max(0.0, min(1.0, volume))

    def toggle_shuffle(self) -> bool:
        """Toggle shuffle mode."""
        self._state.shuffle = not self._state.shuffle
        return self._state.shuffle

    def toggle_repeat(self) -> bool:
        """Toggle repeat mode."""
        self._state.repeat = not self._state.repeat
        return self._state.repeat

    def toggle_ad_blocker(self) -> bool:
        """Toggle ad blocker."""
        self._state.ad_blocker_enabled = not self._state.ad_blocker_enabled
        return self._state.ad_blocker_enabled

    # ── Search & Play ────────────────────────────────────────

    async def play_search(self, query: str, source: str = "auto") -> dict:
        """
        Search and prepare a track for playback.

        Args:
            query: Search query (song name, artist, station name)
            source: "radio", "youtube", or "auto" (try both)

        Returns:
            {
                "tracks": [Track],
                "query": str,
                "source": str,
            }
        """
        tracks = []

        if source in ("radio", "auto"):
            stations = await self.search_stations(query, limit=5)
            for station in stations:
                track = Track(
                    id=f"radio-{station.name}",
                    title=station.name,
                    artist=station.country or "Internet Radio",
                    stream_url=station.url,
                    stream_type=StreamType.INTERNET_RADIO,
                )
                tracks.append(track)

        if source in ("youtube", "auto") and len(tracks) < 3:
            yt_tracks = await self.search_youtube(query, limit=5)
            tracks.extend(yt_tracks)

        if source in ("deezer", "auto") and len(tracks) < 5:
            dz_tracks = await self.search_deezer(query, limit=5)
            tracks.extend(dz_tracks)

        if source in ("soundcloud", "auto") and len(tracks) < 5:
            sc_tracks = await self.search_soundcloud(query, limit=5)
            tracks.extend(sc_tracks)

        return {
            "tracks": [t.to_dict() for t in tracks],
            "query": query,
            "source": source,
            "count": len(tracks),
        }

    async def play_radio_station(self, station_url: str, name: str = "") -> Track:
        """Play a specific radio station by URL."""
        track = Track(
            id=f"radio-{name}",
            title=name or "Radio Station",
            stream_url=station_url,
            stream_type=StreamType.INTERNET_RADIO,
        )
        self._state.current_track = track
        self._state.is_playing = True
        return track

    async def play_youtube_video(self, video_id: str) -> Track | None:
        """Play a specific YouTube video."""
        track = await self.get_youtube_with_ad_check(video_id)
        if track:
            self._state.current_track = track
            self._state.is_playing = True
        return track

    # ── Unified stream URL extractor ─────────────────────────

    async def get_stream_url(self, track: Track) -> str | None:
        """Get the playable stream URL for any track type."""
        if track.stream_url:
            return track.stream_url

        if track.stream_type == StreamType.YOUTUBE:
            return await self.get_youtube_stream_url(track.id)

        if track.stream_type == StreamType.SOUNDCLOUD:
            def _extract():
                import yt_dlp
                ydl_opts = {"format": "bestaudio/best", "quiet": True}
                url = track.id if track.id.startswith("http") else f"https://soundcloud.com/{track.id}"
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    return info.get("url")
            try:
                return await asyncio.get_event_loop().run_in_executor(None, _extract)
            except Exception as e:
                logger.warning("SoundCloud stream extraction failed: %s", e)
                return None

        return None

    # ── Presets ──────────────────────────────────────────────

    def get_presets(self) -> list[dict]:
        """Get default radio presets."""
        return DEFAULT_STATIONS

    async def play_preset(self, preset_index: int) -> Track | None:
        """Play a preset station by index."""
        if 0 <= preset_index < len(DEFAULT_STATIONS):
            preset = DEFAULT_STATIONS[preset_index]
            return await self.play_radio_station(preset["url"], preset["name"])
        return None

    # ── Statistics ───────────────────────────────────────────

    async def get_stats(self) -> dict:
        """Get radio engine statistics."""
        ad_stats = await self.ad_blocker.get_stats()
        return {
            "state": self._state.to_dict(),
            "ad_blocker": ad_stats,
            "presets_count": len(DEFAULT_STATIONS),
        }
