#!/usr/bin/env python3
# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
"""Atlas gates. The search behavior gates run on any built source; the
india-coverage gate is meaningful only for the shipping allCountries build
and self-skips on the fast cities500 source (CI test job), enforcing where
it matters: inside the image build, which always uses allCountries."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.atlas import search as A          # noqa: E402
from app.atlas.build_atlas import built_source  # noqa: E402

pytestmark = pytest.mark.skipif(
    not A.DB_PATH.exists(), reason="atlas.db not built in this checkout")


def test_major_cities_resolve_population_first():
    faridabad = A.search("Faridabad")
    assert faridabad and faridabad[0]["country"] == "IN"
    assert abs(faridabad[0]["lat"] - 28.41) < 0.1
    bradford = A.search("Bradford")
    assert bradford and bradford[0]["country"] == "GB"
    assert bradford[0]["tz"] == "Europe/London"


def test_diacritic_folding_resolves():
    # 'Lodz' typed plain must find Łódź; folding is in the tokenizer.
    rows = A.search("Lodz")
    assert rows and any(r["country"] == "PL" for r in rows[:3])


def test_meta_records_source():
    assert built_source() in {"allCountries", "cities500"}


def test_india_village_coverage():
    """A sub-cities500 Indian village must resolve by name in the shipping
    atlas. Fixture pinned from the built allCountries data itself."""
    if built_source() != "allCountries":
        pytest.skip("india-coverage gate runs on the allCountries build")
    rows = A.search(VILLAGE_NAME)
    assert rows, f"{VILLAGE_NAME} did not resolve at all"
    hit = next((r for r in rows if r["country"] == "IN"
                and abs(r["lat"] - VILLAGE_LAT) < 0.05
                and abs(r["lon"] - VILLAGE_LON) < 0.05), None)
    assert hit, f"{VILLAGE_NAME} resolved without the pinned IN match"
    assert hit["tz"] == "Asia/Kolkata"


# Pinned from the 2026-06-12 allCountries build (5,207,731 places):
# Zochachhuah, a Mizoram village of 333 people, absent from cities500 —
# exactly the class of birth place the deeper source exists to resolve.
VILLAGE_NAME = "Zochachhuah"
VILLAGE_LAT = 22.1325
VILLAGE_LON = 92.77333
