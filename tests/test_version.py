#!/usr/bin/env python3
# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
"""The byte-identical contract is self-stating: /healthz and every Instant
response must carry the engine identity, and the dependency versions in it
must be the ACTUALLY INSTALLED ones, never hand-claimed strings."""

import sys
from importlib import metadata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app          # noqa: E402
from app.version import engine_version  # noqa: E402

client = TestClient(app)


def test_healthz_carries_version_block():
    res = client.get("/v1/healthz")
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    v = body["version"]
    assert v["contract"] == "byte-identical per image digest"
    assert isinstance(v["sha"], str) and v["sha"]
    # Truthfulness gate: the echoed pins are read from installed metadata.
    assert v["pyjhora"] == metadata.version("PyJHora")
    assert v["pyswisseph"] == metadata.version("pyswisseph")


def test_instant_response_names_its_engine():
    res = client.post("/v1/instant", json={
        "birth": {"date": "2025-02-28", "time": "17:55:55",
                  "lat": 53.7938, "lon": -1.7564, "tz_hours": 0.0,
                  "place_name": "Bradford"},
        "asof": "2025-03-01",
    })
    assert res.status_code == 200
    engine = res.json()["engine"]
    # Assert against metadata directly, not engine_version(), so a shared
    # bug in the helper cannot vouch for itself.
    assert engine["pyjhora"] == metadata.version("PyJHora")
    assert engine["pyswisseph"] == metadata.version("pyswisseph")
    assert engine["sha"] == engine_version()["sha"]
    assert engine["contract"] == "byte-identical per image digest"


def test_agpl_source_header_present():
    res = client.get("/v1/healthz")
    assert "github.com/XGeboX/rta-compute" in res.headers["X-AGPL-Source"]
