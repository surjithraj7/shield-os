from __future__ import annotations

import numpy as np
import pytest

from app.engine.autodrive import AutodriveConfig, AutodriveState, compute_advisory
from app.engine.grout import (
    GroutParams,
    effective_volume_loss,
    grout_impact,
    hydration_timeseries,
    stiffness_mpa,
    viscosity,
)
from app.engine.mindlin import ShieldParams, SoilParams
from app.engine.ringeye import RingEyeParams, analyze_ring, simulate_scan
from app.engine.xray import XrayConfig, analyze_assets
from app.engine.consolidation import ConsolidationParams
from app.engine.orchestrator import EngineConfig

SHIELD = ShieldParams()
SOIL = SoilParams()
CONSOLIDATION = ConsolidationParams()
ENGINE = EngineConfig()


class TestGroutSim:
    def test_viscosity_starts_liquid(self):
        assert viscosity(0.0, GroutParams()) < 1.0

    def test_viscosity_gels_over_time(self):
        p = GroutParams()
        assert viscosity(48.0, p) > viscosity(0.0, p)
        assert viscosity(48.0, p) >= p.gel_viscosity_pas * 0.99

    def test_stiffness_growth(self):
        p = GroutParams()
        assert stiffness_mpa(0.0, p) < 1.0
        assert stiffness_mpa(48.0, p) >= p.final_stiffness_mpa * 0.99
        assert stiffness_mpa(12.0, p) > stiffness_mpa(2.0, p)

    def test_effective_loss_decreases_with_age(self):
        p = GroutParams()
        early = effective_volume_loss(0.13, 0.0, p)
        late = effective_volume_loss(0.13, 48.0, p)
        assert 0.0 <= late < early <= 0.13

    def test_hydration_timeseries_shapes(self):
        series = hydration_timeseries(np.array([0.0, 2.0, 6.0, 24.0]), GroutParams())
        assert len(series["t_hours"]) == 4
        assert len(series["viscosity_pas"]) == 4
        assert len(series["stiffness_mpa"]) == 4
        assert len(series["hardening_fraction"]) == 4

    def test_impact_reduces_peak(self):
        imp = grout_impact(-30.0, 12.0, SHIELD, SOIL, GroutParams())
        assert imp["grout_corrected_peak_mm"] < imp["static_peak_mm"]
        assert imp["reduction_pct"] > 0.0


class TestAutodrive:
    def test_nominal_tracking(self):
        out = compute_advisory(AutodriveState(), 3.0, None, AutodriveConfig(target_settlement_mm=4.4))
        assert out["mode"] == "TRACKING"
        assert out["recommendations"] == []

    def test_mitigation_within_bounds(self):
        cfg = AutodriveConfig()
        out = compute_advisory(AutodriveState(), 12.0, 11.0, cfg)
        assert out["mode"] == "MITIGATING"
        assert len(out["recommendations"]) > 0
        assert 0.0 < out["residual_overshoot_mm"] < out["overshoot_mm"]
        for rec in out["recommendations"]:
            assert rec["expected_recovery_mm"] > 0.0
            if rec["parameter"] == "face_pressure":
                assert rec["recommended"] <= cfg.max_face_pressure_kpa
            if rec["parameter"] == "advance_speed":
                assert rec["recommended"] >= cfg.min_advance_speed_mm_min

    def test_recommendations_reduce_overshoot(self):
        out = compute_advisory(AutodriveState(), 10.0, None, AutodriveConfig())
        total_recovery = sum(r["expected_recovery_mm"] for r in out["recommendations"])
        assert total_recovery <= out["overshoot_mm"] + 1e-9

    def test_advance_speed_never_below_floor(self):
        out = compute_advisory(
            AutodriveState(advance_speed_mm_min=45.0), 30.0, None, AutodriveConfig()
        )
        advance = [r for r in out["recommendations"] if r["parameter"] == "advance_speed"]
        if advance:
            assert advance[-1]["recommended"] >= AutodriveConfig().min_advance_speed_mm_min


class TestRingEye:
    def test_ovalization_positive(self):
        cloud = simulate_scan(12.0, seed=1)
        res = analyze_ring(19, 122.8, cloud["radial_devs_mm"], cloud["angles_deg"])
        assert res["delta_d_mm"] > 0.0
        assert res["eccentricity_mm"] > 0.0
        assert res["joint_gap_mm"] > 0.0

    def test_risk_escalates_with_deformation(self):
        small = analyze_ring(1, 100.0, simulate_scan(2.0, seed=1)["radial_devs_mm"])
        big = analyze_ring(2, 101.2, simulate_scan(40.0, seed=1)["radial_devs_mm"])
        assert big["delta_d_mm"] > small["delta_d_mm"]
        assert big["seepage_risk"] in {"warning", "critical"}

    def test_critical_seepage(self):
        cloud = simulate_scan(60.0, seed=3, noise_mm=0.1)
        res = analyze_ring(27, 132.4, cloud["radial_devs_mm"])
        assert res["seepage_risk"] == "critical"

    def test_simulate_scan_point_count(self):
        cloud = simulate_scan(8.0, n_points=48)
        assert len(cloud["radial_devs_mm"]) == 48
        assert len(cloud["angles_deg"]) == 48


class TestXRay:
    ASSETS = [
        {"id": 1, "name": "Sewer DN800", "asset_type": "sewer", "x_enu": 158.0, "y_enu": 2.186, "z_enu": -10.0, "radius_m": 0.4},
        {"id": 2, "name": "Building B-01", "asset_type": "foundation", "x_enu": 180.0, "y_enu": -2.5, "z_enu": -8.0, "radius_m": 0.5},
        {"id": 3, "name": "Water Main", "asset_type": "water_main", "x_enu": 264.0, "y_enu": 1.5, "z_enu": -9.0, "radius_m": 0.6},
    ]

    def test_analyze_assets_shape(self):
        out = analyze_assets(self.ASSETS, 100.0, 244.0, 60.0, 20.0, SHIELD, SOIL, CONSOLIDATION, ENGINE)
        assert len(out["results"]) == 3
        assert out["critical_count"] + out["warning_count"] + out["safe_count"] == 3
        assert all(r["level"] in {"safe", "warning", "critical"} for r in out["results"])
        assert out["max_settlement_mm"] > 0.0

    def test_map_grid_shape(self):
        out = analyze_assets(self.ASSETS, 100.0, 244.0, 60.0, 20.0, SHIELD, SOIL, CONSOLIDATION, ENGINE)
        m = out["map"]
        assert len(m["stations_m"]) == len(m["surface_mm"])
        assert all(len(row) == len(m["y_m"]) for row in m["surface_mm"])
        assert np.array(m["surface_mm"]).max() > 0.0
        assert float(np.array(m["surface_mm"]).min()) > -1.0

    def test_settlement_decays_transversally(self):
        out = analyze_assets(self.ASSETS, 100.0, 244.0, 60.0, 20.0, SHIELD, SOIL, CONSOLIDATION, ENGINE)
        center = next(r for r in out["results"] if r["transverse_offset_m"] < 2.0)
        assert center["settlement_mm"] >= 0.0
        assert center["strain_ue"] >= 0.0
        assert center["stress_mpa"] >= 0.0
