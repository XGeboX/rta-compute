#!/usr/bin/env python3
# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
"""Atlas search: GeoNames-backed FTS5 with diacritic folding.

Population-first ordering within matches (autocomplete convention: the
Bradford a user means is almost always the larger one); FTS matching
filters relevance. Read-only connection per query; the db ships in the
image."""

import re
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "atlas.db"
_SAFE = re.compile(r"[^\w\sÀ-ɏḀ-ỿ.-]")


def search(q: str, limit: int = 8):
    if not DB_PATH.exists():
        return []
    q = _SAFE.sub(" ", q).strip()
    if len(q) < 2:
        return []
    match = " ".join(f'"{tok}"*' for tok in q.split()[:4])
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "SELECT display, country, admin1, lat, lon, tz, population "
            "FROM places WHERE places MATCH ? "
            "ORDER BY population DESC LIMIT ?",
            (match, limit)).fetchall()
    finally:
        con.close()
    return [{"name": r[0], "country": r[1], "admin1": r[2],
             "lat": r[3], "lon": r[4], "tz": r[5], "population": r[6]}
            for r in rows]
