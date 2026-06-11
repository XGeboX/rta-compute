#!/usr/bin/env python3
# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
"""Golden gates. The reference chart is RTA's own founding moment
(28 Feb 2025, 17:55:55 local, Bradford UK) — public brand data, fixtures
cross-validated against an independent Jagannatha Hora computation
(lagna agrees to the arcsecond; luminaries within 40 arcsec, the known
inter-implementation True-Pushya drift).

Rules of the suite: static oracles, no network, no clock dependence
except where an `asof` is pinned. A failing gate means investigate,
never loosen."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.astro import context as C  # noqa: E402
from app.astro import dasha as D    # noqa: E402
from app.astro import gochara as G  # noqa: E402
from app.astro import instant as I  # noqa: E402
from app.astro import panchanga as P  # noqa: E402
from app.astro import vargas as V   # noqa: E402

JD = None
PLACE = None


def setup_module(_m):
    global JD, PLACE
    JD = C.jd_at((2025, 2, 28), (17, 55, 55))
    PLACE = C.place_of("Bradford", 53.7938, -1.7564, 0.0)


def test_lagna_golden():
    with C.frame("TRUE_PUSHYA"):
        pos = C.positions_at(JD, PLACE)
    lag = pos["lagna"]
    assert C.RASI_IAST[lag["sign_index"]] == "Siṃha"
    assert abs(lag["degree"] - 20.534) < 0.002
    assert lag["nakshatra"] == "Pūrva Phālgunī" and lag["pada"] == 3


def test_luminaries_golden():
    with C.frame("TRUE_PUSHYA"):
        pos = C.positions_at(JD, PLACE)
    sun, moon = pos["Sūrya"], pos["Candra"]
    assert C.RASI_IAST[sun["sign_index"]] == "Kumbha"
    assert abs(sun["degree"] - 17.3259) < 0.002
    assert sun["nakshatra"] == "Śatabhiṣā" and sun["pada"] == 4
    assert C.RASI_IAST[moon["sign_index"]] == "Kumbha"
    assert abs(moon["degree"] - 27.1164) < 0.002
    assert moon["nakshatra"] == "Pūrvabhādrapadā" and moon["pada"] == 3


def test_tropical_is_sidereal_plus_ayanamsa():
    with C.frame("TRUE_PUSHYA"):
        sid = C.positions_at(JD, PLACE, zodiac="sidereal")
        trop = C.positions_at(JD, PLACE, zodiac="tropical")
        ay = C.ayanamsa_value(JD)
    d = (trop["Sūrya"]["longitude"] - sid["Sūrya"]["longitude"]) % 360.0
    assert abs(d - ay) < 2e-4  # positions round to 4 decimals by contract
    assert "nakshatra" not in trop["Sūrya"]  # sidereal construct withheld


def test_vargas_d9_d144():
    with C.frame("TRUE_PUSHYA"):
        d9 = V.varga_chart(JD, PLACE, 9)
        d144 = V.varga_chart(JD, PLACE, 144)
    assert d9["lagna"]["sign_index"] == 6     # Tulā navāṁśa lagna
    assert d144["lagna"]["sign_index"] == 2   # Mithuna D144 lagna
    assert d144["name"] == "Dvādaśa-dvādaśāṁśa"


def test_sensitivity_honesty():
    with C.frame("TRUE_PUSHYA"):
        s1 = V.lagna_sensitivity(JD, PLACE, 1)
        s144 = V.lagna_sensitivity(JD, PLACE, 144)
    assert s1["verdict"] == "stable"            # D1 holds beyond the cap
    assert s144["verdict"] == "needs-seconds-accurate-time"
    assert s144["beyond_traditional_ceiling"] is True
    assert s144["stable_plus_min"] < 1.5        # ~32s measured


def test_dasha_stack_golden():
    with C.frame("TRUE_PUSHYA"):
        stack = D.stack_at(JD, PLACE, C.jd_at((2026, 6, 11), (12, 0, 0)),
                           depth=3)
    lords = [(s["lord"], s["start"]) for s in stack]
    assert lords[0] == ("Guru", "2016-08-15")
    assert lords[1][0] == "Śukra" and lords[1][1] == "2024-06-27"
    assert lords[2][0] == "Śani" and lords[2][1] == "2026-03-14"


def test_panchanga_golden():
    with C.frame("TRUE_PUSHYA"):
        pc = P.panchanga_at(JD, PLACE)
    assert pc["tithi"] == {"number": 1, "name": "Pratipadā",
                           "paksha": "Śukla"}
    assert pc["vara"]["name"] == "Śukravāra"           # 28 Feb 2025 = Friday
    assert pc["nakshatra"]["name"] == "Pūrvabhādrapadā"
    assert pc["nakshatra"]["pada"] == 3
    assert pc["karana"]["number"] in range(1, 61)


def test_karana_mapping():
    assert P.karana_name(36) == "Viṣṭi"     # verified against Dṛṣṭi server
    assert P.karana_name(1) == "Kiṃstughna"
    assert P.karana_name(60) == "Nāga"
    assert P.karana_name(2) == "Bava"


def test_av_invariants():
    """BAV column == prastara contributor sum; SAV == BAV column sums."""
    with C.frame("TRUE_PUSHYA"):
        natal = C.natal_bundle(JD, PLACE)
    for g in range(7):
        for s in range(12):
            assert natal["bav"][g][s] == sum(
                natal["prastara"][g][c][s] for c in range(8)), (g, s)
    for s in range(12):
        assert natal["sav"][s] == sum(natal["bav"][g][s] for g in range(7))


def test_state_corruption_guard():
    """Poison the global frame; the next frame() must fully recover."""
    with C.frame("LAHIRI"):
        lahiri_sun = C.positions_at(JD, PLACE)["Sūrya"]["longitude"]
    with C.frame("TRUE_PUSHYA"):
        tp_sun = C.positions_at(JD, PLACE)["Sūrya"]["longitude"]
    assert abs(((lahiri_sun - tp_sun) + 180) % 360 - 180) > 0.3  # frames differ
    assert abs(tp_sun - (300 + 17.3259)) < 0.01                   # TP exact


def test_instant_deterministic():
    asof = C.jd_at((2026, 6, 11), (6, 0, 0))
    with C.frame("TRUE_PUSHYA"):
        a = I.instant(JD, PLACE, asof, PLACE)
    with C.frame("TRUE_PUSHYA"):
        b = I.instant(JD, PLACE, asof, PLACE)
    assert a == b
    assert a["doctrine"] == "computed-not-generated"
    assert a["citations_complete"] is True
    assert all(r["citation"]["source"] for r in a["fired_rules"])
    assert len(a["dasha_stack"]) == 5


def test_tara_rank_formula():
    assert C.tara_rank(4, 4) == 1     # janma
    assert C.tara_rank(4, 13) == 1    # +9
    assert C.tara_rank(4, 5) == 2     # sampat
    assert C.tara_rank(4, 3) == 9     # parama-mitra (one behind)
