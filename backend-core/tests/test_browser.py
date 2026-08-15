"""
Browser endpoints — GET /api/v1/browser/tabs and /marks (POST/DELETE).

The kernel does not control a browser. Its "tabs" are the searches IT performed
since boot (in-memory, honest about being ephemeral), and its "marks" are
memory nodes of kind `bookmark` — so the roundtrip here also proves a saved
mark is a real memory that `forget` knows how to remove.
"""
import uuid

from app.api.routers import vision as vision_router

# ─────────────────────────────────────────────────────── tabs


def test_tabs_shape(client, owner_headers):
    r = client.get("/api/v1/browser/tabs", headers=owner_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == len(body["tabs"])
    assert body["session_started_at"]
    for tab in body["tabs"]:
        assert {"query", "kind", "results", "top_url", "at"} <= set(tab)


def test_successful_search_records_a_tab(client, owner_headers, monkeypatch):
    """
    Contract between /vision/search and /browser/tabs: the search engine returns
    a DICT (query/results/top_content) — not an object with attributes — and the
    hook records it as a tab. This is the exact shape that broke the hook once
    (attribute access on a dict) without any test noticing.
    """

    class _FakeSearch:
        def __init__(self):
            self.calls = 0

        async def search_and_fetch(self, query, max_results=5, fetch_top=False):
            self.calls += 1
            return {
                "query": query,
                "results": [
                    {"title": "Exemplo", "url": "https://exemplo.com/1", "snippet": "snippet"}
                ],
                "top_content": None,
            }

    fake = _FakeSearch()
    monkeypatch.setattr(vision_router, "_web_search", fake)

    r = client.post(
        "/api/v1/vision/search",
        json={"query": "exemplo", "max_results": 5},
        headers=owner_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["query"] == "exemplo"
    assert body["results"][0]["url"] == "https://exemplo.com/1"

    tabs = client.get("/api/v1/browser/tabs", headers=owner_headers).json()
    assert any(
        t["query"] == "exemplo" and t["kind"] == "search" for t in tabs["tabs"]
    )


# ────────────────────────────────────────────────────── marks


def test_marks_roundtrip(client, owner_headers):
    created = client.post(
        "/api/v1/browser/marks",
        json={"url": "https://exemplo.com/artigo", "title": "Artigo"},
        headers=owner_headers,
    )
    assert created.status_code == 201
    mark = created.json()
    assert mark["url"] == "https://exemplo.com/artigo"
    assert mark["title"] == "Artigo"
    assert mark["id"]

    listed = client.get("/api/v1/browser/marks", headers=owner_headers).json()
    assert any(m["id"] == mark["id"] for m in listed["marks"])

    deleted = client.delete(f"/api/v1/browser/marks/{mark['id']}", headers=owner_headers)
    assert deleted.status_code == 200
    assert deleted.json()["forgotten"] == mark["id"]

    after = client.get("/api/v1/browser/marks", headers=owner_headers).json()
    assert all(m["id"] != mark["id"] for m in after["marks"])


def test_mark_validation(client, owner_headers):
    r = client.post(
        "/api/v1/browser/marks",
        json={"url": "x", "title": "curto demais"},
        headers=owner_headers,
    )
    assert r.status_code == 422


def test_delete_unknown_mark_is_404(client, owner_headers):
    r = client.delete(f"/api/v1/browser/marks/{uuid.uuid4().hex}", headers=owner_headers)
    assert r.status_code == 404


# ────────────────────────────────────────────────────────── auth


def test_browser_requires_owner_token(client):
    assert client.get("/api/v1/browser/tabs").status_code == 401
    assert client.get("/api/v1/browser/marks").status_code == 401
