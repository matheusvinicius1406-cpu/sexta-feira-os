"""
The host metrics endpoint.

The System module of the HUD had no source at all — the reactor rendered CPU,
memory, disk, power and temperature as static furniture. This endpoint is what
those readouts read from, so the contract that matters is: every number present
is measured, and anything the platform cannot measure is `null` WITH a stated
reason, never a filler value. A dash on screen must mean "not measurable here",
and the owner must be able to find out why.
"""


def test_system_requires_auth(client):
    assert client.get("/api/v1/system").status_code == 401


def test_system_reports_measured_host_metrics(client, owner_headers):
    body = client.get("/api/v1/system", headers=owner_headers).json()

    cpu = body["cpu"]
    assert 0.0 <= cpu["percent"] <= 100.0
    assert cpu["cores_logical"] >= 1

    memory = body["memory"]
    assert memory["total_bytes"] > 0
    assert 0.0 <= memory["percent"] <= 100.0
    assert memory["used_bytes"] <= memory["total_bytes"]

    disk = body["disk"]
    assert disk["total_bytes"] > 0
    assert disk["used_bytes"] + disk["free_bytes"] <= disk["total_bytes"]

    assert body["uptime_seconds"] > 0
    assert body["host"]["system"]


def test_unmeasurable_fields_are_null_and_explained(client, owner_headers):
    """A null reading must come with a reason, and a reason must mean null.

    Both halves matter. A dashed readout with no explanation is indistinguishable
    from a broken one; and a field listed as unavailable while still carrying a
    number would put an unexplained value on screen.
    """
    body = client.get("/api/v1/system", headers=owner_headers).json()
    unavailable = body["unavailable"]

    # Temperature is the permanent case: psutil exposes no sensor on Windows.
    assert body["temperature"] is None
    assert unavailable.get("temperature"), "temperatura veio nula sem dizer por quê"

    for field, reason in unavailable.items():
        assert reason.strip(), f"campo '{field}' listado como indisponível sem motivo"
        assert body[field] is None, (
            f"campo '{field}' está listado como indisponível mas trouxe valor: {body[field]}"
        )


def test_battery_is_either_a_real_reading_or_declared_absent(client, owner_headers):
    """Desktops have no battery; laptops do. Both are correct — inventing one is not."""
    body = client.get("/api/v1/system", headers=owner_headers).json()
    battery = body["battery"]

    if battery is None:
        assert "battery" in body["unavailable"]
        return

    assert 0.0 <= battery["percent"] <= 100.0
    assert isinstance(battery["plugged"], bool)
    # psutil returns sentinels (huge ints) rather than durations while charging;
    # letting one through would render as ~68 years remaining.
    assert battery["seconds_left"] is None or 0 <= battery["seconds_left"] < 86400 * 2
