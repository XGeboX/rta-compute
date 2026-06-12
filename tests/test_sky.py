#!/usr/bin/env python3
# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
"""Sky pipeline gates.

The yogatara identification gate is the heart: every nakshatra's HIP is
compared against swe.fixstar2_ut for the same star name. A wrong
identification is degrees of error against a tolerance of arcseconds;
nothing misremembered can ship."""

import json
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.astro import context as C          # noqa: E402
from app.sky import asterisms, catalog, figures  # noqa: E402
from app.sky import positions as P          # noqa: E402
from app.sky.build_sky import build         # noqa: E402

RAW = Path(__file__).resolve().parents[1] / "data" / "sky" / "raw"

pytestmark = pytest.mark.skipif(
    not (RAW / "hyglike_from_athyg_v33.csv.gz").exists(),
    reason="sky raw data not fetched (scripts/fetch_sky_data.sh)")


@pytest.fixture(scope="module")
def dist(tmp_path_factory):
    out = tmp_path_factory.mktemp("sky-dist")
    manifest = build(RAW, out)
    return out, manifest


def test_counts_and_no_silent_truncation(dist):
    _out, m = dist
    c = m["counts"]
    assert c["stars"] > 8500
    assert c["line_pairs"] > 700
    assert c["boundary_points"] == 12948  # VI/49 regression value
    assert c["nakshatras"] == 28
    # dropped-segment budget: catalog gaps exist (xi UMa) but a parser
    # regression eating figures must fail here
    dropped = m["dropped_line_hips"]
    assert len(dropped) <= 2, dropped
    assert sum(len(v) for v in dropped.values()) <= 3, dropped


def test_star_record_roundtrip_and_order(dist):
    out, m = dist
    stars_file = out / m["assets"]["stars"]["file"]
    rows = catalog.decode(stars_file)
    assert len(rows) == m["counts"]["stars"]
    mags = [r["mag"] for r in rows]
    assert mags == sorted(mags), "buffer must be magnitude-ascending"
    for r in rows[:200]:
        n = math.sqrt(r["x"]**2 + r["y"]**2 + r["z"]**2)
        assert abs(n - 1.0) < 1e-5, "unit vectors expected"
    # quantization round-trip: mag/bv at exactly milli resolution
    assert all(abs(r["mag"] * 1000 - round(r["mag"] * 1000)) < 1e-6
               for r in rows[:50])


def test_yogatara_identifications_against_swisseph(dist):
    """Every nakshatra HIP must sit within arcminutes of the star the
    Swiss Ephemeris knows by that traditional name (J2000 frame, PM to
    the same instant). Misidentification = degrees; the gate ends it."""
    import swisseph as swe
    out, m = dist
    stars_file = out / m["assets"]["stars"]["file"]
    rows = catalog.decode(stars_file)
    by_hip = {r["hip"]: r for r in rows if r["hip"]}
    jd = catalog.EPOCH_JD
    failures = []
    for n in asterisms.NAKSHATRAS:
        hip = n["yogatara_hip"]
        assert hip in by_hip, f"{n['name_iast']}: HIP {hip} not in buffer"
        assert by_hip[hip]["flags"] & 2, f"{n['name_iast']}: flag unset"
        try:
            xx, _name, _fl = swe.fixstar2_ut(
                n["swe_name"], jd,
                swe.FLG_SWIEPH | swe.FLG_EQUATORIAL | swe.FLG_J2000)
        except swe.Error as exc:
            failures.append(f"{n['name_iast']}: swe cannot resolve "
                            f"{n['swe_name']!r}: {exc}")
            continue
        ra, dec = math.radians(xx[0]), math.radians(xx[1])
        sx = math.cos(dec) * math.cos(ra)
        sy = math.cos(dec) * math.sin(ra)
        sz = math.sin(dec)
        r = by_hip[hip]
        dot = max(-1.0, min(1.0, sx * r["x"] + sy * r["y"] + sz * r["z"]))
        sep_arcsec = math.degrees(math.acos(dot)) * 3600
        if sep_arcsec > 60.0:
            failures.append(
                f"{n['name_iast']}: HIP {hip} is {sep_arcsec:.0f} arcsec "
                f"from swe {n['swe_name']!r}")
    assert not failures, "\n".join(failures)


