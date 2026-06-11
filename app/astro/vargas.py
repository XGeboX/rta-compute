#!/usr/bin/env python3
# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
"""Divisional charts D1–D144 and the birth-time sensitivity computation.

Sensitivity doctrine: depth offered, honesty enforced. For any varga factor
we compute the exact clock window around the recorded birth time within
which the varga lagna is stable — bisected against the true ascendant, not
estimated from average rates. The platform shows this on every varga view;
when the recorded birth-time precision cannot support a varga, the user
sees it stated rather than discovering it from critics.
"""

import io
import sys

from . import context as C

_orig_stdout = sys.stdout
sys.stdout = io.StringIO()
try:
    from jhora.horoscope.chart import charts
finally:
    sys.stdout = _orig_stdout

# The traditional ṣoḍaśavarga set plus the extended series the platform offers.
VARGA_FACTORS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 16, 20, 24, 27, 30,
                 40, 45, 60, 81, 108, 144]
TRADITIONAL_CEILING = 60  # beyond this the methodology page carries the note

VARGA_NAMES = {1: "Rāśi", 2: "Horā", 3: "Drekkāṇa", 4: "Caturthāṁśa",
               5: "Pañcamāṁśa", 6: "Ṣaṣṭhāṁśa", 7: "Saptāṁśa",
               8: "Aṣṭamāṁśa", 9: "Navāṁśa", 10: "Daśāṁśa",
               11: "Ekādaśāṁśa", 12: "Dvādaśāṁśa", 16: "Ṣoḍaśāṁśa",
               20: "Viṁśāṁśa", 24: "Caturviṁśāṁśa", 27: "Bhāṁśa",
               30: "Triṁśāṁśa", 40: "Khavedāṁśa", 45: "Akṣavedāṁśa",
               60: "Ṣaṣṭyaṁśa", 81: "Nava-navāṁśa", 108: "Aṣṭottaraṁśa",
               144: "Dvādaśa-dvādaśāṁśa"}


def varga_chart(jd, place, factor):
    """One divisional chart (sidereal frame assumed pinned by caller).

    Returns {"factor", "name", "lagna": {sign_index, degree}, "planets":
    {Graha: {sign_index, degree}}}."""
    if factor not in VARGA_FACTORS:
        raise ValueError(f"unsupported varga factor {factor}")
    raw = charts.divisional_chart(jd, place, divisional_chart_factor=factor)
    out = {"factor": factor, "name": VARGA_NAMES[factor],
           "lagna": {"sign_index": int(raw[0][1][0]),
                     "degree": round(float(raw[0][1][1]), 4)},
           "planets": {}}
    for entry in raw[1:]:
        idx = entry[0]
        if not isinstance(idx, int) or idx > 8:
            continue
        out["planets"][C.GRAHA_IAST[idx]] = {
            "sign_index": int(entry[1][0]),
            "degree": round(float(entry[1][1]), 4)}
    return out


def all_vargas(jd, place, factors=None):
    return [varga_chart(jd, place, f) for f in (factors or VARGA_FACTORS)]


def _varga_lagna_sign(jd, place, factor):
    raw = charts.divisional_chart(jd, place, divisional_chart_factor=factor)
    return int(raw[0][1][0])


def lagna_sensitivity(jd, place, factor, max_window_min=30.0):
    """Exact clock window (minutes before/after the recorded time) within
    which this varga's lagna sign is unchanged. Bisected to ~1 second
    against the true ascendant.

    Returns {"factor", "stable_minus_min", "stable_plus_min", "verdict"}.
    Window search is capped at max_window_min each side (D1 lagna holds for
    up to ~2h; the cap keeps responses fast and the message clear)."""
    base = _varga_lagna_sign(jd, place, factor)
    day = 1.0 / 1440.0  # one minute in jd

    def flip_offset(direction):
        lo, hi = 0.0, max_window_min
        if _varga_lagna_sign(jd + direction * hi * day, place, factor) == base:
            return max_window_min  # stable beyond the cap
        for _ in range(24):  # bisect to <0.001 min
            mid = (lo + hi) / 2.0
            if _varga_lagna_sign(jd + direction * mid * day, place, factor) == base:
                lo = mid
            else:
                hi = mid
        return lo

    minus = flip_offset(-1.0)
    plus = flip_offset(+1.0)
    window = min(minus, plus)
    if window >= max_window_min:
        verdict = "stable"
    elif window >= 5.0:
        verdict = "needs-minutes-accurate-time"
    elif window >= 1.0:
        verdict = "needs-minute-accurate-time"
    else:
        verdict = "needs-seconds-accurate-time"
    return {"factor": factor,
            "stable_minus_min": round(minus, 2),
            "stable_plus_min": round(plus, 2),
            "verdict": verdict,
            "beyond_traditional_ceiling": factor > TRADITIONAL_CEILING}


def sensitivity_profile(jd, place, factors=None):
    """Sensitivity across the offered varga series for one birth moment."""
    return [lagna_sensitivity(jd, place, f)
            for f in (factors or VARGA_FACTORS)]
