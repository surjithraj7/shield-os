from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.engine.consolidation import ConsolidationParams
from app.engine.mindlin import ShieldParams, SoilParams
from app.engine.orchestrator import EngineConfig, total_settlement_trough


@dataclass
class XrayConfig:
    allowable_strain_ue: float = 150.0
    critical_strain_ue: float = 300.0
    settlement_warning_mm: float = 10.0
    settlement_critical_mm: float = 30.0
    asset_elastic_modulus_mpa: float = 30000.0
    trough_y_half_span_m: float = 40.0


def settlement_profile(
    station: float,
    t_days: float,
    shield: ShieldParams,
    soil: SoilParams,
    consolidation: ConsolidationParams,
    engine: EngineConfig,
    y_half_span: float = 40.0,
    n: int = 241,
) -> tuple[np.ndarray, np.ndarray]:
    y = np.linspace(-y_half_span, y_half_span, n)
    trough = total_settlement_trough(
        station, t_days, shield, soil, consolidation, engine, y
    )
    return y, trough["total_mm"]


def bending_strain_ue(
    settlement_mm: np.ndarray, y: np.ndarray, diameter_m: float
) -> tuple[float, float]:
    """Pipe-bending strain from the settlement trough curvature (microstrain).

    Strain = max|d2s/dy2| * D/2 applied over the transverse profile a pipe
    crossing the trough would see.
    """
    d2 = np.gradient(np.gradient(settlement_mm, y))
    max_curvature_1_m = float(np.max(np.abs(d2))) * 1e-3  # mm/m^2 -> 1/m
    strain = max_curvature_1_m * max(diameter_m, 1e-6) / 2.0
    return strain * 1e6, max_curvature_1_m


def _level_for(strain_ue: float, settlement_mm: float, cfg: XrayConfig) -> str:
    if strain_ue >= cfg.critical_strain_ue or settlement_mm >= cfg.settlement_critical_mm:
        return "critical"
    if strain_ue >= cfg.allowable_strain_ue or settlement_mm >= cfg.settlement_warning_mm:
        return "warning"
    return "safe"


def analyze_assets(
    assets: list[dict],
    start_x: float,
    end_x: float,
    t_days: float,
    depth_m: float,
    shield: ShieldParams,
    soil: SoilParams,
    consolidation: ConsolidationParams,
    engine: EngineConfig,
    cfg: XrayConfig | None = None,
    n_map_x: int = 24,
    n_map_y: int = 41,
) -> dict:
    cfg = cfg or XrayConfig()
    y = np.linspace(-cfg.trough_y_half_span_m, cfg.trough_y_half_span_m, n_map_y)
    results = []

    stations = [float(asset.get("x_enu", start_x)) - start_x for asset in assets]
    map_stations = np.linspace(0.0, float(end_x - start_x), n_map_x)
    all_stations = np.unique(np.round(np.concatenate([stations, map_stations]), 2))

    profiles: dict[float, np.ndarray] = {}
    for station in all_stations:
        profiles[station] = total_settlement_trough(
            float(station), t_days, shield, soil, consolidation, engine, y
        )["total_mm"]
    global_max = max(float(np.max(np.abs(p))) for p in profiles.values())

    map_surface = np.vstack([profiles[s] for s in np.round(map_stations, 2)])

    for asset in assets:
        station = float(asset.get("x_enu", start_x)) - start_x
        y_offset = float(asset.get("y_enu", 0.0))
        profile = profiles[round(station, 2)]
        settlement_mm = float(np.interp(y_offset, y, profile))

        diameter_m = 2.0 * max(float(asset.get("radius_m", 0.5)), 0.05)
        strain_ue, curvature = bending_strain_ue(profile, y, diameter_m)
        level = _level_for(strain_ue, settlement_mm, cfg)
        stress_mpa = strain_ue * 1e-6 * cfg.asset_elastic_modulus_mpa

        results.append(
            {
                "id": asset.get("id"),
                "name": asset["name"],
                "asset_type": asset.get("asset_type", "structure"),
                "x_enu": asset.get("x_enu"),
                "y_enu": asset.get("y_enu"),
                "z_enu": asset.get("z_enu"),
                "station_m": round(station, 2),
                "transverse_offset_m": round(y_offset, 2),
                "settlement_mm": round(settlement_mm, 3),
                "curvature_1_per_m": round(curvature, 6),
                "strain_ue": round(strain_ue, 2),
                "stress_mpa": round(stress_mpa, 3),
                "level": level,
                "safety_cone": {
                    "x": asset.get("x_enu"),
                    "y": asset.get("y_enu"),
                    "z": asset.get("z_enu"),
                    "radius_m": round(
                        max(float(asset.get("radius_m", 0.5)), 1.0 + settlement_mm / 8.0), 2
                    ),
                    "height_m": 8.0,
                },
            }
        )

    order = {"critical": 0, "warning": 1, "safe": 2}
    results.sort(key=lambda r: order.get(r["level"], 9))
    critical = [r for r in results if r["level"] == "critical"]
    warning = [r for r in results if r["level"] == "warning"]

    return {
        "start_x": start_x,
        "end_x": end_x,
        "depth_m": depth_m,
        "t_days": t_days,
        "results": results,
        "critical_count": len(critical),
        "warning_count": len(warning),
        "safe_count": len(results) - len(critical) - len(warning),
        "worst": results[0] if results else None,
        "max_settlement_mm": round(global_max, 3),
        "map": {
            "stations_m": np.round(map_stations, 2).tolist(),
            "y_m": np.round(y, 2).tolist(),
            "surface_mm": np.round(map_surface, 4).tolist(),
        },
    }
