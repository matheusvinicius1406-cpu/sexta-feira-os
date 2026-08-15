"""
Radio playlists — in-memory snapshots of the queue, like the queue itself.

A playlist is saved from the current queue (or the playing track when the
queue is empty), can be listed, loaded into the queue, and deleted. Honest
about being ephemeral: none of this survives a reboot.
"""
from app.engines.radio_engine import RadioEngine, StreamType, Track


def _track(title: str, url: str = "http://stream") -> Track:
    return Track(id=f"radio-{title}", title=title, stream_url=url,
                 stream_type=StreamType.INTERNET_RADIO)


# ── engine ────────────────────────────────────────────────


def test_save_playlist_snapshots_the_queue():
    engine = RadioEngine()
    engine._state.queue = [_track("A"), _track("B")]
    assert engine.save_playlist("meus sons") == 2

    saved = engine.list_playlists()
    assert saved == [{"name": "meus sons", "count": 2, "titles": ["A", "B"]}]


def test_save_with_empty_queue_uses_current_track():
    engine = RadioEngine()
    engine._state.current_track = _track("só essa")
    assert engine.save_playlist("single") == 1


def test_save_with_nothing_to_save_returns_zero():
    engine = RadioEngine()
    assert engine.save_playlist("vazia") == 0
    assert engine.list_playlists() == []


def test_load_playlist_replaces_queue_and_plays_first():
    engine = RadioEngine()
    engine._state.queue = [_track("A"), _track("B")]
    engine.save_playlist("mix")

    engine._state.queue = [_track("antiga")]
    first = engine.load_playlist("mix")
    assert first.title == "A"
    assert [t.title for t in engine._state.queue] == ["A", "B"]
    assert engine._state.current_track.title == "A"
    assert engine._state.is_playing


def test_load_missing_playlist_returns_none():
    engine = RadioEngine()
    assert engine.load_playlist("não existe") is None


def test_delete_playlist():
    engine = RadioEngine()
    engine._state.queue = [_track("A")]
    engine.save_playlist("mix")
    assert engine.delete_playlist("mix") is True
    assert engine.list_playlists() == []
    assert engine.delete_playlist("mix") is False


# ── endpoints ─────────────────────────────────────────────


def _queue_some(engine: RadioEngine) -> None:
    engine._state.queue = [_track("A"), _track("B")]


def test_playlist_roundtrip(client, owner_headers):
    from app.api.routers.radio import get_radio
    _queue_some(get_radio())

    created = client.post("/api/v1/radio/playlists/mix", headers=owner_headers)
    assert created.status_code == 201
    assert created.json() == {"name": "mix", "count": 2}

    listed = client.get("/api/v1/radio/playlists", headers=owner_headers).json()
    assert listed["playlists"][0]["name"] == "mix"

    played = client.post("/api/v1/radio/playlists/mix/play", headers=owner_headers)
    assert played.status_code == 200
    assert played.json()["playing"]["title"] == "A"

    deleted = client.delete("/api/v1/radio/playlists/mix", headers=owner_headers)
    assert deleted.status_code == 200
    assert deleted.json() == {"deleted": "mix"}

    after = client.get("/api/v1/radio/playlists", headers=owner_headers).json()
    assert after["playlists"] == []


def test_save_empty_queue_is_400(client, owner_headers):
    from app.api.routers.radio import get_radio
    get_radio()._state.queue = []
    get_radio()._state.current_track = None
    r = client.post("/api/v1/radio/playlists/vazia", headers=owner_headers)
    assert r.status_code == 400


def test_play_unknown_playlist_is_404(client, owner_headers):
    r = client.post("/api/v1/radio/playlists/nada/play", headers=owner_headers)
    assert r.status_code == 404


def test_delete_unknown_playlist_is_404(client, owner_headers):
    r = client.delete("/api/v1/radio/playlists/nada", headers=owner_headers)
    assert r.status_code == 404


def test_playlists_require_owner_token(client):
    assert client.get("/api/v1/radio/playlists").status_code == 401


# ── queue robustness ──────────────────────────────────────


def test_invalid_stream_type_is_422_not_500(client, owner_headers):
    """`stream_type` is validated by pydantic (a StreamType enum): a garbage
    value gets a clean 422, not an unhandled ValueError 500."""
    r = client.post(
        "/api/v1/radio/queue/add",
        json={"track_id": "radio-x", "title": "X", "stream_type": "internet_radio"},
        headers=owner_headers,
    )
    assert r.status_code == 422
    r2 = client.post(
        "/api/v1/radio/queue/add",
        json={"track_id": "radio-x", "title": "X", "stream_type": "radio"},
        headers=owner_headers,
    )
    assert r2.status_code == 200
