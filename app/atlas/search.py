#!/usr/bin/env python3
# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
"""Atlas search: GeoNames-backed FTS5 with diacritic folding.

Population-first ordering within matches (autocomplete convention: the
Bradford a user means is almost always the larger one); FTS matching
filters relevance. Read-only connection per query; the db ships in the
image."""

import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "atlas.db"
_SAFE = re.compile(r"[^\w\sÀ-ɏḀ-ỿ.-]")


class AtlasUnavailable(RuntimeError):
    pass


@contextmanager
def _connection():
    try:
        # Storage locks must fail before the container probe times out.
        con = sqlite3.connect(f"{DB_PATH.resolve().as_uri()}?mode=ro",
                              uri=True, timeout=0.1)
        try:
            yield con
        finally:
            con.close()
    except (OSError, sqlite3.Error) as exc:
        raise AtlasUnavailable("atlas storage unavailable") from exc


def check_ready():
    with _connection() as con:
        row = con.execute("SELECT 1 FROM places LIMIT 1").fetchone()
    if row is None:
        raise AtlasUnavailable("atlas is empty")


def search(q: str, limit: int = 8):
    q = _SAFE.sub(" ", q).strip()
    with _connection() as con:
        if len(q) < 2:
            return []
        match = " ".join(f'"{tok}"*' for tok in q.split()[:4])
        rows = con.execute(
            "SELECT display, country, admin1, lat, lon, tz, population "
            "FROM places WHERE places MATCH ? "
            "ORDER BY population DESC LIMIT ?",
            (match, limit)).fetchall()
    return [{"name": r[0], "country": r[1], "admin1": r[2],
             "lat": r[3], "lon": r[4], "tz": r[5], "population": r[6]}
            for r in rows]
