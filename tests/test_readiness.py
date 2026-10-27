#!/usr/bin/env python3
# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
"""Readiness failures must be visible to callers and container probes."""

import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.astro import context as C  # noqa: E402
from app.atlas import search as A  # noqa: E402
from app.main import app  # noqa: E402
from app.version import engine_version  # noqa: E402

client = TestClient(app)


@pytest.fixture
def atlas_db(tmp_path, monkeypatch):
    db_path = tmp_path / "atlas.db"
    con = sqlite3.connect(db_path)
    try:
        con.execute(
            "CREATE VIRTUAL TABLE places USING fts5("
            "terms, display UNINDEXED, country UNINDEXED, admin1 UNINDEXED, "
            "lat UNINDEXED, lon UNINDEXED, tz UNINDEXED, population UNINDEXED, "
            "tokenize='unicode61 remove_diacritics 2')")
        con.commit()
    finally:
        con.close()
    monkeypatch.setattr(A, "DB_PATH", db_path)
    return db_path


@pytest.fixture
def populated_atlas(atlas_db):
    con = sqlite3.connect(atlas_db)
    try:
        con.execute("INSERT INTO places VALUES (?,?,?,?,?,?,?,?)",
                    ("Testville", "Testville", "GB", "", 0.0, 0.0,
                     "Etc/UTC", 1))
        con.commit()
    finally:
        con.close()
    return atlas_db


def test_missing_atlas_returns_503_and_health_is_unready(tmp_path, monkeypatch):
    db_path = tmp_path / "missing.db"
    monkeypatch.setattr(A, "DB_PATH", db_path)

    atlas = client.get("/v1/atlas", params={"q": "Bradford"})
    health = client.get("/v1/healthz")

    assert (atlas.status_code, health.status_code) == (503, 503)
    assert atlas.json() == {"detail": "atlas storage unavailable"}
    assert health.json() == {"detail": "atlas storage unavailable"}
    assert not db_path.exists()


@pytest.mark.parametrize("storage", ["directory", "corrupt", "no_schema"])
def test_unreadable_atlas_returns_503_and_health_is_unready(
        tmp_path, monkeypatch, storage):
    db_path = tmp_path / "unreadable.db"
    if storage == "directory":
        db_path.mkdir()
    elif storage == "corrupt":
        db_path.write_bytes(b"not a SQLite database")
    else:
        con = sqlite3.connect(db_path)
        con.close()
    monkeypatch.setattr(A, "DB_PATH", db_path)

    atlas = client.get("/v1/atlas", params={"q": "Testville"})
    health = client.get("/v1/healthz")

    assert (atlas.status_code, health.status_code) == (503, 503)
    assert atlas.json() == {"detail": "atlas storage unavailable"}
    assert health.json() == {"detail": "atlas storage unavailable"}


def test_empty_atlas_is_unready(atlas_db):
    health = client.get("/v1/healthz")

    assert health.status_code == 503
    assert health.json() == {"detail": "atlas is empty"}


def test_no_matches_returns_200_and_populated_atlas_is_ready(populated_atlas):
    atlas = client.get("/v1/atlas", params={"q": "Nevermatches"})
    health = client.get("/v1/healthz")

    assert atlas.status_code == 200
    assert atlas.json() == {"results": []}
    assert health.status_code == 200
    assert health.json() == {"ok": True, "engine": "rta-compute",
                             "version": engine_version()}
    match = client.get("/v1/atlas", params={"q": "Testville"})
    assert match.status_code == 200
    assert match.json()["results"][0]["name"] == "Testville"


def test_computation_failure_is_unready_and_releases_frame(
        populated_atlas, monkeypatch):
    def broken_computation(jd):
        assert C._FRAME_LOCK.locked()
        raise RuntimeError("internal engine failure")

    with monkeypatch.context() as patch:
        patch.setattr(C, "ayanamsa_value", broken_computation)
        health = client.get("/v1/healthz")

    assert health.status_code == 503
    assert health.json() == {"detail": "computation unavailable"}
    assert not C._FRAME_LOCK.locked()
    assert client.get("/v1/healthz").status_code == 200


def test_nonfinite_computation_is_unready(populated_atlas, monkeypatch):
    monkeypatch.setattr(C, "ayanamsa_value", lambda jd: float("nan"))

    health = client.get("/v1/healthz")

    assert health.status_code == 503
    assert health.json() == {"detail": "computation unavailable"}
