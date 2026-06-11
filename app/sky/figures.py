#!/usr/bin/env python3
# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
"""Constellation figures and boundaries.

Lines: dcf21/constellation-stick-figures `constellation_lines_iau.dat`
(IAU/Sky & Telescope derived, CC BY 4.0): `* Name` headers followed by
JSON arrays of HIP id strings (polylines). Encoded as u16 index PAIRS
into the star buffer; a HIP missing from the catalog is a build error
upstream (the loader force-includes referenced HIPs).

Boundaries: VizieR VI/49 `bound_20.dat` (Davenhall & Leggett 1989),
12,948 J2000 rows: RA(deg) Dec(deg) CON type. Encoded as i16-quantized
unit-vector strips, one strip per contiguous constellation run.
"""

import json
import math
import struct
from pathlib import Path

BOUND_EXPECTED_ROWS = 12948


def parse_lines(dat: Path) -> dict[str, list[list[int]]]:
    """-> {constellation_name: [polyline of HIP ints, ...]}"""
    figures: dict[str, list[list[int]]] = {}
    current = ""
    for raw in dat.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("*"):
            current = line.lstrip("*").strip()
            figures.setdefault(current, [])
            continue
        if line.startswith("["):
            # ids may carry a trailing '*' marker in the dcf21 format;
            # the digits are the HIP either way
            hips = [int(str(h).rstrip("*")) for h in json.loads(line)]
            if current and len(hips) >= 2:
                figures[current].append(hips)
    return figures


def referenced_hips(figures: dict[str, list[list[int]]]) -> set[int]:
    return {h for polys in figures.values() for poly in polys for h in poly}


def encode_lines(figures: dict[str, list[list[int]]],
                 hip_index: dict[int, int], out: Path
                 ) -> tuple[int, dict[str, list[int]]]:
    """Polylines -> flat u16 index pairs.

    A few dcf21 HIPs are genuinely absent from ATHYG HYGLike (close
    multiples, e.g. xi UMa 55203). Segments touching a missing star are
    dropped LOUDLY: returned per-constellation, recorded in the manifest,
    and budget-gated in the tests so a parser regression can never eat
    figures silently."""
    pairs: list[tuple[int, int]] = []
    dropped: dict[str, list[int]] = {}
    for name, polys in figures.items():
        for poly in polys:
            for a, b in zip(poly, poly[1:]):
                missing = [h for h in (a, b) if h not in hip_index]
                if missing:
                    dropped.setdefault(name, []).extend(missing)
                    continue
                pairs.append((hip_index[a], hip_index[b]))
    with out.open("wb") as fh:
        fh.write(struct.pack("<4sI", b"RTLN", len(pairs)))
        for a, b in pairs:
            fh.write(struct.pack("<HH", a, b))
    return len(pairs), {k: sorted(set(v)) for k, v in dropped.items()}


def parse_boundaries(dat: Path) -> list[tuple[str, list[tuple[float, float]]]]:
    """-> ordered strips [(con, [(ra_deg, dec_deg), ...]), ...]"""
    strips: list[tuple[str, list[tuple[float, float]]]] = []
    rows = 0
    for raw in dat.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        ra = float(raw[0:12])
        dec = float(raw[12:24])
        con = raw[24:29].strip()
        rows += 1
        if not strips or strips[-1][0] != con:
            strips.append((con, []))
        strips[-1][1].append((ra, dec))
    if rows != BOUND_EXPECTED_ROWS:
        raise ValueError(
            f"VI/49 regression: expected {BOUND_EXPECTED_ROWS} rows, "
            f"parsed {rows}")
    return strips


def encode_boundaries(strips, out: Path) -> int:
    """i16-quantized unit vectors (~6 arcsec, far below line width) with a
    strip offset table."""
    with out.open("wb") as fh:
        fh.write(struct.pack("<4sI", b"RTBD", len(strips)))
        offset = 0
        for _con, pts in strips:
            fh.write(struct.pack("<II", offset, len(pts)))
            offset += len(pts)
        total = 0
        for _con, pts in strips:
            for ra, dec in pts:
                r, d = math.radians(ra), math.radians(dec)
                x = math.cos(d) * math.cos(r)
                y = math.cos(d) * math.sin(r)
                z = math.sin(d)
                fh.write(struct.pack(
                    "<3h",
                    int(round(x * 32767)),
                    int(round(y * 32767)),
                    int(round(z * 32767))))
                total += 1
    return total
