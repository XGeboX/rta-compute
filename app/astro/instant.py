#!/usr/bin/env python3
# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
"""RTA Instant: the deterministic rule engine.

Computed, not generated. This module returns FACTS and FIRED RULES with
citations — pure JSON, byte-identical for identical input. It contains no
prose: editorial rendering happens client-side of the AGPL boundary. Every
rule carries its classical source so any output can be audited against
śāstra.

Rule registry v1 is deliberately small and honest: lagna and Moon
essentials, the running 5-level Vimśottarī stack, the classical gochara
gate verdicts, and a handful of high-signal observations. Weights order
the output; they are display priorities, not probabilities."""

from . import context as C
from . import dasha as D
from . import gochara as G

NAK_LORDS = [8, 5, 0, 1, 2, 7, 4, 6, 3] * 3  # Aśvinī.. cycle Ketu,Śukra,Sūrya..

CIT_GOCHARA = {"source": "Nakshatra, Tithi and Gochara Phala",
               "section": "Transit Effects from the Moon sign"}
CIT_AV = {"source": "Bṛhat Parāśara Horā Śāstra",
          "section": "Aṣṭakavarga adhyāyas (bindu transit weighting)"}
CIT_DASHA = {"source": "Bṛhat Parāśara Horā Śāstra",
             "section": "Vimśottarī daśā (Ch. 46 seq.)"}
CIT_TARA = {"source": "Muhūrta tradition (nava-tārā)",
            "section": "tārā-bala from janma nakṣatra"}


def _facts(natal):
    pos = natal["positions"]
    lag = pos["lagna"]
    moon = pos["Candra"]
    sun = pos["Sūrya"]
    lagna_lord = C.RASI_LORDS[lag["sign_index"]]
    return {
        "lagna": {"sign": C.RASI_IAST[lag["sign_index"]],
                  "sign_en": C.RASI_EN[lag["sign_index"]],
                  "degree": lag["degree"],
                  "nakshatra": lag.get("nakshatra"),
                  "pada": lag.get("pada"),
                  "lord": C.GRAHA_IAST[lagna_lord]},
        "moon": {"sign": C.RASI_IAST[moon["sign_index"]],
                 "degree": moon["degree"],
                 "nakshatra": moon.get("nakshatra"),
                 "pada": moon.get("pada"),
                 "nak_lord": C.GRAHA_IAST[NAK_LORDS[moon["nak_index"]]]},
        "sun": {"sign": C.RASI_IAST[sun["sign_index"]],
                "degree": sun["degree"],
                "nakshatra": sun.get("nakshatra")},
    }


def _rules_from_gates(card, stack):
    """Fire observation rules from the gate scorecard + daśā stack."""
    fired = []
    md_lord = stack[0]["lord"] if stack else None
    ad_lord = stack[1]["lord"] if len(stack) > 1 else None

    for g, row in card.items():
        ved = row["classical"]
        # R1: classically favorable seat, unobstructed
        if ved["effective"] is True:
            w = 70 + (10 if g in (md_lord, ad_lord) else 0)
            fired.append({
                "rule_id": "GOCHARA_SEAT_CLEAR",
                "weight": w,
                "citation": CIT_GOCHARA,
                "slots": {"graha": g, "house_from_moon": ved["house_from_moon"],
                          "is_dasha_lord": g in (md_lord, ad_lord)},
            })
        # R2: favorable seat BLOCKED by vedha
        if ved["effective"] is False:
            fired.append({
                "rule_id": "GOCHARA_VEDHA_BLOCK",
                "weight": 75,
                "citation": CIT_GOCHARA,
                "slots": {"graha": g, "house_from_moon": ved["house_from_moon"],
                          "vedha_house": ved["vedha_house"],
                          "blocked_by": ved["vedha_by"]},
            })
        # R3: strong bindu carriage (sign + kakṣyā both carrying)
        if row["bindus"] is not None and row["bindus"] >= 5 \
                and row["kakshya"]["bindu"] == 1:
            fired.append({
                "rule_id": "AV_STRONG_CARRIAGE",
                "weight": 60 + (15 if g in (md_lord, ad_lord) else 0),
                "citation": CIT_AV,
                "slots": {"graha": g, "bindus": row["bindus"],
                          "kakshya_lord": row["kakshya"]["lord"]},
            })
        # R4: bindu-poor transit (sign-level weakness regardless of dignity)
        if row["bindus"] is not None and row["bindus"] <= 2:
            fired.append({
                "rule_id": "AV_POOR_CARRIAGE",
                "weight": 55 + (15 if g in (md_lord, ad_lord) else 0),
                "citation": CIT_AV,
                "slots": {"graha": g, "bindus": row["bindus"],
                          "sign": row["sign"]},
            })
        # R5: daśā-lord tārā
        if g in (md_lord, ad_lord) and row["tara"]["favorability"] != "mixed":
            fired.append({
                "rule_id": "DASHA_LORD_TARA",
                "weight": 50,
                "citation": CIT_TARA,
                "slots": {"graha": g, "tara": row["tara"]["tara"],
                          "favorability": row["tara"]["favorability"],
                          "role": "mahā" if g == md_lord else "antar"},
            })
    return fired


def instant(birth_jd, birth_place, asof_jd, asof_place):
    """The Instant bundle: facts + daśā stack + gates + fired rules.

    Deterministic: identical inputs yield identical output. The caller pins
    the frame (sidereal; ayanāṁśa per request)."""
    natal = C.natal_bundle(birth_jd, birth_place)
    stack = D.stack_at(birth_jd, birth_place, asof_jd, depth=5)
    transits = C.positions_at(asof_jd, asof_place, zodiac="sidereal")
    card = G.scorecard(natal, transits)
    fired = _rules_from_gates(card, stack)
    fired.sort(key=lambda r: (-r["weight"], r["rule_id"],
                              str(sorted(r["slots"].items()))))
    return {
        "doctrine": "computed-not-generated",
        "facts": _facts(natal),
        "dasha_stack": stack,
        "gates": {g: {"carried": row["gates_carried"],
                      "total": row["gates_total"],
                      "house_from_moon": row["house_from_moon"],
                      "vedha_blocked": row["classical"]["effective"] is False,
                      "tara": row["tara"]["tara"]}
                  for g, row in card.items()},
        "fired_rules": fired[:8],
        "citations_complete": all(r.get("citation") for r in fired),
    }
