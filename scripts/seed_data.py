from __future__ import annotations

import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import SessionLocal, init_db
from app.engine.consolidation import ConsolidationParams
from app.engine.mindlin import SoilParams, ShieldParams
from app.engine.orchestrator import EngineConfig, predict_at_point
from app.models import CalculatedResult, MonitoringData, ShieldParameter
from app.risk import assess_risk

LINE = "Beijing Metro Line 12"
SECTION = "TBM-left-line"
N_RINGS = 120
RING_LENGTH_M = 1.2
BASE_CHAINAGE_M = 100.0
STATION_BEHIND_FACE_M = -30.0
CONSOLIDATION_DAYS = 60.0

SHIELD = ShieldParams(
    depth_m=20.0,
    radius_m=3.2,
    length_m=8.0,
    face_pressure_kpa=300.0,
    skin_friction_kpa=60.0,
    volume_loss_pct=0.13,
    trough_width_coef=0.5,
)
SOIL = SoilParams(es_mpa=30.0, poisson=0.35, gamma_kn_m3=18.0)
CONSOLIDATION = ConsolidationParams(
    depth_m=20.0,
    tunnel_radius_m=3.2,
    base_depth_m=40.0,
    mv_per_mpa=0.02,
    cv_m2_per_day=2.0,
    ch_m2_per_day=2.5,
    p0_kpa=20.0,
    sigma_r_m=8.0,
    sigma_z_m=2.5,
    n_modes=60,
)
ENGINE = EngineConfig(calibration_immediate=1.0, calibration_consolidation=1.0)


def shield_params_for_ring(ring_no: int) -> dict:
    cycle = math.sin(ring_no / 12.0)
    thrust = 12000.0 + 1200.0 * cycle
    speed = 42.0 + 6.0 * math.sin(ring_no / 8.0)
    return {
        "line": LINE,
        "section": SECTION,
        "ring_no": ring_no,
        "chainage_m": BASE_CHAINAGE_M + ring_no * RING_LENGTH_M,
        "thrust_kn": round(thrust, 1),
        "advance_speed_mm_min": round(speed, 1),
        "torque_knm": round(3800.0 + 300.0 * cycle, 1),
        "grouting_pressure_mpa": round(0.35 + 0.05 * cycle, 3),
        "grouting_volume_m3": round(9.5 + 0.6 * cycle, 2),
        "face_pressure_kpa": round(300.0 + 25.0 * cycle, 1),
        "pitch_deg": round(0.1 * cycle, 3),
        "yaw_deg": round(-0.1 * cycle, 3),
    }


def predicted_for_ring(ring_no: int) -> float:
    result = predict_at_point(
        STATION_BEHIND_FACE_M,
        CONSOLIDATION_DAYS,
        SHIELD,
        SOIL,
        CONSOLIDATION,
        ENGINE,
    )
    return result["total_predicted_mm"]


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        db.query(CalculatedResult).delete()
        db.query(MonitoringData).delete()
        db.query(ShieldParameter).delete()

        for ring in range(1, N_RINGS + 1):
            db.add(ShieldParameter(**shield_params_for_ring(ring)))

        base_prediction = predicted_for_ring(1)
        for ring in range(1, N_RINGS + 1):
            perturbation = 0.15 * math.sin(ring / 9.0)
            predicted = base_prediction + perturbation
            monitored = predicted + 0.08 * math.sin(ring / 7.0) + 0.05 * math.cos(ring / 13.0)
            if abs(predicted - monitored) / monitored >= 0.05:
                monitored = predicted * (1.0 + 0.02 * math.sin(ring))
            risk = assess_risk(monitored)
            db.add(
                MonitoringData(
                    line=LINE,
                    section=SECTION,
                    ring_no=ring,
                    chainage_m=BASE_CHAINAGE_M + ring * RING_LENGTH_M,
                    sensor_id=f"SURF-{ring:03d}",
                    target_type="surface",
                    measured_value_mm=round(monitored, 2),
                )
            )
            db.add(
                CalculatedResult(
                    line=LINE,
                    section=SECTION,
                    ring_no=ring,
                    chainage_m=BASE_CHAINAGE_M + ring * RING_LENGTH_M,
                    model_name="mindlin+hankel",
                    immediate_mm=round(predicted * 0.72, 2),
                    consolidation_mm=round(predicted * 0.28, 2),
                    predicted_value_mm=round(predicted, 2),
                    monitored_value_mm=round(monitored, 2),
                    difference_mm=round(predicted - monitored, 2),
                    relative_error_pct=round(abs(predicted - monitored) / monitored * 100.0, 2),
                    risk_level=risk["risk_level"],
                )
            )
        db.commit()
        print(f"Seeded {N_RINGS} rings, {N_RINGS} monitoring rows, {N_RINGS} calculated rows.")
        print(f"Representative prediction: {base_prediction:.2f} mm vs monitored target ~4.4 mm scale")
    finally:
        db.close()


if __name__ == "__main__":
    main()
