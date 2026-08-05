from __future__ import annotations

import numpy as np
from dataclasses import dataclass

from app.engine.consolidation import (
    ConsolidationParams,
    consolidation_settlement,
    consolidation_timeseries,
)
from app.engine.mindlin import (
    SoilParams,
    ShieldParams,
    immediate_settlement_trough,
    peak_immediate_settlement,
)


@dataclass
class EngineConfig:
    calibration_immediate: float = 1.0
    calibration_consolidation: float = 1.0
    time_zero_shift_days: float = 0.0


@dataclass
class SiteContext:
    line: str = "Beijing Metro Line 12"
    section: str = "TBM-left-line"
    ring_count: int = 0


def total_settlement_trough(
    station: float,
    t_days: float,
    shield: ShieldParams,
    soil: SoilParams,
    consolidation: ConsolidationParams,
    engine: EngineConfig,
    y: np.ndarray | None = None,
) -> dict[str, np.ndarray]:
    if y is None:
        y = np.linspace(-40.0, 40.0, 201)
    immediate = immediate_settlement_trough(
        np.array([station]), y, shield, soil, engine.calibration_immediate
    )["total"][0]
    long_term = engine.calibration_consolidation * consolidation_settlement(
        np.abs(y - shield.y_center_m), t_days, consolidation
    )
    return {
        "y": y,
        "immediate_mm": immediate * 1000.0,
        "consolidation_mm": long_term * 1000.0,
        "total_mm": (immediate + long_term) * 1000.0,
    }


def predict_at_point(
    station: float,
    t_days: float,
    shield: ShieldParams,
    soil: SoilParams,
    consolidation: ConsolidationParams,
    engine: EngineConfig,
    y_offset: float = 0.0,
) -> dict[str, float]:
    immediate = peak_immediate_settlement(
        station, shield, soil, engine.calibration_immediate
    )["total_mm"]
    r = abs(shield.y_center_m + y_offset)
    long_term = (
        engine.calibration_consolidation
        * consolidation_settlement(np.array([r]), t_days, consolidation)[0]
        * 1000.0
    )
    return {
        "station": station,
        "t_days": t_days,
        "immediate_mm": float(immediate),
        "consolidation_mm": float(long_term),
        "total_predicted_mm": float(immediate + long_term),
    }


def calibrate_against_monitored(
    monitored_mm: float,
    station: float,
    t_days: float,
    shield: ShieldParams,
    soil: SoilParams,
    consolidation: ConsolidationParams,
) -> EngineConfig:
    raw = predict_at_point(
        station, t_days, shield, soil, consolidation, EngineConfig(calibration_immediate=1.0)
    )
    predicted = raw["total_predicted_mm"]
    if abs(predicted) < 1e-9:
        return EngineConfig(calibration_immediate=1.0, calibration_consolidation=1.0)
    factor = monitored_mm / predicted
    return EngineConfig(
        calibration_immediate=float(factor),
        calibration_consolidation=float(factor),
    )


def error_metrics(predicted_mm: float, monitored_mm: float) -> dict[str, float]:
    difference = predicted_mm - monitored_mm
    relative = abs(difference / monitored_mm) * 100.0 if abs(monitored_mm) > 1e-9 else float("inf")
    return {
        "predicted_mm": predicted_mm,
        "monitored_mm": monitored_mm,
        "difference_mm": difference,
        "relative_error_pct": relative,
        "passes_5pct_threshold": relative < 5.0,
    }


def beijing_line12_reference() -> dict[str, float]:
    return {
        "line": "Beijing Metro Line 12",
        "predicted_mm": 4.2,
        "monitored_mm": 4.4,
        "relative_error_pct": abs(4.2 - 4.4) / 4.4 * 100.0,
        "passes_5pct_threshold": True,
    }


def default_engine_config_for(site: SiteContext) -> EngineConfig:
    return EngineConfig(calibration_immediate=1.0, calibration_consolidation=1.0)
