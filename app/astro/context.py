#!/usr/bin/env python3
# This file is part of rta-compute.
#
# rta-compute is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version. See LICENSE.
"""Frame management and natal computation.

PyJhora's ayanāṁśa is GLOBAL MUTABLE STATE. Every computation in this
service runs inside `frame(...)`, which takes a process-wide lock, pins the
requested frame, computes, and releases. Endpoints are sync `def` (FastAPI
threadpool) — the lock makes concurrent requests within a worker safe; run
multiple uvicorn worker PROCESSES for parallelism.

Tropical doctrine: PyJhora computes sidereal natively; the tropical frame is
derived exactly as tropical = sidereal + ayanāṁśa(jd) (the definitional
relation). Verified: PyJhora's `set_tropical_planets()` does not alter
longitudes and is not used here.

No birth data is ever persisted by this module. Stateless by design.
"""

import io
import sys
import threading
from contextlib import contextmanager

_orig_stdout = sys.stdout
sys.stdout = io.StringIO()
try:
    from jhora.panchanga import drik
    from jhora.horoscope.chart import charts
    from jhora.horoscope.chart import ashtakavarga as jav
    from jhora import utils as jutils
    from jhora import const as jconst
    import swisseph as swe
finally:
    sys.stdout = _orig_stdout

RASI_IAST = ["Meṣa", "Vṛṣabha", "Mithuna", "Karkaṭa", "Siṃha", "Kanyā",
             "Tulā", "Vṛścika", "Dhanus", "Makara", "Kumbha", "Mīna"]
RASI_EN = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
           "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
GRAHA_IAST = ["Sūrya", "Candra", "Maṅgala", "Budha", "Guru", "Śukra",
              "Śani", "Rāhu", "Ketu"]
GRAHA_EN = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus",
            "Saturn", "Rahu", "Ketu"]
GRAHA_INDEX = {n: i for i, n in enumerate(GRAHA_IAST)}
NAK_IAST = ["Aśvinī", "Bharaṇī", "Kṛttikā", "Rohiṇī", "Mṛgaśīrṣā", "Ārdrā",
            "Punarvasu", "Puṣya", "Āśleṣā", "Maghā", "Pūrva Phālgunī",
            "Uttara Phālgunī", "Hasta", "Citrā", "Svāti", "Viśākhā",
            "Anurādhā", "Jyeṣṭhā", "Mūla", "Pūrvāṣāḍhā", "Uttarāṣāḍhā",
            "Śravaṇa", "Dhaniṣṭhā", "Śatabhiṣā", "Pūrvabhādrapadā",
            "Uttarabhādrapadā", "Revatī"]
RASI_LORDS = [2, 5, 3, 1, 0, 3, 5, 2, 4, 6, 6, 4]

AYANAMSAS = ("TRUE_PUSHYA", "LAHIRI", "RAMAN", "KP")
_AYANAMSA_MAP = {"KP": "KP"}  # request name -> drik mode name (identity unless aliased)

_FRAME_LOCK = threading.Lock()
DEFAULT_AYANAMSA = "TRUE_PUSHYA"


@contextmanager
def frame(ayanamsa: str = DEFAULT_AYANAMSA):
    """Pin the sidereal frame for the duration of one computation.

    Process-wide lock: PyJhora's mode is global; concurrent threads must not
    interleave set-and-compute sequences."""
    if ayanamsa not in AYANAMSAS:
        raise ValueError(f"unsupported ayanamsa {ayanamsa!r}; one of {AYANAMSAS}")
    mode = _AYANAMSA_MAP.get(ayanamsa, ayanamsa)
    with _FRAME_LOCK:
        drik.set_ayanamsa_mode(mode)
        yield


def place_of(name, lat, lon, tz_hours):
    return drik.Place(name, float(lat), float(lon), float(tz_hours))


def jd_at(date_tuple, time_tuple):
    """Julian day from LOCAL civil date+time (PyJhora convention; tz rides
    in the Place passed alongside)."""
    return jutils.julian_day_number(tuple(date_tuple), tuple(time_tuple))


def ayanamsa_value(jd):
    return float(drik.get_ayanamsa_value(jd))