def test_citation_completeness():
    for n in asterisms.NAKSHATRAS:
        assert n["citations"], f"{n['name_iast']} uncited"
        assert n["swe_name"], f"{n['name_iast']} lacks swe cross-check name"
        lo, hi = n["span_sid"]
        assert 0 <= lo < 360 and 0 < hi <= 360
    ids = sorted(n["id"] for n in asterisms.NAKSHATRAS)
    assert ids == list(range(1, 29))


def test_boundaries_parse_strips():
    strips = figures.parse_boundaries(RAW / "bound_20.dat")
    assert sum(len(pts) for _c, pts in strips) == 12948
    cons = {c for c, _ in strips}
    assert {"CEP", "ARI", "UMA", "CRU"} - cons == set()


FOUNDING_T = "2025-02-28T17:55:55"


def test_sky_consistent_with_chart_longitudes():
    """The founding gate: /v1/sky sidereal longitudes must match the
    chart engine's positions for the same instant. The two public
    surfaces can never disagree."""
    jd = C.jd_at((2025, 2, 28), (17, 55, 55))
    place = C.place_of("Bradford", 53.7938, -1.7564, 0.0)
    with C.frame("TRUE_PUSHYA"):
        sky = P.sky_at(jd, "TRUE_PUSHYA")
        chart = C.positions_at(jd, place, zodiac="sidereal")
    for graha in ["Sūrya", "Candra", "Maṅgala", "Budha", "Guru",
                  "Śukra", "Śani", "Rāhu", "Ketu"]:
        a = sky["grahas"][graha]["ecl_lon_sid"]
        b = chart[graha]["longitude"]
        diff = min(abs(a - b), 360 - abs(a - b))
        assert diff < 0.01, f"{graha}: sky {a} vs chart {b}"
        assert sky["grahas"][graha]["nakshatra"] == chart[graha]["nakshatra"]


def test_sky_frame_payload_sane():
    jd = C.jd_at((2025, 2, 28), (17, 55, 55))
    with C.frame("TRUE_PUSHYA"):
        sky = P.sky_at(jd, "TRUE_PUSHYA", lat=53.7938, lon=-1.7564)
    ay = sky["ayanamsa"]["deg"]
    assert 20 < ay < 26
    assert 23.0 < sky["obliquity_deg"] < 23.7
    starts = sky["arcs"]["rasi_starts_trop"]
    assert len(starts) == 12
    assert abs((starts[1] - starts[0]) % 360 - 30) < 1e-6
    naks = sky["arcs"]["nakshatra_starts_trop"]
    assert len(naks) == 27
    assert abs(starts[0] - ay) < 1e-6  # sidereal 0 in tropical frame
    assert "lst_deg" in sky["sidereal"]
    # every graha names its nakshatra and a dec inside the zodiac band
    for g, rec in sky["grahas"].items():
        assert -35 < rec["dec_deg"] < 35, g
        assert rec["nakshatra"]


def test_sky_route_rejects_timezone_strings():
    """A '+05:30' suffix silently read as UTC would be hours of error;
    only bare ISO or trailing-Z may pass."""
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    ok = client.get("/v1/sky", params={"t": "2025-02-28T17:55:55"})
    assert ok.status_code == 200
    okz = client.get("/v1/sky", params={"t": "2025-02-28T17:55:55Z"})
    assert okz.status_code == 200
    assert okz.json()["grahas"] == ok.json()["grahas"]
    for bad in ["2025-02-28T17:55:55+05:30", "2025-02-28T17:55:55.123",
                "2025-02-28 17:55:55", "2025-02-28"]:
        res = client.get("/v1/sky", params={"t": bad})
        assert res.status_code == 422, bad
