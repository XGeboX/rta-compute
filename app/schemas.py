#!/usr/bin/env python3
# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
"""Request/response models. Birth data arrives per request and is never
persisted; responses carry the frame so every output is reproducible."""

from datetime import date, time
from typing import Annotated, Literal, Optional

from pydantic import AfterValidator, BaseModel, Field, model_validator

from .astro.vargas import VARGA_FACTORS, validate_factors

Ayanamsa = Literal["TRUE_PUSHYA", "LAHIRI", "RAMAN", "KP"]
Zodiac = Literal["sidereal", "tropical"]
HouseSystem = Literal["placidus", "whole-sign", "equal"]
VargaFactors = Annotated[list[int],
                         Field(min_length=1, max_length=len(VARGA_FACTORS)),
                         AfterValidator(validate_factors)]

# Swiss Ephemeris accuracy window this service relies on; an `asof` outside
# it is rejected rather than silently computed against degraded ephemeris.
ASOF_MIN = date(1800, 1, 1)
ASOF_MAX = date(2200, 12, 31)


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
    vargas: VargaFactors = Field(
        default=[1, 9],
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
    asof: Optional[date] = Field(default=None, ge=ASOF_MIN, le=ASOF_MAX)
    depth: int = Field(default=5, ge=1, le=5)

    @model_validator(mode="after")
    def _resolved_asof_in_window(self):
        # the route falls back to the birth date when asof is omitted, so the
        # window has to hold for that resolved value as well, or a pre-1800
        # birth slips past the bound the field above promises
        if self.asof is None and not ASOF_MIN <= self.birth.date <= ASOF_MAX:
            raise ValueError("asof defaults to the birth date, which is outside "
                             "the ephemeris window; pass asof explicitly")
        return self


class SensitivityRequest(BaseModel):
    birth: BirthInput
    ayanamsa: Ayanamsa = "TRUE_PUSHYA"
    factors: Optional[VargaFactors] = None


class InstantRequest(BaseModel):
    birth: BirthInput
    ayanamsa: Ayanamsa = "TRUE_PUSHYA"
    # defaults handled by caller-supplied date; no server clock in compute path
    asof: Optional[date] = Field(default=None, ge=ASOF_MIN, le=ASOF_MAX)


class RectifyEvent(BaseModel):
    date: date
    type: Literal["marriage", "relationship", "separation", "career",
                  "children", "siblings", "mother", "father", "education",
                  "injury", "relocation-abroad", "spiritual"]
    label: str = Field(default="", max_length=120)


class BoundaryScanRequest(BaseModel):
    birth: BirthInput
    ayanamsa: Ayanamsa = "TRUE_PUSHYA"
    before_min: float = Field(default=20, gt=0, le=120)
    after_min: float = Field(default=20, gt=0, le=120)


class RectifyRequest(BaseModel):
    birth: BirthInput
    ayanamsa: Ayanamsa = "TRUE_PUSHYA"
    before_min: float = Field(default=20, gt=0, le=120)
    after_min: float = Field(default=20, gt=0, le=120)
    step_min: float = Field(default=5, ge=0.5, le=15)
    events: list[RectifyEvent] = Field(min_length=1, max_length=40)
