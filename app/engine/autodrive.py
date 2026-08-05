from __future__ import annotations

from dataclasses import dataclass, field

from app.risk import assess_risk


@dataclass
class AutodriveState:
    """Current live TBM operating point fed by SENSOR.EXE."""

    face_pressure_kpa: float = 300.0
    grouting_volume_m3: float = 2.4
    grouting_pressure_mpa: float = 2.6
    advance_speed_mm_min: float = 45.0
    thrust_kn: float = 12000.0
    torque_knm: float = 2200.0
    screw_rpm: float = 8.5


@dataclass
class AutodriveConfig:
    """Control-loop targets, actuator steps and sensitivity gains."""

    target_settlement_mm: float = 4.4
    alert_threshold_mm: float = 8.0
    face_pressure_step_kpa: float = 20.0
    max_face_pressure_kpa: float = 500.0
    grout_volume_step_m3: float = 0.2
    max_grout_volume_m3: float = 5.0
    grout_pressure_step_mpa: float = 0.1
    max_grout_pressure_mpa: float = 4.0
    advance_step_mm_min: float = 5.0
    min_advance_speed_mm_min: float = 20.0
    # settlement (mm) recovered per unit of each actuator, all positive
    sens_face_pressure_mm_per_kpa: float = 0.01
    sens_grout_volume_mm_per_m3: float = 0.8
    sens_grout_pressure_mm_per_mpa: float = 0.5
    sens_advance_mm_per_mm_min: float = 0.06
    priority_order: list[str] = field(
        default_factory=lambda: ["face_pressure", "grouting_volume", "grouting_pressure", "advance_speed"]
    )


ACTUATOR_META = {
    "face_pressure": {
        "label": "FACE SUPPORT PRESSURE",
        "unit": "kPa",
        "advice": "Increase face support pressure to restrain the tunnel-face relaxation feeding the settlement trough.",
    },
    "grouting_volume": {
        "label": "TAIL-VOID GROUT VOLUME",
        "unit": "m3",
        "advice": "Inject additional two-component backfill grout at the tail-void zone to back-fill the ground-loss volume.",
    },
    "grouting_pressure": {
        "label": "GROUTING PRESSURE",
        "unit": "MPa",
        "advice": "Raise tail-void grouting pressure to seat the gasket against the ground before hydration locks the ring.",
    },
    "advance_speed": {
        "label": "ADVANCE SPEED",
        "unit": "mm/min",
        "advice": "Reduce advance speed so fresh grout gains early-age stiffness before the following ring passes the tail.",
    },
}


def _recovery_capacity(state: AutodriveState, cfg: AutodriveConfig) -> dict[str, float]:
    return {
        "face_pressure": max(0.0, cfg.max_face_pressure_kpa - state.face_pressure_kpa) * cfg.sens_face_pressure_mm_per_kpa,
        "grouting_volume": max(0.0, cfg.max_grout_volume_m3 - state.grouting_volume_m3) * cfg.sens_grout_volume_mm_per_m3,
        "grouting_pressure": max(0.0, cfg.max_grout_pressure_mpa - state.grouting_pressure_mpa) * cfg.sens_grout_pressure_mm_per_mpa,
        "advance_speed": max(0.0, state.advance_speed_mm_min - cfg.min_advance_speed_mm_min) * cfg.sens_advance_mm_per_mm_min,
    }


