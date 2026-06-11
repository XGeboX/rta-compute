#!/usr/bin/env python3
# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
"""Rectification gates, fixtured on the RTA founding chart (public brand
data). Pinned 2026-06-11 from a verified run; a failing gate means
investigate, never loosen."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.astro import context as C   # noqa: E402
from app.astro import rectify as R   # noqa: E402

JD = None
PLACE = None


def setup_module(_m):
    global JD, PLACE
    JD = C.jd_at((2025, 2, 28), (17, 55, 55))
    PLACE = C.place_of("Bradford", 53.7938, -1.7564, 0.0)


def test_boundary_scan_pinned():
    with C.frame("TRUE_PUSHYA"):
        scan = R.boundary_scan(JD, PLACE, 20, 20)
    assert len(scan["boundaries"]) == 14
    assert scan["live_discriminators"] == [3, 9, 10, 12, 24]  # D1 stable
    first = scan["boundaries"][0]
    assert first["factor"] == 12
    assert abs(first["offset_min"] - (-17.77)) < 0.05
    assert (first["from_sign"], first["to_sign"]) == ("Kumbha", "Mīna")
    assert "decisive" in scan["verdict"]


def test_boundary_scan_stable_window():
    """A tight window with no flips must say so honestly."""
    with C.frame("TRUE_PUSHYA"):
        scan = R.boundary_scan(JD, PLACE, 1, 1, factors=[1])
    assert scan["boundaries"] == []
    assert "varga-stable" in scan["verdict"]


def test_d9_flip_bisection_consistency():
    """The flip moment itself must separate the two signs."""
    with C.frame("TRUE_PUSHYA"):
        flips = R.boundaries_in_window(JD, PLACE, 9, 20, 20)
        f = next(x for x in flips if abs(x["offset_min"] - (-3.12)) < 0.1)
        day = 1.0 / 1440.0
        before = R._varga_lagna(JD + (f["offset_min"] - 0.02) * day, PLACE, 9)
        after = R._varga_lagna(JD + (f["offset_min"] + 0.02) * day, PLACE, 9)
    assert C.RASI_IAST[before] == f["from_sign"] == "Kanyā"
    assert C.RASI_IAST[after] == f["to_sign"] == "Tulā"


EVENTS = [
    {"date": (2020, 6, 1), "type": "education", "label": "edu"},
    {"date": (2025, 1, 15), "type": "marriage", "label": "marriage"},
]


def test_sweep_shape_and_karaka_lens():
    with C.frame("TRUE_PUSHYA"):
        sweep = R.rectify_sweep(JD, PLACE, 20, 20, EVENTS, step_min=10)
    assert len(sweep["candidates"]) == 5  # -20..+20 by 10
    c0 = sweep["candidates"][0]
    assert c0["offset_min"] == -20.0
    # Guru MD covers 2020: education karakas include Guru -> maha match.
    ev0 = c0["events"][0]
    assert ev0["maha"] == "Guru"
    assert ev0["karaka_match"]["maha"] is True
    assert ev0["karaka_match"]["citation"]["source"].startswith("Bṛhat")
    assert c0["karaka_score"] == 3
    # Cascade lagnas present for every candidate.
    for c in sweep["candidates"]:
        assert set(c["varga_lagnas"].keys()) == set(R.CASCADE)
    assert "human judgment" in sweep["doctrine"]


def test_sweep_deterministic():
    with C.frame("TRUE_PUSHYA"):
        a = R.rectify_sweep(JD, PLACE, 10, 10, EVENTS, step_min=5)
    with C.frame("TRUE_PUSHYA"):
        b = R.rectify_sweep(JD, PLACE, 10, 10, EVENTS, step_min=5)
    assert a == b


def test_event_types_sync_with_schema():
    """The schema Literal and the kāraka table must never drift apart."""
    from typing import get_args
    from app.schemas import RectifyEvent
    literal = set(get_args(RectifyEvent.model_fields["type"].annotation))
    assert literal == set(R.EVENT_KARAKAS.keys())


def test_unknown_event_type_fails_loudly():
    import pytest
    with C.frame("TRUE_PUSHYA"):
        with pytest.raises(ValueError, match="unknown event type"):
            R.rectify_sweep(JD, PLACE, 5, 5,
                            [{"date": (2020, 1, 1), "type": "lost-love"}],
                            step_min=5)


def test_work_cap_enforced():
    import pytest
    events = [{"date": (2020, 1, 1), "type": "career"}] * 40
    with C.frame("TRUE_PUSHYA"):
        with pytest.raises(ValueError, match="work cap"):
            R.rectify_sweep(JD, PLACE, 120, 120, events, step_min=0.5)


def test_boundary_sequence_is_sign_continuous():
    """For each factor, consecutive boundaries must chain: the next flip's
    from_sign equals the previous flip's to_sign (no skipped intermediate
    signs, even at this 53°N latitude where ascension compresses)."""
    with C.frame("TRUE_PUSHYA"):
        for f in (9, 24, 60):
            flips = R.boundaries_in_window(JD, PLACE, f, 40, 40)
            for a, b in zip(flips, flips[1:]):
                assert a["to_sign"] == b["from_sign"], (f, a, b)
