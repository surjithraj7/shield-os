from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import IotSensor
from app.risk_engine import evaluate_value


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def admin_headers(client):
    res = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['token']}"}


@pytest.fixture(scope="module")
def operator_headers(client):
    res = client.post("/api/auth/login", json={"username": "operator", "password": "shield123"})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['token']}"}


@pytest.fixture(scope="module")
def sensor_id():
    return f"TEST-SETTLE-{uuid.uuid4().hex[:10]}"


@pytest.fixture(scope="module")
def registered_sensor(client, admin_headers, sensor_id):
    payload = {
        "sensor_id": sensor_id,
        "name": "Automated test settlement point",
        "sensor_type": "settlement",
        "unit": "mm",
        "ring_no": 99,
        "chainage_m": 220.0,
        "min_value": -100.0,
        "max_value": 100.0,
        "source": "simulated",
        "sampling_interval_s": 60.0,
    }
    res = client.post("/api/iot/sensors", json=payload, headers=admin_headers)
    assert res.status_code == 201, res.text
    return res.json()


class TestRiskEngineUnit:
    def test_low_reading(self):
        result = evaluate_value("settlement", 1.0, "mm")
        assert result["risk_category"] == "LOW"
        assert result["threshold_source"] == "builtin_demo"

    def test_threshold_categories(self):
        assert evaluate_value("settlement", 6.0, "mm")["risk_category"] == "MODERATE"
        assert evaluate_value("settlement", 11.0, "mm")["risk_category"] == "HIGH"
        assert evaluate_value("settlement", 25.0, "mm")["risk_category"] == "CRITICAL"

    def test_statistical_anomaly_detected(self):
        history = [2.0] * 20
        result = evaluate_value("settlement", 4.0, "mm", history=history)
        assert result["risk_category"] in {"MODERATE", "HIGH"}
        assert "statistical anomaly" in result["trigger"]

    def test_unknown_sensor_type_uses_anomaly_only(self):
        result = evaluate_value("unknown_sensor", 1.0, "x")
        assert result["risk_category"] == "LOW"
        assert result["threshold_source"] == "none"

    def test_simulated_data_has_lower_confidence(self):
        sim = evaluate_value("settlement", 1.0, "mm", sensor_source="simulated")
        real = evaluate_value("settlement", 1.0, "mm", sensor_source="real")
        assert sim["confidence"] < real["confidence"]

    def test_threshold_override_from_environment(self, monkeypatch):
        monkeypatch.setenv(
            "RISK_THRESHOLDS_JSON",
            '{"settlement": {"moderate": 1, "high": 2, "critical": 3}}',
        )
        result = evaluate_value("settlement", 2.5, "mm")
        assert result["risk_category"] == "HIGH"
        assert result["threshold_source"] == "environment_override"


