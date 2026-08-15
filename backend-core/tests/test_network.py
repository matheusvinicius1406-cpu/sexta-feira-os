"""
Network traffic endpoint — GET /api/v1/network/traffic.

The reading must be measured, never invented: counters come from the OS via
psutil, and the rate is a delta between two reads of the same counters. The
first read of a fresh kernel has no previous sample, so `rate` is null and the
API says so instead of returning a made-up number.
"""
import time

# ─────────────────────────────────────────────────────── shape


def test_traffic_shape(client, owner_headers):
    r = client.get("/api/v1/network/traffic", headers=owner_headers)
    assert r.status_code == 200
    body = r.json()

    # Counters: the eight psutil fields, as the OS accounts them.
    assert body["since_boot"] is not None
    for field in ("bytes_sent", "bytes_recv", "packets_sent", "packets_recv", "errin", "errout", "dropin", "dropout"):
        assert field in body["since_boot"]
        assert isinstance(body["since_boot"][field], int)

    # Interfaces: a list, heaviest first, each with the same eight counters.
    assert isinstance(body["interfaces"], list)
    for iface in body["interfaces"]:
        assert "name" in iface
        assert isinstance(iface["bytes_sent"], int)

    # Rate may be null on the first read — that is the honest answer, not a bug.
    assert "rate" in body
    if body["rate"] is not None:
        assert "bytes_sent_per_s" in body["rate"]
        assert "bytes_recv_per_s" in body["rate"]

    assert "connections" in body
    assert "unavailable" in body


# ─────────────────────────────────────────────────── rate sampling


def test_rate_is_delta_between_reads(client, owner_headers):
    # The kernel is a singleton for the whole session, so "the very first read"
    # is not ours to rely on — a previous test may already have warmed the
    # sampler. What IS guaranteed: two reads with a real interval produce a
    # second read whose rate covers exactly that interval.
    client.get("/api/v1/network/traffic", headers=owner_headers)
    time.sleep(0.05)
    second = client.get("/api/v1/network/traffic", headers=owner_headers).json()

    assert second["rate"] is not None
    assert second["rate"]["measured_over_s"] >= 0.05
    assert second["rate"]["bytes_sent_per_s"] >= 0
    assert second["rate"]["bytes_recv_per_s"] >= 0


# ─────────────────────────────────────────────────────── vpn


def test_vpn_shape(client, owner_headers):
    r = client.get("/api/v1/network/vpn", headers=owner_headers)
    assert r.status_code == 200
    body = r.json()

    assert isinstance(body["vpn_active"], bool)
    assert isinstance(body["vpn_interfaces"], list)
    for iface in body["vpn_interfaces"]:
        assert {"name", "up", "addresses"} <= set(iface)
        assert isinstance(iface["name"], str)
        assert isinstance(iface["up"], bool)
        assert isinstance(iface["addresses"], list)
    # The heuristic is stated, never silent — the owner must know what this
    # reading is (and is not) claiming.
    assert "heuristic" in body["method"]
    assert "unavailable" in body


def test_vpn_requires_owner_token(client):
    r = client.get("/api/v1/network/vpn")
    assert r.status_code == 401


# ────────────────────────────────────────────────────────── auth


def test_traffic_requires_owner_token(client):
    r = client.get("/api/v1/network/traffic")
    assert r.status_code == 401
