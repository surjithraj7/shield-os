from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


class TestGroutEndpoints:
    def test_hydration(self, client):
        res = client.post(
            "/api/grout/hydration",
            json={"t_hours": [0, 2, 6, 24]},
        )
        assert res.status_code == 200
        body = res.json()
        assert len(body["t_hours"]) == 4
        assert len(body["stiffness_mpa"]) == 4
        assert body["stiffness_mpa"][-1] > body["stiffness_mpa"][0]

    def test_impact(self, client):
        res = client.post(
            "/api/grout/impact",
            json={"station": -30.0, "t_grout_hours": 12.0},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["grout_corrected_peak_mm"] < body["static_peak_mm"]
        assert body["reduction_pct"] > 0.0


class TestAutodriveEndpoints:
    def test_advisory_get(self, client):
        res = client.get("/api/autodrive/advisory")
        assert res.status_code == 200
        body = res.json()
        assert "mode" in body
        assert "recommendations" in body
        assert "context" in body

    def test_advisory_post(self, client):
        res = client.post(
            "/api/autodrive/advisory",
            json={"predicted_mm": 15.0, "monitored_mm": 14.0, "target_mm": 4.4},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["mode"] == "MITIGATING"
        assert len(body["recommendations"]) > 0
        assert body["overshoot_mm"] > 0.0


class TestRingEyeEndpoints:
    def test_scan_persists(self, client):
        res = client.post(
            "/api/ringeye/scan",
            json={"ring_no": 40, "chainage_m": 148.0, "ovalization_mm": 15.0},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["analysis"]["delta_d_mm"] > 0.0
        assert "ring_no" in body["stored"]
        readings = client.get("/api/ringeye/readings")
        assert any(r["ring_no"] == 40 for r in readings.json())

    def test_analyze(self, client):
        res = client.post(
            "/api/ringeye/analyze",
            json={
                "ring_no": 5,
                "chainage_m": 106.0,
                "radial_devs_mm": [0, 2, 0, -2, 0, 2, 0, -2],
                "nominal_diameter_mm": 6400.0,
                "segment_count": 8,
            },
        )
        assert res.status_code == 200
        assert res.json()["delta_d_mm"] > 0.0

    def test_summary(self, client):
        res = client.get("/api/ringeye/summary")
        assert res.status_code == 200
        assert "risk_counts" in res.json()


class TestXRayEndpoints:
    def test_map(self, client):
        res = client.post(
            "/api/xray/map",
            json={"start_x": 100, "end_x": 244, "t_days": 60},
        )
        assert res.status_code == 200
        body = res.json()
        assert "results" in body
        assert "map" in body
        assert body["max_settlement_mm"] > 0.0
        m = body["map"]
        assert len(m["stations_m"]) == len(m["surface_mm"])
        assert len(m["surface_mm"][0]) == len(m["y_m"])

    def test_summary(self, client):
        res = client.get("/api/xray/summary")
        assert res.status_code == 200
        assert "critical_count" in res.json()