def compute_advisory(
    state: AutodriveState,
    predicted_mm: float,
    monitored_mm: float | None = None,
    cfg: AutodriveConfig | None = None,
    anomaly_hints: list[str] | None = None,
) -> dict:
    cfg = cfg or AutodriveConfig()
    effective_mm = monitored_mm if monitored_mm is not None else predicted_mm
    overshoot = max(0.0, predicted_mm - cfg.target_settlement_mm)
    risk = assess_risk(effective_mm)

    if overshoot <= 1e-9:
        return {
            "mode": "TRACKING",
            "status": "NOMINAL",
            "predicted_mm": round(predicted_mm, 3),
            "monitored_mm": round(monitored_mm, 3) if monitored_mm is not None else None,
            "target_settlement_mm": cfg.target_settlement_mm,
            "overshoot_mm": 0.0,
            "residual_overshoot_mm": 0.0,
            "risk_level": risk["risk_level"],
            "alert_color": risk["alert_color"],
            "recommendations": [],
            "actuator_capacity_mm": {k: round(v, 3) for k, v in _recovery_capacity(state, cfg).items()},
            "anomaly_hints": anomaly_hints or [],
            "exhausted": False,
        }

    recommendations = []
    remaining = overshoot
    capacity = _recovery_capacity(state, cfg)

    SENS = {
        "face_pressure": cfg.sens_face_pressure_mm_per_kpa,
        "grouting_volume": cfg.sens_grout_volume_mm_per_m3,
        "grouting_pressure": cfg.sens_grout_pressure_mm_per_mpa,
        "advance_speed": cfg.sens_advance_mm_per_mm_min,
    }
    STEP = {
        "face_pressure": (cfg.face_pressure_step_kpa, cfg.max_face_pressure_kpa, "kPa", "face_pressure_kpa"),
        "grouting_volume": (cfg.grout_volume_step_m3, cfg.max_grout_volume_m3, "m3", "grouting_volume_m3"),
        "grouting_pressure": (cfg.grout_pressure_step_mpa, cfg.max_grout_pressure_mpa, "MPa", "grouting_pressure_mpa"),
        "advance_speed": (cfg.advance_step_mm_min, cfg.min_advance_speed_mm_min, "mm/min", "advance_speed_mm_min"),
    }

    def _adjust(actuator: str, descending: bool = False):
        nonlocal remaining
        if remaining <= 0.0:
            return
        step, bound, unit, attr = STEP[actuator]
        current = getattr(state, attr)
        if descending:
            headroom = current - bound
            if headroom <= 1e-9:
                return
            steps = max(1, int(remaining / (step * SENS[actuator])))
            delta = min(steps * step, headroom)
            recommended = max(bound, current - delta)
        else:
            headroom = bound - current
            if headroom <= 1e-9:
                return
            steps = max(1, int(remaining / (step * SENS[actuator])))
            delta = min(steps * step, headroom)
            recommended = current + delta
        recovered = min(delta * SENS[actuator], remaining)
        if recovered <= 1e-9:
            return
        remaining -= recovered
        recommendations.append(
            {
                "parameter": actuator,
                "label": ACTUATOR_META[actuator]["label"],
                "unit": unit,
                "current": round(current, 2),
                "recommended": round(recommended, 2),
                "delta": round(delta, 2),
                "expected_recovery_mm": round(recovered, 3),
                "advice": ACTUATOR_META[actuator]["advice"],
            }
        )

    for actuator in cfg.priority_order:
        if actuator == "advance_speed":
            _adjust("advance_speed", descending=True)
        else:
            _adjust(actuator)

    residual = max(0.0, remaining)
    saturated = residual > 0.05
    mode = "MITIGATING" if recommendations else "TRACKING"
    status = "CONTROL HEADROOM EXHAUSTED" if saturated else "RECOMMENDING"

    return {
        "mode": mode,
        "status": status,
        "predicted_mm": round(predicted_mm, 3),
        "monitored_mm": round(monitored_mm, 3) if monitored_mm is not None else None,
        "target_settlement_mm": cfg.target_settlement_mm,
        "overshoot_mm": round(overshoot, 3),
        "residual_overshoot_mm": round(residual, 3),
        "risk_level": risk["risk_level"],
        "alert_color": risk["alert_color"],
        "recommendations": recommendations,
        "actuator_capacity_mm": {k: round(v, 3) for k, v in capacity.items()},
        "anomaly_hints": anomaly_hints or [],
        "exhausted": saturated,
    }
