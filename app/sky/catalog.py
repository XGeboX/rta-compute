#!/usr/bin/env python3
# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
"""ATHYG HYGLike catalog -> stars-v1.bin.

Record layout (little-endian, 24 bytes, magnitude-ascending so a prefix of
the buffer IS a magnitude cut and progressive rendering is free):

    xyz   3x f32   ICRS unit vector, proper motion propagated to EPOCH
    mag   i16      magnitude * 1000
    bv    i16      B-V color index * 1000 (clamped to +/-2.0)
    hip   u32      Hipparcos id (0 if none)
    flags u8       bit0 named, bit1 yogatara (set by build_sky)
    pad   3x u8

Header (32 bytes): magic 'RTSK', u8 version=1, u8 flags, u16 record_size,
u32 count, f64 epoch_jd, 12 reserved.

Proper motion: HYG carries pmrarad/pmdecrad (rad/yr; pmra is the
mu_alpha* convention, cos-delta included). The propagation convention is
not trusted from documentation alone: the yogatara gate cross-checks the
propagated positions of named stars against swe.fixstar2_ut, so a wrong
convention fails the suite loudly.
"""

import csv
import gzip
import math
import struct
from pathlib import Path

MAGIC = b"RTSK"
VERSION = 1
RECORD = 24
EPOCH_YEAR = 2026.0
J2000_JD = 2451545.0
EPOCH_JD = J2000_JD + (EPOCH_YEAR - 2000.0) * 365.25
MAG_LIMIT = 6.5


def load_athyg(csv_gz: Path, mag_limit: float = MAG_LIMIT,
               force_hips: set[int] | None = None) -> list[dict]:
    """Parse the HYGLike subset; keep mag <= limit plus any force-included
    HIP ids (line figures must never dangle)."""
    force_hips = force_hips or set()
    stars: list[dict] = []
    dt = EPOCH_YEAR - 2000.0
    with gzip.open(csv_gz, "rt", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            # ATHYG carries the Sun as its first row (proper "Sol",
            # mag -26.7, no HIP). It is a graha, not a fixed star: the
            # renderer places it from the live engine, never the pack.
            if (row.get("proper") or "").strip() == "Sol":
                continue
            try:
                mag = float(row["mag"])
            except (ValueError, KeyError):
                continue
            hip = int(float(row["hip"])) if row.get("hip") else 0
            if mag > mag_limit and hip not in force_hips:
                continue
            try:
                ra = float(row["rarad"])
                dec = float(row["decrad"])
            except (ValueError, KeyError):
                continue
            # propagate proper motion (rad/yr) to the asset epoch
            pmra = float(row["pmrarad"] or 0.0)
            pmdec = float(row["pmdecrad"] or 0.0)
            dec_e = dec + pmdec * dt
            cosd = math.cos(dec_e) or 1e-9
            ra_e = ra + (pmra * dt) / cosd
            try:
                bv = float(row["ci"]) if row.get("ci") else 0.0
            except ValueError:
                bv = 0.0
            stars.append({
                "hip": hip,
                "mag": mag,
                "bv": max(-2.0, min(2.0, bv)),
                "ra": ra_e,
                "dec": dec_e,
                "proper": (row.get("proper") or "").strip(),
                "bayer": (row.get("bayer") or "").strip(),
                "con": (row.get("con") or "").strip(),
            })
    stars.sort(key=lambda s: s["mag"])
    return stars


def unit_vec(ra: float, dec: float) -> tuple[float, float, float]:
    cd = math.cos(dec)
    return (cd * math.cos(ra), cd * math.sin(ra), math.sin(dec))


def encode(stars: list[dict], out: Path,
           yogatara_hips: set[int] | None = None) -> dict[int, int]:
    """Write stars-v1.bin; returns hip -> record index for join tables."""
    yogatara_hips = yogatara_hips or set()
    hip_index: dict[int, int] = {}
    with out.open("wb") as fh:
        fh.write(struct.pack("<4sBBHI d 12x", MAGIC, VERSION, 0,
                             RECORD, len(stars), EPOCH_JD))
        for i, s in enumerate(stars):
            x, y, z = unit_vec(s["ra"], s["dec"])
            flags = (1 if s["proper"] else 0) | \
                    (2 if s["hip"] in yogatara_hips else 0)
            fh.write(struct.pack(
                "<3f h h I B 3x",
                x, y, z,
                int(round(s["mag"] * 1000)),
                int(round(s["bv"] * 1000)),
                s["hip"], flags))
            if s["hip"]:
                hip_index[s["hip"]] = i
    return hip_index


def decode(path: Path) -> list[dict]:
    """Round-trip reader used by the gates (not by the renderer)."""
    out = []
    with path.open("rb") as fh:
        magic, ver, _flags, rec, count, epoch = struct.unpack(
            "<4sBBHI d 12x", fh.read(32))
        if magic != MAGIC or ver != VERSION or rec != RECORD:
            raise ValueError("stars-v1.bin header mismatch")
        for _ in range(count):
            x, y, z, mag, bv, hip, flags = struct.unpack(
                "<3f h h I B 3x", fh.read(RECORD))
            out.append({"x": x, "y": y, "z": z, "mag": mag / 1000,
                        "bv": bv / 1000, "hip": hip, "flags": flags,
                        "epoch_jd": epoch})
    return out
