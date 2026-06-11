#!/usr/bin/env python3
# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
"""Classical gochara (transit) gates: aṣṭakavarga bindu-weighting, kakṣyā,
vedha, tārā-bala. Ported from the author's tested toolkit.

Source discipline:
  - Vedha tables + favorable houses + exemptions: "Nakshatra, Tithi and
    Gochara Phala", Transit Effects chapters (Rāhu/Ketu share Śani's table
    per the text).
  - Bindu-weighting of transits: same text + BPHS aṣṭakavarga adhyāyas.
  - Kakṣyā lord order: standard aṣṭakavarga tradition (tagged `tradition`).
  - Tārā favorability: universal muhūrta doctrine (tagged `tradition`).
All houses are whole-sign counts from the NATAL Moon sign (gochara
convention) unless stated otherwise."""

from . import context as C

KAKSHYA_SPAN = 3.75
KAKSHYA_LORDS = ["Śani", "Guru", "Maṅgala", "Sūrya", "Śukra", "Budha",
                 "Candra", "Lagna"]
# contributor index in prastara rows: 0=Sun..6=Saturn, 7=Lagna
_KAKSHYA_CONTRIB = [6, 4, 2, 0, 5, 3, 1, 7]

VEDHA = {
    "Sūrya":   {3: 9, 6: 12, 10: 4, 11: 5},
    "Candra":  {1: 5, 3: 9, 6: 12, 7: 2, 10: 4, 11: 8},
    "Maṅgala": {3: 12, 6: 9, 11: 5},
    "Budha":   {2: 5, 4: 3, 6: 9, 8: 1, 10: 8, 11: 12},
    "Guru":    {2: 12, 5: 4, 7: 3, 9: 10, 11: 8},
    "Śukra":   {1: 8, 2: 7, 3: 1, 4: 10, 5: 9, 8: 5, 9: 11, 11: 3, 12: 6},
    "Śani":    {3: 12, 6: 9, 11: 5},
    "Rāhu":    {3: 12, 6: 9, 11: 5},
    "Ketu":    {3: 12, 6: 9, 11: 5},
}
VEDHA_EXEMPT = {("Sūrya", "Śani"), ("Candra", "Budha")}

TARA_NAMES = ["Janma", "Sampat", "Vipat", "Kṣema", "Pratyak", "Sādhana",
              "Naidhana", "Mitra", "Parama-mitra"]
TARA_FAVOR = {1: "mixed", 2: "favorable", 3: "unfavorable", 4: "favorable",
              5: "unfavorable", 6: "favorable", 7: "unfavorable",
              8: "favorable", 9: "favorable"}


def house_from(sign_index, ref_sign_index):
    return ((sign_index - ref_sign_index) % 12) + 1


def kakshya_of(degree_in_sign):
    idx = min(int(degree_in_sign // KAKSHYA_SPAN), 7)
    return idx, KAKSHYA_LORDS[idx]


def _bindus(natal, graha_index, sign_index):
    return natal["bav"][graha_index][sign_index]


def _kakshya_bindu(natal, graha_index, sign_index, degree):
    kidx, _ = kakshya_of(degree)
    contrib = _KAKSHYA_CONTRIB[kidx]
    return natal["prastara"][graha_index][contrib][sign_index]


def vedha_status(natal, transit_positions, graha):
    moon_sign = natal["moon_sign_index"]
    house = house_from(transit_positions[graha]["sign_index"], moon_sign)
    table = VEDHA[graha]
    if house not in table:
        return {"house_from_moon": house, "classically_favorable": False,
                "vedha_house": None, "vedha_by": [], "effective": None}
    vhouse = table[house]
    occupants = [
        g for g in C.GRAHA_IAST
        if g != graha
        and house_from(transit_positions[g]["sign_index"], moon_sign) == vhouse
        and (graha, g) not in VEDHA_EXEMPT
    ]
    return {"house_from_moon": house, "classically_favorable": True,
            "vedha_house": vhouse, "vedha_by": occupants,
            "effective": not occupants}


def tara_of(natal, nak_index):
    rank = C.tara_rank(natal["janma_nak_index"], nak_index)
    return {"rank": rank, "tara": TARA_NAMES[rank - 1],
            "favorability": TARA_FAVOR[rank]}


def scorecard(natal, transit_positions):
    """Per-graha classical gate scorecard. All raw values exposed; no
    hidden weighting. Nodes carry no BAV of their own (classical)."""
    out = {}
    moon_sign = natal["moon_sign_index"]
    lagna_sign = natal["lagna_sign_index"]
    for gi, g in enumerate(C.GRAHA_IAST):
        p = transit_positions[g]
        si, deg = p["sign_index"], p["degree"]
        has_av = gi <= 6
        b = _bindus(natal, gi, si) if has_av else None
        kx, klord = kakshya_of(deg)
        kb = _kakshya_bindu(natal, gi, si, deg) if has_av else None
        ved = vedha_status(natal, transit_positions, g)
        ni = int(p["longitude"] // (360.0 / 27.0)) % 27
        tara = tara_of(natal, ni)
        gates, carried = 0, 0
        if b is not None:
            gates += 1
            carried += 1 if b >= 4 else 0
        if kb is not None:
            gates += 1
            carried += kb
        if ved["effective"] is not None:
            gates += 1
            carried += 1 if ved["effective"] else 0
        gates += 1
        carried += 1 if tara["favorability"] == "favorable" else 0
        out[g] = {
            "sign_index": si, "sign": C.RASI_IAST[si],
            "degree": round(deg, 3), "retrograde": p.get("retrograde", False),
            "house_from_moon": house_from(si, moon_sign),
            "house_from_lagna": house_from(si, lagna_sign),
            "bindus": b,
            "kakshya": {"index": kx, "lord": klord, "bindu": kb},
            "classical": ved,
            "tara": tara,
            "gates_carried": carried, "gates_total": gates,
        }
    return out
