#!/usr/bin/env python3
# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
"""Sunrise-anchored vaara gates.

The classical vara runs sunrise to sunrise: before local sunrise the
previous day's vara persists; it never flips at civil midnight or at the
local-noon JD boundary. The old `drik.vaara(jd)` call (no place argument)
flipped at the JD integer boundary -- local noon in this codebase's
wall-clock JD frame -- so every pre-noon query reported the previous vara.

Static oracles below were pinned live from the Drsti reference engine
(panchanga_unified.PanchangaCalculator, Faridabad 28.4089N 77.3178E +5:30,
sunrise 05:22 IST on 2026-06-03):

    2026-06-03 03:00 -> Mangalavara   (pre-sunrise: Tuesday persists)
    2026-06-03 06:00 -> Budhavara
    2026-06-03 12:00 -> Budhavara     (the old code failed here)
    2026-06-03 23:30 -> Budhavara     (no flip at sunset or midnight)
    2026-06-04 04:00 -> Budhavara     (pre-sunrise: Wednesday persists)
    2026-06-04 06:00 -> Guruvara

Numbering is Sunday==1 (Ravivara) .. Saturday==7 (Sanivara)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.astro import context as C     # noqa: E402
from app.astro import panchanga as P   # noqa: E402

FARIDABAD = ("Faridabad", 28.4089, 77.3178, 5.5)


def _vara(date_tuple, time_tuple):
    place = C.place_of(*FARIDABAD)
    jd = C.jd_at(date_tuple, time_tuple)
    return P.panchanga_at(jd, place)["vara"]


@pytest.mark.parametrize("date_tuple,time_tuple,number,name", [
    ((2026, 6, 3), (3, 0, 0), 3, "Maṅgalavāra"),   # pre-sunrise Wed -> Tue persists
    ((2026, 6, 3), (6, 0, 0), 4, "Budhavāra"),
    ((2026, 6, 3), (12, 0, 0), 4, "Budhavāra"),          # old code: previous vara here
    ((2026, 6, 3), (23, 30, 0), 4, "Budhavāra"),         # no flip at sunset/midnight
    ((2026, 6, 4), (4, 0, 0), 4, "Budhavāra"),           # pre-sunrise Thu -> Wed persists
    ((2026, 6, 4), (6, 0, 0), 5, "Guruvāra"),
])
def test_vara_is_sunrise_anchored(date_tuple, time_tuple, number, name):
    v = _vara(date_tuple, time_tuple)
    assert v["number"] == number
    assert v["name"] == name
