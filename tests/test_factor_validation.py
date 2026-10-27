#!/usr/bin/env python3
# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
"""Factor lists must be bounded before taking the shared frame lock."""

from contextlib import nullcontext
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.astro import context as C
from app.astro import vargas as V
from app.main import app

client = TestClient(app)

_BIRTH = {"date": "2025-02-28", "time": "17:55:55",
          "lat": 53.7938, "lon": -1.7564, "tz_hours": 0.0,
          "place_name": "Bradford"}

_BAD_FACTORS = [[], [0], [1, -1], [1, 13], [1, 145], [1, 1],
                V.VARGA_FACTORS + [1], [1] * 10000]
_BAD_IDS = ["empty", "zero", "negative", "gap", "above-series",
            "duplicate", "over-limit", "ten-thousand"]


@pytest.fixture
def computation_calls(monkeypatch):
    calls = {"jd_place": Mock(return_value=(0.0, None)),
             "frame": Mock(side_effect=lambda *_: nullcontext()),
             "ayanamsa": Mock(return_value=0.0),
             "positions": Mock(return_value={}),
             "houses": Mock(return_value={}),
             "varga": Mock(side_effect=lambda jd, place, f: {"factor": f}),
             "sensitivity": Mock(side_effect=lambda jd, place, f: {"factor": f})}
    monkeypatch.setattr(routes, "_jd_place", calls["jd_place"])
    monkeypatch.setattr(C, "frame", calls["frame"])
    monkeypatch.setattr(C, "ayanamsa_value", calls["ayanamsa"])
    monkeypatch.setattr(C, "positions_at", calls["positions"])
    monkeypatch.setattr(C, "tropical_houses", calls["houses"])
    monkeypatch.setattr(V, "varga_chart", calls["varga"])
    monkeypatch.setattr(V, "lagna_sensitivity", calls["sensitivity"])
    return calls


def _factor_request(path, factors):
    if path == "/v1/chart":
        return {"birth": _BIRTH, "options": {"vargas": factors}}
    return {"birth": _BIRTH, "factors": factors}


@pytest.mark.parametrize("path", ["/v1/chart", "/v1/sensitivity"])
@pytest.mark.parametrize("factors", [[1, 1], [1] * 10000],
                         ids=["duplicate", "ten-thousand"])
def test_repeated_factor_lists_are_rejected_before_computation(
        path, factors, computation_calls):
    response = client.post(path, json=_factor_request(path, factors))
    assert response.status_code == 422
    assert all(call.call_count == 0 for call in computation_calls.values())


@pytest.mark.parametrize("path", ["/v1/chart", "/v1/sensitivity"])
@pytest.mark.parametrize("factors", _BAD_FACTORS, ids=_BAD_IDS)
def test_invalid_factor_lists_are_rejected_by_request_validation(
        path, factors, computation_calls):
    response = client.post(path, json=_factor_request(path, factors))
    assert response.status_code == 422
    location = (["body", "options", "vargas"] if path == "/v1/chart"
                else ["body", "factors"])
    assert response.json()["detail"][0]["loc"] == location
    assert all(call.call_count == 0 for call in computation_calls.values())


@pytest.mark.parametrize("factors", _BAD_FACTORS, ids=_BAD_IDS)
def test_tropical_chart_rejects_invalid_factor_lists(factors, computation_calls):
    body = _factor_request("/v1/chart", factors)
    body["options"]["zodiac"] = "tropical"
    response = client.post("/v1/chart", json=body)
    assert response.status_code == 422
    assert all(call.call_count == 0 for call in computation_calls.values())


@pytest.mark.parametrize("helper", [V.all_vargas, V.sensitivity_profile])
@pytest.mark.parametrize("factors", _BAD_FACTORS, ids=_BAD_IDS)
def test_helpers_reject_invalid_factor_lists_before_computation(
        helper, factors, computation_calls):
    with pytest.raises(ValueError):
        helper(0.0, None, factors=factors)
    assert all(call.call_count == 0 for call in computation_calls.values())


@pytest.mark.parametrize("path", ["/v1/chart", "/v1/sensitivity"])
@pytest.mark.parametrize("factors", [[1]] + [[1, f] for f in V.VARGA_FACTORS
                                           if f != 1])
def test_platform_factor_lists_remain_valid(path, factors, computation_calls):
    """The platform sends D1 alone or D1 plus another supported factor."""
    response = client.post(path, json=_factor_request(path, factors))
    assert response.status_code == 200, response.text
    key = "vargas" if path == "/v1/chart" else "profile"
    assert [item["factor"] for item in response.json()[key]] == factors
    computation = "varga" if path == "/v1/chart" else "sensitivity"
    assert computation_calls[computation].call_count == len(factors)


@pytest.mark.parametrize("path, extra, expected", [
    ("/v1/chart", {}, [1, 9]),
    ("/v1/chart", {"options": {}}, [1, 9]),
    ("/v1/sensitivity", {}, V.VARGA_FACTORS),
    ("/v1/sensitivity", {"factors": None}, V.VARGA_FACTORS),
])
def test_factor_list_defaults_are_preserved(
        path, extra, expected, computation_calls):
    response = client.post(path, json={"birth": _BIRTH, **extra})
    assert response.status_code == 200, response.text
    key = "vargas" if path == "/v1/chart" else "profile"
    assert [item["factor"] for item in response.json()[key]] == expected
    computation = "varga" if path == "/v1/chart" else "sensitivity"
    assert computation_calls[computation].call_count == len(expected)


@pytest.mark.parametrize("path", ["/v1/chart", "/v1/sensitivity"])
def test_full_factor_series_is_valid_and_keeps_order(path, computation_calls):
    factors = list(reversed(V.VARGA_FACTORS))
    response = client.post(path, json=_factor_request(path, factors))
    assert response.status_code == 200, response.text
    key = "vargas" if path == "/v1/chart" else "profile"
    assert [item["factor"] for item in response.json()[key]] == factors
    computation = "varga" if path == "/v1/chart" else "sensitivity"
    assert computation_calls[computation].call_count == len(V.VARGA_FACTORS)


@pytest.mark.parametrize("helper", [V.all_vargas, V.sensitivity_profile])
def test_helpers_keep_default_series(helper, computation_calls):
    omitted = helper(0.0, None)
    explicit_none = helper(0.0, None, factors=None)
    assert [item["factor"] for item in omitted] == V.VARGA_FACTORS
    assert explicit_none == omitted
