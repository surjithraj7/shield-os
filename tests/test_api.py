from __future__ import annotations

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.risk import AlarmThresholds, assess_risk


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


class TestEngineEndpoints:
    def test_health(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_immediate(self, client):
        response = client.post("/api/engine/immediate", json={"station": -30.0})
        assert response.status_code == 200
        body = response.json()
        assert len(body["y_m"]) == len(body["total_mm"])
        assert max(body["total_mm"]) > 0.0

    def test_consolidation(self, client):
        response = client.post(
            "/api/engine/consolidation", json={"t_days": [0.0, 30.0, 90.0]}
        )
        assert response.status_code == 200
        body = response.json()
        values = body["center_settlement_mm"]
        assert values[0] == 0.0
        assert values[-1] >= values[0]

    def test_total(self, client):
        response = client.post(
            "/api/engine/total", json={"station": -30.0, "t_days": 60.0}
        )
        assert response.status_code == 200
        body = response.json()
        assert np.allclose(
            np.array(body["total_mm"]),
            np.array(body["immediate_mm"]) + np.array(body["consolidation_mm"]),
        )

    def test_evaluate_beijing_scale(self, client):
        response = client.post(
            "/api/engine/evaluate", json={"monitored_mm": 4.4}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["monitored_value_mm"] == 4.4
        assert 1.0 < body["predicted_value_mm"] < 15.0
        assert "risk_level" in body
        assert "alert_color" in body

    def test_calibrate_roundtrip(self, client):
        response = client.post(
            "/api/engine/calibrate", json={"monitored_mm": 4.4}
        )
        assert response.status_code == 200
        factor = response.json()["calibration_immediate"]
        assert factor > 0
        evaluate = client.post(
            "/api/engine/evaluate",
            json={
                "monitored_mm": 4.4,
                "engine": {
                    "calibration_immediate": factor,
                    "calibration_consolidation": factor,
                },
            },
        )
        assert abs(evaluate.json()["predicted_value_mm"] - 4.4) < 1e-6


class TestDataEndpoints:
    def test_shield_param_crud(self, client):
        created = client.post(
            "/api/data/shield-params",
            json={
                "ring_no": 1,
                "chainage_m": 101.2,
                "thrust_kn": 12500.0,
                "advance_speed_mm_min": 42.0,
            },
        )
        assert created.status_code == 200
        listed = client.get("/api/data/shield-params")
        assert listed.status_code == 200
        assert any(r["ring_no"] == 1 for r in listed.json())

    def test_monitoring_and_calculated(self, client):
        created = client.post(
            "/api/data/monitoring",
            json={
                "ring_no": 2,
                "chainage_m": 102.4,
                "sensor_id": "SURF-002",
                "measured_value_mm": 4.4,
            },
        )
        assert created.status_code == 200
        monitored = client.get("/api/data/monitoring")
        assert any(r["sensor_id"] == "SURF-002" for r in monitored.json())
        calculated = client.get("/api/data/calculated")
        assert calculated.status_code == 200


class TestAssistant:
    def test_assistant_chat_rule_based_fallback(self, client, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        response = client.post("/api/assistant/chat", json={"message": "open the cyber twin"})
        assert response.status_code == 200
        body = response.json()
        assert body["reply"]
        assert isinstance(body["actions"], list)

    def test_assistant_chat_empty(self, client, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        response = client.post("/api/assistant/chat", json={"message": ""})
        assert response.status_code == 200
        assert response.json()["reply"]


class TestRiskRules:
    def test_orange_threshold(self):
        risk = assess_risk(10.0, AlarmThresholds())
        assert risk["alert_color"] == "orange"

    def test_yellow_threshold(self):
        risk = assess_risk(20.0, AlarmThresholds())
        assert risk["alert_color"] == "yellow"

    def test_red_threshold(self):
        risk = assess_risk(30.0, AlarmThresholds())
        assert risk["alert_color"] == "red"

    def test_green_below_thresholds(self):
        risk = assess_risk(4.4, AlarmThresholds())
        assert risk["alert_color"] == "green"
