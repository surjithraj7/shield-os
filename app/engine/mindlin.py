from __future__ import annotations

import numpy as np
from dataclasses import dataclass


@dataclass
class SoilParams:
    es_mpa: float = 30.0
    poisson: float = 0.35
    gamma_kn_m3: float = 18.0


@dataclass
class ShieldParams:
    depth_m: float = 20.0
    radius_m: float = 3.2
    y_center_m: float = 0.0
    length_m: float = 8.0
    face_pressure_kpa: float = 300.0
    skin_friction_kpa: float = 60.0
    volume_loss_pct: float = 0.13
    trough_width_coef: float = 0.5


def _mindlin_surface_settlement(
    px: float,
    x0: float,
    y0: float,
    depth_c: float,
    x: float,
    y: float,
    soil: SoilParams,
) -> float:
    g_modulus = soil.es_mpa * 1000.0 / (2.0 * (1.0 + soil.poisson))
    r_sq = (x - x0) ** 2 + (y - y0) ** 2 + depth_c ** 2
    r = np.sqrt(r_sq)
    if r < 1e-9:
        r = 1e-9
    term_1 = (1.0 - 2.0 * soil.poisson) / (r * (r + depth_c))
    term_2 = depth_c / r ** 3
    return px * (x - x0) / (4.0 * np.pi * g_modulus) * (term_1 - term_2)


def _face_thrust_settlement(
    stations: np.ndarray,
    y: np.ndarray,
    shield: ShieldParams,
    soil: SoilParams,
    n_radial: int = 20,
    n_angle: int = 48,
) -> np.ndarray:
    depth_h = shield.depth_m
    radius_a = shield.radius_m
    earth_pressure = soil.gamma_kn_m3 * depth_h
    net_pressure = shield.face_pressure_kpa - earth_pressure
    if abs(net_pressure) < 1e-6:
        return np.zeros((stations.size, y.size))
    rho = np.linspace(1e-3, radius_a, n_radial)
    theta = np.linspace(0.0, 2.0 * np.pi, n_angle, endpoint=False)
    weights = np.outer(rho, np.ones(n_angle)) * (radius_a / n_radial) * (2.0 * np.pi / n_angle)
    dpx = net_pressure * weights
    y0 = shield.y_center_m + rho[:, None] * np.sin(theta[None, :])
    depth = depth_h + rho[:, None] * np.cos(theta[None, :])
    result = np.zeros((stations.size, y.size))
    for i, x_station in enumerate(stations):
        for j, y_obs in enumerate(y):
            total = 0.0
            for k in range(n_radial):
                for m in range(n_angle):
                    total += _mindlin_surface_settlement(
                        dpx[k, m], 0.0, y0[k, m], depth[k, m], x_station, y_obs, soil
                    )
            result[i, j] = total
    return result


def _skin_friction_settlement(
    stations: np.ndarray,
    y: np.ndarray,
    shield: ShieldParams,
    soil: SoilParams,
    n_along: int = 24,
    n_angle: int = 48,
) -> np.ndarray:
    depth_h = shield.depth_m
    radius_a = shield.radius_m
    if shield.skin_friction_kpa <= 0.0:
        return np.zeros((stations.size, y.size))
    along = np.linspace(0.0, shield.length_m, n_along)
    theta = np.linspace(0.0, 2.0 * np.pi, n_angle, endpoint=False)
    weights = (shield.length_m / n_along) * (2.0 * np.pi / n_angle)
    dpx = shield.skin_friction_kpa * radius_a * weights
    result = np.zeros((stations.size, y.size))
    for i, x_station in enumerate(stations):
        for j, y_obs in enumerate(y):
            total = 0.0
            for k in range(n_along):
                x0 = -along[k]
                for m in range(n_angle):
                    y0 = shield.y_center_m + radius_a * np.sin(theta[m])
                    depth = depth_h + radius_a * np.cos(theta[m])
                    total += _mindlin_surface_settlement(
                        dpx, x0, y0, depth, x_station, y_obs, soil
                    )
            result[i, j] = total
    return result


def _ground_loss_settlement(
    stations: np.ndarray,
    y: np.ndarray,
    shield: ShieldParams,
    volume_loss_pct: float | None = None,
) -> np.ndarray:
    depth_h = shield.depth_m
    radius_a = shield.radius_m
    trough_width = shield.trough_width_coef * depth_h
    loss = shield.volume_loss_pct if volume_loss_pct is None else volume_loss_pct
    max_settlement = (
        loss / 100.0 * np.pi * radius_a ** 2
    ) / (trough_width * np.sqrt(2.0 * np.pi))
    gaussian = np.exp(-(y - shield.y_center_m) ** 2 / (2.0 * trough_width ** 2))
    result = np.zeros((stations.size, y.size))
    for i, x_station in enumerate(stations):
        fraction = 1.0
        if x_station < -shield.length_m:
            fraction = 1.0
        elif x_station > 0.0:
            fraction = 0.0
        else:
            fraction = -x_station / shield.length_m
        result[i, :] = max_settlement * gaussian * fraction
    return result


def immediate_settlement_trough(
    stations: np.ndarray,
    y: np.ndarray,
    shield: ShieldParams,
    soil: SoilParams,
    calibration: float = 1.0,
    volume_loss_pct: float | None = None,
) -> dict[str, np.ndarray]:
    thrust = _face_thrust_settlement(stations, y, shield, soil)
    friction = _skin_friction_settlement(stations, y, shield, soil)
    ground_loss = _ground_loss_settlement(stations, y, shield, volume_loss_pct)
    total = calibration * (thrust + friction + ground_loss)
    return {
        "thrust": thrust,
        "friction": friction,
        "ground_loss": ground_loss,
        "total": total,
    }


def peak_immediate_settlement(
    station: float,
    shield: ShieldParams,
    soil: SoilParams,
    calibration: float = 1.0,
    y_range: tuple[float, float] = (-30.0, 30.0),
    n_y: int = 401,
    volume_loss_pct: float | None = None,
) -> dict[str, float]:
    y = np.linspace(y_range[0], y_range[1], n_y)
    result = immediate_settlement_trough(
        np.array([station]), y, shield, soil, calibration, volume_loss_pct
    )
    peak_idx = int(np.argmax(np.abs(result["total"][0])))
    return {
        "station": station,
        "y_peak": float(y[peak_idx]),
        "total_mm": float(result["total"][0, peak_idx] * 1000.0),
        "thrust_mm": float(result["thrust"][0, peak_idx] * 1000.0),
        "friction_mm": float(result["friction"][0, peak_idx] * 1000.0),
        "ground_loss_mm": float(result["ground_loss"][0, peak_idx] * 1000.0),
    }