class TestIotApi:
    def test_sensor_registration_requires_admin(self, client, operator_headers):
        res = client.post(
            "/api/iot/sensors",
            json={
                "sensor_id": f"TEST-OP-{uuid.uuid4().hex[:8]}",
                "sensor_type": "vibration",
                "unit": "mm/s",
            },
            headers=operator_headers,
        )
        assert res.status_code == 403

    def test_unauthorized_ingest_rejected(self, client, registered_sensor, monkeypatch):
        monkeypatch.delenv("IOT_INGEST_API_KEY", raising=False)
        res = client.post(
            "/api/iot/readings",
            json={"sensor_id": registered_sensor["sensor_id"], "value": 1.0, "unit": "mm"},
        )
        assert res.status_code == 401

    def test_valid_ingest_creates_assessment_and_alert(self, client, admin_headers, registered_sensor):
        res = client.post(
            "/api/iot/readings",
            json={
                "sensor_id": registered_sensor["sensor_id"],
                "value": 25.0,
                "unit": "mm",
                "event_id": f"evt-{uuid.uuid4().hex}",
            },
            headers=admin_headers,
        )
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["status"] == "accepted"
        assert body["risk"]["category"] == "CRITICAL"
        assert body["alert_id"] is not None

    def test_duplicate_event_returns_duplicate(self, client, admin_headers, registered_sensor):
        event_id = f"evt-{uuid.uuid4().hex}"
        payload = {
            "sensor_id": registered_sensor["sensor_id"],
            "value": 26.0,
            "unit": "mm",
            "event_id": event_id,
        }
        first = client.post("/api/iot/readings", json=payload, headers=admin_headers)
        second = client.post("/api/iot/readings", json=payload, headers=admin_headers)
        assert first.status_code == 201
        assert second.status_code == 201
        assert second.json()["duplicate"] is True
        assert second.json()["reading_id"] == first.json()["reading_id"]

    def test_alert_dedupe_and_escalation(self, client, admin_headers, registered_sensor):
        payload = {
            "sensor_id": registered_sensor["sensor_id"],
            "value": 30.0,
            "unit": "mm",
            "event_id": f"evt-{uuid.uuid4().hex}",
        }
        first = client.post("/api/iot/readings", json=payload, headers=admin_headers).json()
        payload["event_id"] = f"evt-{uuid.uuid4().hex}"
        payload["value"] = 31.0
        second = client.post("/api/iot/readings", json=payload, headers=admin_headers).json()
        assert first["alert_id"] == second["alert_id"]
        alert = client.get(f"/api/alerts/{first['alert_id']}").json()
        assert alert["occurrence_count"] >= 2
        assert alert["severity"] == "CRITICAL"

    def test_invalid_unit_rejected(self, client, admin_headers, registered_sensor):
        res = client.post(
            "/api/iot/readings",
            json={
                "sensor_id": registered_sensor["sensor_id"],
                "value": 3.0,
                "unit": "kPa",
                "event_id": f"evt-{uuid.uuid4().hex}",
            },
            headers=admin_headers,
        )
        assert res.status_code == 422

    def test_out_of_range_rejected(self, client, admin_headers, registered_sensor):
        res = client.post(
            "/api/iot/readings",
            json={
                "sensor_id": registered_sensor["sensor_id"],
                "value": 5000.0,
                "unit": "mm",
                "event_id": f"evt-{uuid.uuid4().hex}",
            },
            headers=admin_headers,
        )
        assert res.status_code == 422

    def test_out_of_order_is_accepted_and_flagged(self, client, admin_headers, registered_sensor):
        old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        res = client.post(
            "/api/iot/readings",
            json={
                "sensor_id": registered_sensor["sensor_id"],
                "value": 1.0,
                "unit": "mm",
                "measured_at": old,
                "event_id": f"evt-{uuid.uuid4().hex}",
            },
            headers=admin_headers,
        )
        assert res.status_code == 201
        assert res.json()["quality"] == "out_of_order"

    def test_alert_acknowledge_and_resolve(self, client, admin_headers, operator_headers, registered_sensor):
        ingested = client.post(
            "/api/iot/readings",
            json={
                "sensor_id": registered_sensor["sensor_id"],
                "value": 40.0,
                "unit": "mm",
                "event_id": f"evt-{uuid.uuid4().hex}",
            },
            headers=admin_headers,
        ).json()
        alert_id = ingested["alert_id"]
        ack = client.post(
            f"/api/alerts/{alert_id}/acknowledge",
            json={"note": "site engineer notified"},
            headers=operator_headers,
        )
        assert ack.status_code == 200
        assert ack.json()["status"] == "acknowledged"
        assert ack.json()["acknowledged_by"] == "operator"
        resolved = client.post(
            f"/api/alerts/{alert_id}/resolve",
            json={"note": "verified and instrument re-zeroed"},
            headers=admin_headers,
        )
        assert resolved.status_code == 200
        assert resolved.json()["status"] == "resolved"
        assert resolved.json()["resolved_by"] == "admin"

    def test_alert_action_requires_authentication(self, client):
        res = client.post("/api/alerts/1/acknowledge", json={"note": "x"})
        assert res.status_code == 401

    def test_sensor_list_and_health(self, client, registered_sensor):
        sensors = client.get("/api/iot/sensors").json()
        assert any(s["sensor_id"] == registered_sensor["sensor_id"] for s in sensors)
        health = client.get("/api/iot/health").json()
        assert health["total_sensors"] >= 1
        assert "connectivity_counts" in health

    def test_simulator_is_labelled_and_creates_data(self, client, admin_headers, registered_sensor):
        res = client.post(
            "/api/iot/simulate?sensor_type=settlement&count=2&anomaly=true&seed=7",
            headers=admin_headers,
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["source"] == "simulated"
        assert body["readings_created"] >= 2
        assert all(r["source"] == "simulated" for r in body["results"])

    def test_api_key_ingestion_path(self, client, registered_sensor, monkeypatch):
        monkeypatch.setenv("IOT_INGEST_API_KEY", "test-device-key")
        res = client.post(
            "/api/iot/readings",
            json={
                "sensor_id": registered_sensor["sensor_id"],
                "value": 2.0,
                "unit": "mm",
                "event_id": f"evt-{uuid.uuid4().hex}",
            },
            headers={"X-API-Key": "test-device-key"},
        )
        assert res.status_code == 201
        assert res.json()["source"] == "simulated"
        bad = client.post(
            "/api/iot/readings",
            json={
                "sensor_id": registered_sensor["sensor_id"],
                "value": 2.0,
                "unit": "mm",
                "event_id": f"evt-{uuid.uuid4().hex}",
            },
            headers={"X-API-Key": "wrong-key"},
        )
        assert bad.status_code == 401

    def test_offline_sensor_health_alert(self, client, admin_headers, sensor_id):
        db = SessionLocal()
        try:
            sensor = db.query(IotSensor).filter(IotSensor.sensor_id == sensor_id).first()
            sensor.last_seen_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
            sensor.sampling_interval_s = 60.0
            db.commit()
        finally:
            db.close()
        res = client.post("/api/iot/health/check", headers=admin_headers)
        assert res.status_code == 200
        assert res.json()["alerts_created"] >= 1
        health = client.get("/api/iot/health").json()
        row = next(r for r in health["sensors"] if r["sensor_id"] == sensor_id)
        assert row["connectivity"] == "offline"

    def test_regulatory_report_includes_iot_risk_section(self, client):
        res = client.get("/api/report/regulatory")
        assert res.status_code == 200, res.text[:400]
        assert "IoT Risk Engine and Alert Lifecycle" in res.text
        assert "Simulated Readings (Labelled)" in res.text
        assert "do not constitute a statutory" in res.text