def nak_of(longitude):
    ni = int(longitude // (360.0 / 27.0)) % 27
    pada = int((longitude % (360.0 / 27.0)) // (360.0 / 108.0)) + 1
    return ni, pada


def _house_to_planet_list(raw_chart):
    """PyJhora 1-D chart array: 12 strings, '/'-joined planet indices, 'L'
    for lagna (the get_ashtaka_varga input format)."""
    out = [""] * 12
    for entry in raw_chart:
        idx, (sign, _deg) = entry[0], entry[1]
        tok = "L" if not isinstance(idx, int) else str(idx)
        if isinstance(idx, int) and idx > 8:
            continue
        out[sign] = tok if not out[sign] else out[sign] + "/" + tok
    return out


def positions_at(jd, place, zodiac="sidereal"):
    """D-1 positions. Sidereal natively; tropical = sidereal + ayanāṁśa(jd).

    Returns {"lagna": {...}, "<Graha>": {sign_index, degree, longitude,
    retrograde, nakshatra, pada}} — nakṣatra fields only in sidereal frame
    (nakṣatras are a sidereal construct)."""
    raw = charts.divisional_chart(jd, place, divisional_chart_factor=1)
    retro = drik.planets_in_retrograde(jd, place)
    shift = ayanamsa_value(jd) if zodiac == "tropical" else 0.0

    def conv(sign, deg):
        lon = (sign * 30 + deg + shift) % 360.0
        return int(lon // 30), lon % 30.0, lon

    lsign, ldeg, llon = conv(raw[0][1][0], raw[0][1][1])
    out = {"lagna": {"sign_index": lsign, "degree": round(ldeg, 4),
                     "longitude": round(llon, 4)}}
    for entry in raw[1:]:
        idx = entry[0]
        if not isinstance(idx, int) or idx > 8:
            continue
        s, d, lon = conv(entry[1][0], entry[1][1])
        rec = {"sign_index": s, "degree": round(d, 4),
               "longitude": round(lon, 4), "retrograde": idx in retro}
        if zodiac == "sidereal":
            ni, pada = nak_of(lon)
            rec["nakshatra"] = NAK_IAST[ni]
            rec["nak_index"] = ni
            rec["pada"] = pada
        out[GRAHA_IAST[idx]] = rec
    if zodiac == "sidereal":
        ni, pada = nak_of(llon)
        out["lagna"].update({"nakshatra": NAK_IAST[ni], "nak_index": ni,
                             "pada": pada})
    return out


def tropical_houses(jd, place, hsys=b"P"):
    """Tropical house cusps via Swiss Ephemeris (default Placidus).
    Returns {"cusps": [12 longitudes], "asc": lon, "mc": lon}."""
    jd_ut = jd - place.timezone / 24.0
    cusps, ascmc = swe.houses(jd_ut, place.latitude, place.longitude, hsys)
    return {"cusps": [round(c, 4) for c in cusps[:12]],
            "asc": round(ascmc[0], 4), "mc": round(ascmc[1], 4)}


def natal_bundle(jd, place):
    """Everything the gates/instant layers need, computed fresh per request
    (sidereal frame assumed pinned by caller). No persistence."""
    pos = positions_at(jd, place, zodiac="sidereal")
    raw = charts.divisional_chart(jd, place, divisional_chart_factor=1)
    h2p = _house_to_planet_list(raw)
    binna, samudaya, prastara = jav.get_ashtaka_varga(h2p)
    moon_nak = pos["Candra"]["nak_index"]
    return {
        "positions": pos,
        "lagna_sign_index": pos["lagna"]["sign_index"],
        "moon_sign_index": pos["Candra"]["sign_index"],
        "janma_nak_index": moon_nak,
        "bav": [[int(b) for b in row] for row in binna],      # [graha0..6,lagna][sign]
        "sav": [int(s) for s in samudaya],                     # [sign]
        "prastara": [[[int(v) for v in row] for row in pl] for pl in prastara],
    }


def tara_rank(janma_nak_index, nak_index):
    """Nava-tārā rank 1..9 of nak counted from the janma nakṣatra."""
    return ((nak_index - janma_nak_index) % 9) + 1
