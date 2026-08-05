from __future__ import annotations

import numpy as np
import pytest

from app.engine.consolidation import (
    ConsolidationParams,
    consolidation_settlement,
    consolidation_timeseries,
    excess_pore_pressure_field,
)
from app.engine.mindlin import (
    SoilParams,
    ShieldParams,
    immediate_settlement_trough,
    peak_immediate_settlement,
)
from app.engine.orchestrator import (
    EngineConfig,
    beijing_line12_reference,
    error_metrics,
    predict_at_point,
    total_settlement_trough,
)

SHIELD = ShieldParams()
SOIL = SoilParams()
CONSOLIDATION = ConsolidationParams()
ENGINE = EngineConfig()


class TestMindlinImmediate:
    def test_trough_symmetric_about_tunnel(self):
        y = np.linspace(-40.0, 40.0, 201)
        result = immediate_settlement_trough(
            np.array([-30.0]), y, SHIELD, SOIL, calibration=1.0
        )["total"][0]
        assert result.max() > 0
        assert np.allclose(result, result[::-1], atol=1e-6)
        assert abs(y[int(np.argmax(result))]) < 0.5

    def test_trough_peak_at_tunnel_axis(self):
        out = peak_immediate_settlement(-30.0, SHIELD, SOIL)
        assert abs(out["y_peak"]) < 0.5
        assert out["total_mm"] > 0.0

    def test_settlement_grows_behind_face(self):
        ahead = peak_immediate_settlement(15.0, SHIELD, SOIL)["total_mm"]
        behind = peak_immediate_settlement(-30.0, SHIELD, SOIL)["total_mm"]
        assert behind > ahead

    def test_no_settlement_ahead_of_face_without_ground_loss(self):
        y = np.linspace(-40.0, 40.0, 101)
        result = immediate_settlement_trough(
            np.array([20.0]), y, SHIELD, SOIL
        )["ground_loss"][0]
        assert np.allclose(result, 0.0, atol=1e-12)


class TestConsolidationHankel:
    def test_initial_pore_pressure_reproduced(self):
        r = np.linspace(0.0, 40.0, 41)
        z = np.linspace(0.5, 39.5, 40)
        field = excess_pore_pressure_field(r, z, 0.0, CONSOLIDATION)
        expected = CONSOLIDATION.p0_kpa * np.exp(
            -(r[:, None] ** 2) / (2.0 * CONSOLIDATION.sigma_r_m ** 2)
        ) * np.exp(
            -((z[None, :] - CONSOLIDATION.depth_m) ** 2)
            / (2.0 * CONSOLIDATION.sigma_z_m ** 2)
        )
        mask = (z > CONSOLIDATION.depth_m - 3 * CONSOLIDATION.sigma_z_m) & (
            z < CONSOLIDATION.depth_m + 3 * CONSOLIDATION.sigma_z_m
        )
        assert np.allclose(field[:, mask], expected[:, mask], rtol=0.2)

    def test_settlement_starts_at_zero(self):
        value = consolidation_settlement(np.array([0.0]), 0.0, CONSOLIDATION)
        assert abs(value) < 1e-9

    def test_settlement_monotonic_increasing(self):
        t = np.linspace(1.0, 2000.0, 40)
        values = consolidation_settlement(np.zeros(1), t, CONSOLIDATION)
        diffs = np.diff(values)
        assert np.all(diffs >= -1e-12)

    def test_final_settlement_matches_analytic(self):
        final = consolidation_settlement(np.array([0.0]), 1e9, CONSOLIDATION)
        analytic = (
            CONSOLIDATION.mv_per_mpa
            / 1000.0
            * CONSOLIDATION.p0_kpa
            * CONSOLIDATION.sigma_z_m
            * np.sqrt(2.0 * np.pi)
        )
        assert np.isclose(final, analytic, rtol=0.15)

    def test_timeseries_shape(self):
        series = consolidation_timeseries(np.array([10.0, 100.0]), CONSOLIDATION)
        assert series["settlement_m"][0] <= series["settlement_m"][1]


class TestOrchestration:
    def test_total_is_sum_of_components(self):
        y = np.linspace(-40.0, 40.0, 101)
        out = total_settlement_trough(-30.0, 60.0, SHIELD, SOIL, CONSOLIDATION, ENGINE, y)
        expected_total = out["immediate_mm"] + out["consolidation_mm"]
        assert np.allclose(out["total_mm"], expected_total, atol=1e-9)

    def test_prediction_scale_matches_reference(self):
        pred = predict_at_point(-30.0, 60.0, SHIELD, SOIL, CONSOLIDATION, ENGINE)
        assert 1.0 < pred["total_predicted_mm"] < 15.0

    def test_calibration_hits_monitored(self):
        from app.engine.orchestrator import calibrate_against_monitored

        config = calibrate_against_monitored(
            4.4, -30.0, 60.0, SHIELD, SOIL, CONSOLIDATION
        )
        pred = predict_at_point(
            -30.0, 60.0, SHIELD, SOIL, CONSOLIDATION, config
        )["total_predicted_mm"]
        assert abs(pred - 4.4) < 1e-6


class TestValidationTarget:
    def test_reported_beijing_line12_case(self):
        ref = beijing_line12_reference()
        assert ref["predicted_mm"] == pytest.approx(4.2)
        assert ref["monitored_mm"] == pytest.approx(4.4)
        assert ref["relative_error_pct"] < 5.0

    def test_error_metrics_under_5pct(self):
        metrics = error_metrics(4.2, 4.4)
        assert metrics["relative_error_pct"] < 5.0
        assert metrics["passes_5pct_threshold"] is True

    def test_error_metrics_over_5pct(self):
        metrics = error_metrics(5.0, 4.0)
        assert metrics["relative_error_pct"] > 5.0
        assert metrics["passes_5pct_threshold"] is False
