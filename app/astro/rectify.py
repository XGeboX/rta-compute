#!/usr/bin/env python3
# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
"""Birth-time rectification: the computational half.

Method lineage: PVR Narasimha Rao's multi-varga rectification technique as
practiced in the founder's own rectification (candidate sweep, varga-lagna
boundary mapping, dated life events tested against Vimśottarī periods,
divisional sensitivity cascade D1 → D9 → D3 → D10 → D12 → D24, fine sweep
through D60/D24/D20).

This module returns FACTS plus one deliberately narrow, fully cited score:
the naisargika-kāraka match between each event's daśā lords and the
classical significators of its event type. The full rectification verdict
is a human judgment built on these facts; the score is a lens, not an
oracle, and every output says so.
"""

import io
import sys

from . import context as C
from . import dasha as D

_orig_stdout = sys.stdout
sys.stdout = io.StringIO()
try:
    from jhora.horoscope.chart import charts
finally:
    sys.stdout = _orig_stdout

# PVR sensitivity cascade order (coarse -> fine).
CASCADE = [1, 9, 3, 10, 12, 24]
FINE = [60, 24, 20]

# Naisargika kāraka significators per event type [BPHS kāraka adhyāya;
# Phaladīpikā 16 for bhāva-kārakas]. The kāraka lens only: bhāva-lord
# analysis is candidate-dependent judgment and stays with the human tier.
EVENT_KARAKAS = {
    "marriage": ["Śukra"],
    "relationship": ["Śukra"],
    "separation": ["Śani", "Rāhu"],
    "career": ["Sūrya", "Śani", "Budha"],
    "children": ["Guru"],
    "siblings": ["Maṅgala"],
    "mother": ["Candra"],
    "father": ["Sūrya"],
    "education": ["Budha", "Guru"],
    "injury": ["Maṅgala", "Śani"],
    "relocation-abroad": ["Rāhu"],
    "spiritual": ["Ketu", "Guru"],
}
CIT_KARAKA = {"source": "Bṛhat Parāśara Horā Śāstra",
              "section": "naisargika kārakas (kāraka adhyāya)"}


def _varga_lagna(jd, place, factor):
    raw = charts.divisional_chart(jd, place, divisional_chart_factor=factor)
    return int(raw[0][1][0])


# A public endpoint must bound its own work: scan sampling calls.
MAX_SCAN_CALLS = 4000


def _scan_call_estimate(before_min, after_min, factors):
    window = float(before_min) + float(after_min)
    return sum(int(window / max(0.02, (120.0 / f) / 12.0)) + 1
               for f in factors)


def boundaries_in_window(jd_center, place, factor, before_min, after_min):
    """Every varga-lagna sign flip inside [t-before, t+after], bisected to
    about one second. The free boundary-scan teaser runs on this."""
    day = 1.0 / 1440.0
    # The D-N lagna flips on average every 120/N minutes, but ascendant
    # speed varies strongly with latitude and rising sign (short-ascension
    # signs at high latitudes rise several times faster than the mean), so
    # sample with a generous safety factor; and after each found flip,
    # resume the scan FROM the flip moment so multiple flips inside one
    # original step interval are never skipped.
    step = max(0.02, (120.0 / factor) / 12.0)
    flips = []
    t = -float(before_min)
    end = float(after_min)
    prev_sign = _varga_lagna(jd_center + t * day, place, factor)
    while t < end:
        t_next = min(t + step, end)
        sign = _varga_lagna(jd_center + t_next * day, place, factor)
        if sign != prev_sign:
            lo, hi = t, t_next
            for _ in range(24):
                mid = (lo + hi) / 2.0
                if _varga_lagna(jd_center + mid * day, place, factor) == prev_sign:
                    lo = mid
                else:
                    hi = mid
            flip_sign = _varga_lagna(jd_center + hi * day, place, factor)
            flips.append({
                "factor": factor,
                "offset_min": round(hi, 3),
                "from_sign": C.RASI_IAST[prev_sign],
                "to_sign": C.RASI_IAST[flip_sign],
            })
            # resume just past the flip; the remainder of this step may
            # hold another boundary.
            t = hi
            prev_sign = flip_sign
            continue
        prev_sign = sign
        t = t_next
    return flips


