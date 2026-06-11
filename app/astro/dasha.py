#!/usr/bin/env python3
# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
"""Vimśottarī daśā to 5 levels (mahā → antar → pratyantar → sūkṣma → prāṇa).

Levels 1-3 from PyJhora's native functions; PyJhora implements nothing
deeper (its "sukshma-prana" docstring is aspirational), so levels 4-5
subdivide the parent JD span proportionally: duration = parent_span ×
lord_years / 120, sequence from the parent lord in adhipati order — the
classical proportional rule. Ported from the author's tested toolkit
(golden-gated against engine boundaries to the day)."""

import io
import sys

from . import context as C

_orig_stdout = sys.stdout
sys.stdout = io.StringIO()
try:
    from jhora import const as jconst
    from jhora.horoscope.dhasa.graha import vimsottari as vim
finally:
    sys.stdout = _orig_stdout

ADHIPATI = list(jconst.vimsottari_adhipati_list)
YEARS = dict(jconst.vimsottari_dict)
TOTAL_YEARS = float(vim.human_life_span_for_vimsottari_dhasa)
LEVEL_NAMES = ["maha", "antar", "pratyantar", "sukshma", "prana"]
LEVEL_IAST = ["mahā", "antar", "pratyantar", "sūkṣma", "prāṇa"]


def _iso(jd):
    y, m, d, _ = C.jutils.jd_to_gregorian(jd)
    return f"{y:04d}-{m:02d}-{d:02d}"


def _seq_from(lord):
    i = ADHIPATI.index(lord)
    return ADHIPATI[i:] + ADHIPATI[:i]


def _subdivide(parent_lord, start_jd, end_jd):
    span = end_jd - start_jd
    out, t = [], start_jd
    for lord in _seq_from(parent_lord):
        dur = span * YEARS[lord] / TOTAL_YEARS
        out.append((lord, t, t + dur))
        t += dur
    out[-1] = (out[-1][0], out[-1][1], end_jd)
    return out


def _native_l1(jd_birth, place):
    md = vim.vimsottari_mahadasa(jd_birth, place)
    lords, starts = list(md.keys()), list(md.values())
    return [(lord, starts[i],
             starts[i + 1] if i + 1 < len(lords)
             else starts[i] + YEARS[lord] * jconst.sidereal_year)
            for i, lord in enumerate(lords)]


def _native_l2(maha_lord, maha_start, maha_end):
    bd = vim._vimsottari_bhukti(maha_lord, maha_start)
    lords, starts = list(bd.keys()), list(bd.values())
    return [(lord, starts[i], starts[i + 1] if i + 1 < len(lords) else maha_end)
            for i, lord in enumerate(lords)]


def _native_l3(maha_lord, antar_lord, antar_start, antar_end):
    ad = vim._vimsottari_antara(maha_lord, antar_lord, antar_start)
    lords, starts = list(ad.keys()), list(ad.values())
    return [(lord, starts[i], starts[i + 1] if i + 1 < len(lords) else antar_end)
            for i, lord in enumerate(lords)]


def _containing(periods, at_jd):
    for lord, s, e in periods:
        if s <= at_jd < e:
            return lord, s, e
    return None


def stack_at(jd_birth, place, at_jd, depth=5):
    """Running daśā stack at a moment, levels 1..depth (max 5). Lazy
    descent: native L1-L3, proportional L4-L5."""
    if not 1 <= depth <= 5:
        raise ValueError("depth must be 1..5")
    stack = []
    hit = _containing(_native_l1(jd_birth, place), at_jd)
    if hit is None:
        return []
    stack.append(hit)
    if depth >= 2:
        hit = _containing(_native_l2(stack[0][0], stack[0][1], stack[0][2]), at_jd)
        if hit:
            stack.append(hit)
    if depth >= 3 and len(stack) == 2:
        hit = _containing(_native_l3(stack[0][0], stack[1][0],
                                     stack[1][1], stack[1][2]), at_jd)
        if hit:
            stack.append(hit)
    for lvl in (3, 4):
        if depth >= lvl + 1 and len(stack) == lvl:
            parent = stack[-1]
            hit = _containing(_subdivide(parent[0], parent[1], parent[2]), at_jd)
            if hit:
                stack.append(hit)
    return [{"level": i + 1, "level_name": LEVEL_NAMES[i],
             "level_iast": LEVEL_IAST[i],
             "lord": C.GRAHA_IAST[lord], "lord_index": int(lord),
             "start": _iso(s), "end": _iso(e)}
            for i, (lord, s, e) in enumerate(stack)]


def maha_periods(jd_birth, place):
    """The 9 mahādaśās with boundaries (for timeline display)."""
    return [{"lord": C.GRAHA_IAST[lord], "start": _iso(s), "end": _iso(e)}
            for lord, s, e in _native_l1(jd_birth, place)]
