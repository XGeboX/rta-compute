#!/usr/bin/env python3
# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
"""API routes. Sync handlers (FastAPI threadpool) — the frame lock in
astro.context serializes PyJhora's global state; run multiple uvicorn
worker processes for parallelism. No request bodies are logged; no birth
data is persisted."""

from datetime import date as _date

from fastapi import APIRouter, HTTPException

from .. import schemas as S
from ..version import engine_version
from ..astro import context as C
from ..astro import dasha as D
from ..astro import gochara as G
from ..astro import instant as I
from ..astro import panchanga as P
from ..astro import rectify as R
from ..astro import vargas as V
from ..atlas import search as atlas_search

router = APIRouter()


def _jd_place(birth: S.BirthInput):
    jd = C.jd_at((birth.date.year, birth.date.month, birth.date.day),
                 (birth.time.hour, birth.time.minute, birth.time.second))
    place = C.place_of(birth.place_name or "-", birth.lat, birth.lon,
                       birth.tz_hours)
    return jd, place


@router.get("/healthz")
def healthz():
    return {"ok": True, "engine": "rta-compute", "version": engine_version()}


@router.post("/chart")
def chart(req: S.ChartRequest):
    jd, place = _jd_place(req.birth)
    bad = [f for f in req.options.vargas if f not in V.VARGA_FACTORS]
    if bad:
        raise HTTPException(422, f"unsupported varga factors: {bad}")
    with C.frame(req.options.ayanamsa):
        ay = C.ayanamsa_value(jd)
        if req.options.zodiac == "tropical":
            positions = C.positions_at(jd, place, zodiac="tropical")
            houses = None
            if req.options.house_system == "placidus":
                houses = C.tropical_houses(jd, place, hsys=b"P")
            elif req.options.house_system == "equal":
                houses = C.tropical_houses(jd, place, hsys=b"E")
            return {"frame": {"zodiac": "tropical", "ayanamsa": None,
                              "ayanamsa_value_subtracted": round(ay, 6)},
                    "positions": positions, "houses": houses,
                    "vargas": None,
                    "note": "tropical = sidereal + ayanāṁśa(jd); vargas and "
                            "nakṣatras are sidereal constructs and are not "
                            "served in this frame"}
        positions = C.positions_at(jd, place, zodiac="sidereal")
        vargas = V.all_vargas(jd, place, factors=req.options.vargas)
        return {"frame": {"zodiac": "sidereal",
                          "ayanamsa": req.options.ayanamsa,
                          "ayanamsa_value": round(ay, 6)},
                "positions": positions, "vargas": vargas}


@router.post("/panchanga")
def panchanga(req: S.PanchangaRequest):
    jd, place = _jd_place(req.birth)
    with C.frame(req.ayanamsa):
        return {"frame": {"ayanamsa": req.ayanamsa},
                "panchanga": P.panchanga_at(jd, place)}


@router.post("/dasha")
def dasha(req: S.DashaRequest):
    jd, place = _jd_place(req.birth)
    asof = req.asof or req.birth.date
    asof_jd = C.jd_at((asof.year, asof.month, asof.day), (12, 0, 0))
    with C.frame(req.ayanamsa):
        return {"frame": {"ayanamsa": req.ayanamsa},
                "maha_periods": D.maha_periods(jd, place),
                "stack_asof": str(asof),
                "stack": D.stack_at(jd, place, asof_jd, depth=req.depth)}


@router.post("/sensitivity")
def sensitivity(req: S.SensitivityRequest):
    jd, place = _jd_place(req.birth)
    factors = req.factors or V.VARGA_FACTORS
    bad = [f for f in factors if f not in V.VARGA_FACTORS]
    if bad:
        raise HTTPException(422, f"unsupported varga factors: {bad}")
    with C.frame(req.ayanamsa):
        return {"frame": {"ayanamsa": req.ayanamsa},
                "doctrine": "depth offered, honesty enforced",
                "profile": V.sensitivity_profile(jd, place, factors=factors)}


@router.post("/instant")
def instant(req: S.InstantRequest):
    jd, place = _jd_place(req.birth)
    asof = req.asof or _date.today()
    asof_jd = C.jd_at((asof.year, asof.month, asof.day), (6, 0, 0))
    with C.frame(req.ayanamsa):
        bundle = I.instant(jd, place, asof_jd, place)
        bundle["asof"] = str(asof)
        bundle["frame"] = {"ayanamsa": req.ayanamsa}
        # Every Instant reading names the engine that produced it: any
        # client can verify which image digest computed their result.
        bundle["engine"] = engine_version()
        return bundle


@router.post("/rectify/boundaries")
def rectify_boundaries(req: S.BoundaryScanRequest):
    """The free boundary scan: how decisive is the stated uncertainty
    window? No events required; nothing persisted."""
    jd, place = _jd_place(req.birth)
    try:
        with C.frame(req.ayanamsa):
            return {"frame": {"ayanamsa": req.ayanamsa},
                    **R.boundary_scan(jd, place, req.before_min,
                                      req.after_min)}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/rectify")
def rectify(req: S.RectifyRequest):
    """Tier-1 computational rectification sweep: candidates, boundary map,
    daśā-at-event lords, kāraka-lens score. Verdict stays human."""
    jd, place = _jd_place(req.birth)
    events = [{"date": (e.date.year, e.date.month, e.date.day),
               "type": e.type, "label": e.label} for e in req.events]
    try:
        with C.frame(req.ayanamsa):
            return {"frame": {"ayanamsa": req.ayanamsa},
                    **R.rectify_sweep(jd, place, req.before_min,
                                      req.after_min, events,
                                      step_min=req.step_min)}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/atlas")
def atlas(q: str, limit: int = 8):
    if not q or len(q) < 2:
        raise HTTPException(422, "query too short")
    return {"results": atlas_search.search(q, limit=min(limit, 20))}