def boundary_scan(jd_center, place, before_min, after_min,
                  factors=None):
    """The teaser: how decisive is this uncertainty window?"""
    factors = factors or CASCADE
    est = _scan_call_estimate(before_min, after_min, factors)
    if est > MAX_SCAN_CALLS:
        raise ValueError(
            f"boundary scan too large: ~{est} lagna samples exceeds the "
            f"{MAX_SCAN_CALLS} cap; narrow the window or the factor list")
    table = []
    for f in factors:
        table.extend(boundaries_in_window(jd_center, place, f,
                                          before_min, after_min))
    table.sort(key=lambda b: b["offset_min"])
    live = sorted({b["factor"] for b in table})
    return {
        "window_min": {"before": before_min, "after": after_min},
        "boundaries": table,
        "live_discriminators": live,
        "verdict": ("decisive window: rectification can resolve real "
                    "chart differences" if table else
                    "no varga boundaries inside this window: the stated "
                    "time is already varga-stable at these factors"),
    }


class _CandidateDasha:
    """One candidate birth time's daśā tree, computed once and queried for
    every event: the native L1 list is built a single time and L2 bhukti
    lists are memoized per mahā lord, so an N-event request costs one L1
    computation plus at most a handful of L2 expansions per candidate
    (instead of N full stack recomputations under the frame lock)."""

    def __init__(self, jd_birth, place):
        self._l1 = D._native_l1(jd_birth, place)
        self._l2_cache = {}

    def lords_at(self, event_jd):
        for lord, s, e in self._l1:
            if s <= event_jd < e:
                if lord not in self._l2_cache:
                    self._l2_cache[lord] = D._native_l2(lord, s, e)
                for alord, as_, ae in self._l2_cache[lord]:
                    if as_ <= event_jd < ae:
                        return C.GRAHA_IAST[lord], C.GRAHA_IAST[alord]
                return C.GRAHA_IAST[lord], None
        return None, None


# A public endpoint must bound its own work: candidates × events.
MAX_SWEEP_WORK = 2000


def rectify_sweep(jd_center, place, before_min, after_min, events,
                  step_min=5.0, factors=None):
    """The Tier-1 computational sweep.

    events: [{"date": (y,m,d), "type": <EVENT_KARAKAS key>, "label": str}]
    Returns per-candidate: varga lagnas across the cascade, per-event daśā
    lords, and the kāraka-lens score with citations. Plus the boundary
    table. Deterministic; no verdict."""
    factors = factors or CASCADE
    n_candidates = int((before_min + after_min) / step_min) + 1
    if n_candidates * max(1, len(events)) > MAX_SWEEP_WORK:
        raise ValueError(
            f"sweep too large: {n_candidates} candidates x {len(events)} "
            f"events exceeds the {MAX_SWEEP_WORK} work cap; widen step_min "
            f"or narrow the window")
    for ev in events:
        if ev["type"] not in EVENT_KARAKAS:
            raise ValueError(f"unknown event type: {ev['type']!r}")
    day = 1.0 / 1440.0
    candidates = []
    t = -float(before_min)
    while t <= float(after_min) + 1e-9:
        cjd = jd_center + t * day
        lagnas = {f: C.RASI_IAST[_varga_lagna(cjd, place, f)] for f in factors}
        tree = _CandidateDasha(cjd, place)
        per_event = []
        score = 0
        for ev in events:
            ejd = C.jd_at(tuple(ev["date"]), (12, 0, 0))
            md, ad = tree.lords_at(ejd)
            karakas = EVENT_KARAKAS[ev["type"]]
            md_hit = md in karakas
            ad_hit = ad in karakas
            score += (2 if md_hit else 0) + (1 if ad_hit else 0)
            per_event.append({
                "label": ev.get("label", ev["type"]),
                "type": ev["type"],
                "maha": md, "antar": ad,
                "karaka_match": {"maha": md_hit, "antar": ad_hit,
                                 "karakas": karakas,
                                 "citation": CIT_KARAKA},
            })
        candidates.append({
            "offset_min": round(t, 2),
            "varga_lagnas": lagnas,
            "events": per_event,
            "karaka_score": score,
        })
        t += step_min
    scan = boundary_scan(jd_center, place, before_min, after_min, factors)
    return {
        "doctrine": ("computed-not-generated; the kāraka score is one "
                     "classical lens, not a verdict - final rectification "
                     "is a human judgment over these facts"),
        "method": "PVR multi-varga rectification (sweep + boundary map + "
                  "daśā-at-event, cascade D1-D9-D3-D10-D12-D24)",
        "candidates": candidates,
        "boundary_scan": scan,
        "fine_factors_available": FINE,
    }
