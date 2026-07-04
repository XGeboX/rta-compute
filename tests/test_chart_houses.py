"""Tropical chart houses must not be null for the default whole-sign option."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

_BIRTH = {
    "date": "1990-01-15",
    "time": "10:30:00",
    "lat": 28.6139,
    "lon": 77.209,
    "tz_hours": 5.5,
    "place_name": "Delhi",
}


def test_tropical_default_whole_sign_returns_houses():
    r = client.post(
        "/v1/chart",
        json={
            "birth": _BIRTH,
            "options": {"zodiac": "tropical", "house_system": "whole-sign"},
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["houses"] is not None
    assert len(body["houses"]["cusps"]) == 12


def test_tropical_whole_sign_differs_from_equal():
    """Regression: whole-sign must use Swiss Ephemeris W, not equal-house E."""
    whole = client.post(
        "/v1/chart",
        json={
            "birth": _BIRTH,
            "options": {"zodiac": "tropical", "house_system": "whole-sign"},
        },
    )
    equal = client.post(
        "/v1/chart",
        json={
            "birth": _BIRTH,
            "options": {"zodiac": "tropical", "house_system": "equal"},
        },
    )
    assert whole.status_code == 200, whole.text
    assert equal.status_code == 200, equal.text
    assert whole.json()["houses"]["cusps"] != equal.json()["houses"]["cusps"]
