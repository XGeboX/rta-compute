#!/usr/bin/env python3
# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
"""Pañcāṅga at a moment: tithi, nakṣatra, yoga, karaṇa, vāra, with sunrise
and sunset. Computed via PyJhora's drik layer in the pinned frame."""

import datetime
import io
import sys

from . import context as C

_orig_stdout = sys.stdout
sys.stdout = io.StringIO()
try:
    from jhora import utils as jutils
    from jhora.panchanga import drik
finally:
    sys.stdout = _orig_stdout

TITHI_IAST = ["Pratipadā", "Dvitīyā", "Tṛtīyā", "Caturthī", "Pañcamī",
              "Ṣaṣṭhī", "Saptamī", "Aṣṭamī", "Navamī", "Daśamī", "Ekādaśī",
              "Dvādaśī", "Trayodaśī", "Caturdaśī", "Pūrṇimā",
              "Pratipadā", "Dvitīyā", "Tṛtīyā", "Caturthī", "Pañcamī",
              "Ṣaṣṭhī", "Saptamī", "Aṣṭamī", "Navamī", "Daśamī", "Ekādaśī",
              "Dvādaśī", "Trayodaśī", "Caturdaśī", "Amāvāsyā"]
YOGA_IAST = ["Viṣkambha", "Prīti", "Āyuṣmān", "Saubhāgya", "Śobhana",
             "Atigaṇḍa", "Sukarma", "Dhṛti", "Śūla", "Gaṇḍa", "Vṛddhi",
             "Dhruva", "Vyāghāta", "Harṣaṇa", "Vajra", "Siddhi", "Vyatīpāta",
             "Varīyān", "Parigha", "Śiva", "Siddha", "Sādhya", "Śubha",
             "Śukla", "Brahma", "Indra", "Vaidhṛti"]
KARANA_MOVABLE = ["Bava", "Bālava", "Kaulava", "Taitila", "Gara", "Vaṇija",
                  "Viṣṭi"]
KARANA_FIXED = {1: "Kiṃstughna", 58: "Śakuni", 59: "Catuṣpāda", 60: "Nāga"}


def karana_name(k_no):
    """Karaṇa #1..60: Kiṃstughna first, 7 movables cycling 2..57, three
    fixed at the close. Verified: #36 == Viṣṭi."""
    if k_no in KARANA_FIXED:
        return KARANA_FIXED[k_no]
    return KARANA_MOVABLE[(k_no - 2) % 7]
VARA_IAST = ["Ravivāra", "Somavāra", "Maṅgalavāra", "Budhavāra",
             "Guruvāra", "Śukravāra", "Śanivāra"]


def _first_int(x):
    if isinstance(x, (list, tuple)):
        return int(x[0])
    return int(x)


def vaara_at(jd, place):
    """Sunrise-anchored vāra, Sunday==1 .. Saturday==7 -- the classical vāra
    runs sunrise to sunrise, so before local sunrise the previous day's vāra
    persists (matches the Dṛṣṭi reference engine).

    drik.vaara(jd) is deliberately NOT used: it is 0-based (Sunday==0) and,
    taking no place, flips at the JD integer boundary -- local noon in this
    codebase's wall-clock JD frame. The two defects cancelled in evening spot
    checks (0-based value + post-noon shift looked 1-based) while every
    pre-noon query silently reported the previous vāra."""
    y, m, d, _fh = jutils.jd_to_gregorian(jd)
    v = (datetime.date(y, m, d).weekday() + 1) % 7 + 1   # Mon=0..Sun=6 -> Sun=1..Sat=7
    if jd < drik.sunrise(jd, place)[2]:                  # [2] == sunrise jd, same frame
        v = (v - 2) % 7 + 1
    return v


def panchanga_at(jd, place):
    """The five limbs + sun events at jd/place (frame pinned by caller)."""
    t = drik.tithi(jd, place)
    n = drik.nakshatra(jd, place)
    y = drik.yogam(jd, place)
    k = drik.karana(jd, place)
    v = vaara_at(jd, place)

    t_no = _first_int(t)
    n_no = _first_int(n)
    y_no = _first_int(y)
    k_no = _first_int(k)
    v_no = _first_int(v)

    nak_index = (n_no - 1) % 27
    # drik.nakshatra returns [nak_no, pada, ...] (verified empirically:
    # 2026-06-03 -> [20, 3, ...] == Pūrvāṣāḍhā pada 3)
    pada = None
    if isinstance(n, (list, tuple)) and len(n) >= 2 and isinstance(n[1], (int, float)):
        maybe_pada = int(n[1])
        if 1 <= maybe_pada <= 4:
            pada = maybe_pada

    sunrise = drik.sunrise(jd, place)[1]
    sunset = drik.sunset(jd, place)[1]

    return {
        "tithi": {"number": t_no,
                  "name": TITHI_IAST[(t_no - 1) % 30],
                  "paksha": "Śukla" if t_no <= 15 else "Kṛṣṇa"},
        "nakshatra": {"number": n_no, "name": C.NAK_IAST[nak_index],
                      "pada": pada},
        "yoga": {"number": y_no, "name": YOGA_IAST[(y_no - 1) % 27]},
        "karana": {"number": k_no, "name": karana_name(k_no)},
        # vaara_at: sunrise-anchored, Sunday==1 (gates in tests/test_vara.py)
        "vara": {"number": v_no, "name": VARA_IAST[(v_no - 1) % 7]},
        "sunrise": str(sunrise),
        "sunset": str(sunset),
    }
