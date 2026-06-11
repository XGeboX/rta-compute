#!/usr/bin/env python3
# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
"""Request/response models. Birth data arrives per request and is never
persisted; responses carry the frame so every output is reproducible."""

from datetime import date, time
from typing import Literal, Optional

from pydantic import BaseModel, Field

Ayanamsa = Literal["TRUE_PUSHYA", "LAHIRI", "RAMAN", "KP"]
Zodiac = Literal["sidereal", "tropical"]
HouseSystem = Literal["placidus", "whole-sign", "equal"]


class BirthInput(BaseModel):
    date: date
    time: time
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    tz_hours: float = Field(ge=-14, le=14,
                            description="UTC offset in hours at the birth moment")
    place_name: str = Field(default="", max_length=120)


class ChartOptions(BaseModel):
    zodiac: Zodiac = "sidereal"
    ayanamsa: Ayanamsa = "TRUE_PUSHYA"
    house_system: HouseSystem = "whole-sign"  # tropical wheel honors this
    vargas: list[int] = Field(default=[1, 9],
                              description="divisional factors, subset of the offered series")


class ChartRequest(BaseModel):
    birth: BirthInput
    options: ChartOptions = ChartOptions()


class PanchangaRequest(BaseModel):
    birth: BirthInput  # the moment + place (any moment, not only births)
    ayanamsa: Ayanamsa = "TRUE_PUSHYA"


class DashaRequest(BaseModel):
    birth: BirthInput
    ayanamsa: Ayanamsa = "TRUE_PUSHYA"
    asof: Optional[date] = None
    depth: int = Field(default=5, ge=1, le=5)


class SensitivityRequest(BaseModel):
    birth: BirthInput
    ayanamsa: Ayanamsa = "TRUE_PUSHYA"
    factors: Optional[list[int]] = None


class InstantRequest(BaseModel):
    birth: BirthInput
    ayanamsa: Ayanamsa = "TRUE_PUSHYA"
    asof: Optional[date] = None  # defaults handled by caller-supplied date; no server clock in compute path


class FrameEcho(BaseModel):
    zodiac: Zodiac
    ayanamsa: Optional[Ayanamsa]
    ayanamsa_value: Optional[float]
    engine: str = "rta-compute (PyJhora 4.6.0 / Swiss Ephemeris)"
