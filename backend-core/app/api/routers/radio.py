"""
Radio — Jarvis toca rádio e música, com filtro de anúncios.

  GET  /api/v1/radio/status              radio engine health
  POST /api/v1/radio/search              search stations & YouTube
  POST /api/v1/radio/play                play a station or YouTube video
  POST /api/v1/radio/youtube             search YouTube music
  GET  /api/v1/radio/queue               get the current queue
  POST /api/v1/radio/queue/add           add track to queue
  POST /api/v1/radio/queue/clear         clear the queue
  POST /api/v1/radio/skip                skip to next track
  POST /api/v1/radio/previous            go to previous track
  GET  /api/v1/radio/presets             get default stations
  POST /api/v1/radio/presets/{index}     play a preset
  POST /api/v1/radio/volume/{level}      set volume
  POST /api/v1/radio/shuffle             toggle shuffle
  POST /api/v1/radio/repeat              toggle repeat
  POST /api/v1/radio/adblock             toggle ad blocker
  GET  /api/v1/radio/stats               engine statistics
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth.jwt import get_current_owner
from app.engines.radio_engine import RadioEngine, StreamType, Track
from app.models.models import Owner

logger = logging.getLogger("sexta-feira.radio.router")

router = APIRouter(prefix="/api/v1/radio", tags=["radio"])

# ── Singleton ──────────────────────────────────────────────

_radio_engine: RadioEngine | None = None


def get_radio() -> RadioEngine:
    global _radio_engine
    if _radio_engine is None:
        _radio_engine = RadioEngine()
    return _radio_engine


# ── Request / Response models ──────────────────────────────

class RadioSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    source: str = Field(default="auto", description="radio, youtube, or auto")
    country: str = Field(default="BR", description="Country code for radio search")
    genre: str | None = Field(default=None, description="Genre filter")


class YouTubeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    limit: int = Field(default=5, ge=1, le=20)


class PlayRequest(BaseModel):
    url: str | None = Field(default=None, description="Direct stream URL")
    video_id: str | None = Field(default=None, description="YouTube video ID")
    name: str = Field(default="", description="Track/station name")


class AddQueueRequest(BaseModel):
    track_id: str
    title: str = ""
    artist: str = ""
    stream_url: str = ""
    stream_type: StreamType = StreamType.INTERNET_RADIO


class VolumeRequest(BaseModel):
    level: float = Field(..., ge=0.0, le=1.0)


# ── Endpoints ──────────────────────────────────────────────

@router.get("/status")
async def radio_status(
    owner: Owner = Depends(get_current_owner),
):
    """Check radio engine availability."""
    radio = get_radio()
    return {"enabled": True, "state": radio.get_state()}


@router.post("/search")
async def search_radio(
    body: RadioSearchRequest,
    owner: Owner = Depends(get_current_owner),
):
    """Search for radio stations and YouTube tracks."""
    radio = get_radio()
    result = await radio.play_search(body.query, source=body.source)
    return result


@router.post("/play")
async def play(
    body: PlayRequest,
    owner: Owner = Depends(get_current_owner),
):
    """Play a radio station or YouTube video."""
    radio = get_radio()

    if body.url:
        track = await radio.play_radio_station(body.url, body.name)
        return {"playing": track.to_dict(), "is_live": True}

    if body.video_id:
        track = await radio.play_youtube_video(body.video_id)
        if track:
            return {"playing": track.to_dict(), "is_live": False}
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Não consegui extrair o stream deste vídeo.",
        )

    raise HTTPException(
        status.HTTP_400_BAD_REQUEST,
        "Forneça 'url' (estação) ou 'video_id' (YouTube).",
    )


@router.post("/youtube")
async def search_youtube(
    body: YouTubeSearchRequest,
    owner: Owner = Depends(get_current_owner),
):
    """Search YouTube for music tracks."""
    radio = get_radio()
    tracks = await radio.search_youtube(body.query, limit=body.limit)
    return {
        "tracks": [t.to_dict() for t in tracks],
        "count": len(tracks),
    }


@router.get("/queue")
async def get_queue(
    owner: Owner = Depends(get_current_owner),
):
    """Get the current playback queue."""
    radio = get_radio()
    return {"queue": radio.get_queue(), "state": radio.get_state()}


@router.post("/queue/add")
async def add_to_queue(
    body: AddQueueRequest,
    owner: Owner = Depends(get_current_owner),
):
    """Add a track to the queue."""
    radio = get_radio()
    track = Track(
        id=body.track_id,
        title=body.title,
        artist=body.artist,
        stream_url=body.stream_url,
        stream_type=body.stream_type,
    )
    position = radio.add_to_queue(track)
    return {"added": True, "position": position, "queue_length": len(radio._state.queue)}


@router.post("/queue/clear")
async def clear_queue(
    owner: Owner = Depends(get_current_owner),
):
    """Clear the playback queue."""
    radio = get_radio()
    radio.clear_queue()
    return {"cleared": True}


@router.post("/skip")
async def skip(
    owner: Owner = Depends(get_current_owner),
):
    """Skip to the next track."""
    radio = get_radio()
    track = radio.skip()
    if track:
        return {"skipped": True, "track": track.to_dict()}
    return {"skipped": True, "track": None, "message": "Fila vazia ou fim da fila."}


@router.post("/previous")
async def previous(
    owner: Owner = Depends(get_current_owner),
):
    """Go to the previous track."""
    radio = get_radio()
    track = radio.previous()
    return {"track": track.to_dict() if track else None}


@router.get("/presets")
async def get_presets(
    owner: Owner = Depends(get_current_owner),
):
    """Get default radio station presets."""
    radio = get_radio()
    return {"presets": radio.get_presets()}


@router.post("/presets/{index}")
async def play_preset(
    index: int,
    owner: Owner = Depends(get_current_owner),
):
    """Play a preset station by index."""
    radio = get_radio()
    track = await radio.play_preset(index)
    if track:
        return {"playing": track.to_dict()}
    raise HTTPException(
        status.HTTP_404_NOT_FOUND,
        f"Preset {index} não encontrado.",
    )


@router.post("/volume/{level}")
async def set_volume(
    level: float,
    owner: Owner = Depends(get_current_owner),
):
    """Set volume (0.0 to 1.0)."""
    radio = get_radio()
    radio.set_volume(level)
    return {"volume": level}


@router.post("/shuffle")
async def toggle_shuffle(
    owner: Owner = Depends(get_current_owner),
):
    """Toggle shuffle mode."""
    radio = get_radio()
    shuffle = radio.toggle_shuffle()
    return {"shuffle": shuffle}


@router.post("/repeat")
async def toggle_repeat(
    owner: Owner = Depends(get_current_owner),
):
    """Toggle repeat mode."""
    radio = get_radio()
    repeat = radio.toggle_repeat()
    return {"repeat": repeat}


@router.post("/adblock")
async def toggle_ad_blocker(
    owner: Owner = Depends(get_current_owner),
):
    """Toggle ad blocker."""
    radio = get_radio()
    enabled = radio.toggle_ad_blocker()
    return {"ad_blocker_enabled": enabled}


@router.get("/stats")
async def radio_stats(
    owner: Owner = Depends(get_current_owner),
):
    """Get radio engine statistics."""
    radio = get_radio()
    return await radio.get_stats()


# ── Playlists (in-memory, like the queue) ───────────────────


@router.get("/playlists")
async def list_playlists(
    owner: Owner = Depends(get_current_owner),
):
    """List saved playlists."""
    return {"playlists": get_radio().list_playlists()}


@router.post("/playlists/{name}", status_code=status.HTTP_201_CREATED)
async def save_playlist(
    name: str,
    owner: Owner = Depends(get_current_owner),
):
    """Save the current queue as a named playlist."""
    radio = get_radio()
    count = radio.save_playlist(name)
    if not count:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Nada para salvar: a fila está vazia e nada está tocando.",
        )
    return {"name": name, "count": count}


@router.post("/playlists/{name}/play")
async def play_playlist(
    name: str,
    owner: Owner = Depends(get_current_owner),
):
    """Load a playlist into the queue and play its first track."""
    track = get_radio().load_playlist(name)
    if track is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Playlist '{name}' não existe. Paleta: `playlists` para ver as salvas.",
        )
    return {"playing": track.to_dict()}


@router.delete("/playlists/{name}")
async def delete_playlist(
    name: str,
    owner: Owner = Depends(get_current_owner),
):
    """Delete a saved playlist."""
    if not get_radio().delete_playlist(name):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Playlist '{name}' não existe.",
        )
    return {"deleted": name}
