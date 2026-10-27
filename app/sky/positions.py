#!/usr/bin/env python3
# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
"""The live-sky payload: grahas in equatorial-of-date coordinates plus
the frame data the renderer draws arcs from.

Everything here is draw-ready for the EQD scene frame: RA/Dec of date
for sprite placement, tropical AND sidereal ecliptic longitudes for
readouts, the ayanamsa and obliquity for arc construction, GMST for the
horizon mode quaternion. The founding-chart gate pins this module's
sidereal longitudes to the /v1/chart output, so the two surfaces can
never drift apart.
"""

import math

import swisseph as swe
from jhora import const
from jhora.panchanga import drik

from ..astro import context as C

# (display name, swe body for the equatorial sprite, drik body for the
# sidereal readout). Sidereal longitudes come from drik.sidereal_longitude,
# the exact code path the chart engine walks, so the founding gate holds
# the two public surfaces identical BY CONSTRUCTION rather than by flag
# archaeology. The engine's node is the MEAN node (const._RAHU == 10).
GRAHA_TABLE = [
    ("Sūrya", swe.SUN, const._SUN),
    ("Candra", swe.MOON, const._MOON),
    ("Maṅgala", swe.MARS, const._MARS),
    ("Budha", swe.MERCURY, const._MERCURY),
    ("Guru", swe.JUPITER, const._JUPITER),
    ("Śukra", swe.VENUS, const._VENUS),
    ("Śani", swe.SATURN, const._SATURN),
]
NODE = swe.MEAN_NODE

_FLAGS_EQ = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_EQUATORIAL
_FLAGS_ECL = swe.FLG_SWIEPH | swe.FLG_SPEED


def _nak_pada(sid_lon: float) -> tuple[int, int, str]:
    ni = int(sid_lon // (360.0 / 27.0)) % 27
    pada = int((sid_lon % (360.0 / 27.0)) // (360.0 / 108.0)) + 1
    return ni, pada, C.NAK_IAST[ni]


def sky_at(jd_ut: float, ayanamsa: str,
           lat: float | None = None, lon: float | None = None) -> dict:
    """Assumes the caller holds the ayanamsa frame (C.frame)."""
    ay = C.ayanamsa_value(jd_ut)
    # true obliquity + nutation come from the ecliptic/nutation record
    ecl = swe.calc_ut(jd_ut, swe.ECL_NUT, swe.FLG_SWIEPH)[0]
    obliquity = ecl[0]

    topo = lat is not None and lon is not None
    if topo:
        swe.set_topo(lon, lat, 0.0)

    grahas: dict[str, dict] = {}

    def one(name: str, swe_body: int, drik_body: int, use_topo: bool):
        fl_eq = _FLAGS_EQ | (swe.FLG_TOPOCTR if use_topo else 0)
        eq = swe.calc_ut(jd_ut, swe_body, fl_eq)[0]
        # readout longitudes stay geocentric (sastric convention)
        ec = swe.calc_ut(jd_ut, swe_body, _FLAGS_ECL)[0]
        trop = ec[0] % 360.0
        sid = float(drik.sidereal_longitude(jd_ut, drik_body)) % 360.0
        ni, pada, nak = _nak_pada(sid)
        grahas[name] = {
            "ra_deg": round(eq[0], 6),
            "dec_deg": round(eq[1], 6),
            "ecl_lon_trop": round(trop, 6),
            "ecl_lon_sid": round(sid, 6),
            "speed_lon": round(ec[3], 6),
            "retro": ec[3] < 0,
            "nakshatra": nak,
            "nak_index": ni,
            "pada": pada,
        }

    for name, swe_body, drik_body in GRAHA_TABLE:
        # Moon sprite goes topocentric when a place is given (the visible
        # sky); all readouts remain geocentric.
        one(name, swe_body, drik_body, use_topo=(topo and swe_body == swe.MOON))

    one("Rāhu", NODE, const._RAHU, use_topo=False)
    rahu = grahas["Rāhu"]
    ketu_trop = (rahu["ecl_lon_trop"] + 180.0) % 360.0
    ketu_sid = (rahu["ecl_lon_sid"] + 180.0) % 360.0
    # Ketu mirrors Rahu through the center: opposite ecliptic point.
    k_ni, k_pada, k_nak = _nak_pada(ketu_sid)
    ra_k, dec_k = _ecl_to_eq(ketu_trop, 0.0, obliquity)
    grahas["Ketu"] = {
        "ra_deg": round(ra_k, 6), "dec_deg": round(dec_k, 6),
        "ecl_lon_trop": round(ketu_trop, 6),
        "ecl_lon_sid": round(ketu_sid, 6),
        "speed_lon": rahu["speed_lon"], "retro": rahu["retro"],
        "nakshatra": k_nak, "nak_index": k_ni, "pada": k_pada,
    }

    gmst_h = swe.sidtime(jd_ut)
    out = {
        "jd_ut": jd_ut,
        "ayanamsa": {"name": ayanamsa, "deg": round(ay, 6)},
        "obliquity_deg": round(obliquity, 6),
        "sidereal": {"gmst_h": round(gmst_h, 6)},
        "grahas": grahas,
        "arcs": {
            # sidereal boundaries expressed in the tropical frame the
            # renderer draws in: trop = sid + ayanamsa
            "rasi_starts_trop": [round((k * 30 + ay) % 360.0, 6)
                                 for k in range(12)],
            "nakshatra_starts_trop": [
                round((n * (360.0 / 27.0) + ay) % 360.0, 6)
                for n in range(27)],
            "abhijit_span_trop": [
                round((276.666667 + ay) % 360.0, 6),
                round((280.888889 + ay) % 360.0, 6)],
        },
    }
    if topo:
        out["sidereal"]["lst_deg"] = round((gmst_h * 15.0 + lon) % 360.0, 6)
    return out


def _ecl_to_eq(lon_deg: float, lat_deg: float,
               obliquity_deg: float) -> tuple[float, float]:
    lo, la, ob = map(math.radians, (lon_deg, lat_deg, obliquity_deg))
    sin_dec = (math.sin(la) * math.cos(ob) +
               math.cos(la) * math.sin(ob) * math.sin(lo))
    dec = math.asin(sin_dec)
    y = math.sin(lo) * math.cos(ob) - math.tan(la) * math.sin(ob)
    x = math.cos(lo)
    ra = math.atan2(y, x) % (2 * math.pi)
    return math.degrees(ra), math.degrees(dec)
