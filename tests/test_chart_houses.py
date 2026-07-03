"""Tropical chart houses must not be null for the default whole-sign option."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_tropical_default_whole_sign_returns_houses():
    r = client.post(
        "/v1/chart",
        json={
            "birth": {
                "date": "1990-01-15",
                "time": "10:30:00",
                "lat": 28.6139,
                "lon": 77.209,
                "tz_hours": 5.5,
                "place_name": "Delhi",
            },
            "options": {"zodiac": "tropical", "house_system": "whole-sign"},
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["houses"] is not None
    assert len(body["houses"]["cusps"]) == 12
