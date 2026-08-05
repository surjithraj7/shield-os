from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from scipy.integrate import quad


@dataclass
class ConsolidationParams:
    depth_m: float = 20.0
    tunnel_radius_m: float = 3.2
    base_depth_m: float = 40.0
    mv_per_mpa: float = 0.02
    cv_m2_per_day: float = 2.0
    ch_m2_per_day: float = 2.5
    p0_kpa: float = 20.0
    sigma_r_m: float = 8.0
    sigma_z_m: float = 2.5
    n_modes: int = 60


def _mode_coefficients(params: ConsolidationParams) -> np.ndarray:
    h = params.base_depth_m
    depth_h = params.depth_m
    sigma_z = params.sigma_z_m
    n = np.arange(1, params.n_modes + 1)
    lambda_n = (2 * n - 1) * np.pi / (2 * h)
    coeffs = np.zeros(n.size)
    for i, lam in enumerate(lambda_n):
        lower = depth_h - 3.0 * sigma_z
        upper = depth_h + 3.0 * sigma_z
        def integrand(z: float, lam_: float = lam) -> float:
            g = np.exp(-((z - depth_h) ** 2) / (2.0 * sigma_z ** 2))
            return g * np.sin(lam_ * z)
        value, _ = quad(integrand, max(lower, 0.0), min(upper, h), limit=200)
        coeffs[i] = 2.0 / h * value
    return coeffs


def excess_pore_pressure_field(
    r: np.ndarray,
    z: np.ndarray,
    t_days: float,
    params: ConsolidationParams,
) -> np.ndarray:
    lambda_n = (2 * np.arange(1, params.n_modes + 1) - 1) * np.pi / (2 * params.base_depth_m)
    coeffs = _mode_coefficients(params)
    sigma_h = 0.5 * params.sigma_r_m ** 2 + params.ch_m2_per_day * t_days
    radial_scale = 1.0 / (2.0 * sigma_h) * np.exp(-r ** 2 / (4.0 * sigma_h))
    pressure = np.zeros((r.size, z.size))
    for i, lam in enumerate(lambda_n):
        decay = np.exp(-params.cv_m2_per_day * lam ** 2 * t_days)
        for j, z_obs in enumerate(z):
            vertical = np.sin(lam * z_obs)
            pressure[:, j] += coeffs[i] * decay * vertical * radial_scale
    return params.p0_kpa * params.sigma_r_m ** 2 * pressure


def consolidation_settlement(
    r: np.ndarray,
    t_days: float | np.ndarray,
    params: ConsolidationParams,
) -> np.ndarray:
    t_array = np.atleast_1d(np.asarray(t_days, dtype=float))
    lambda_n = (2 * np.arange(1, params.n_modes + 1) - 1) * np.pi / (2 * params.base_depth_m)
    coeffs = _mode_coefficients(params)
    s0 = params.p0_kpa * np.sum(coeffs / lambda_n)
    st = params.p0_kpa * np.sum(
        coeffs[:, None] / lambda_n[:, None]
        * np.exp(-params.cv_m2_per_day * lambda_n[:, None] ** 2 * t_array[None, :]),
        axis=0,
    )
    sigma_h = 0.5 * params.sigma_r_m ** 2 + params.ch_m2_per_day * t_array
    initial_term = s0 * np.exp(-(r ** 2) / (2.0 * params.sigma_r_m ** 2))
    dissipating_term = st[:, None] * (params.sigma_r_m ** 2 / (2.0 * sigma_h))[:, None] * np.exp(
        -(r[None, :] ** 2) / (4.0 * sigma_h[:, None])
    )
    mv = params.mv_per_mpa / 1000.0
    result = mv * (initial_term[None, :] - dissipating_term)
    if np.ndim(t_days) == 0:
        return result[0]
    return result.T


def consolidation_timeseries(
    t_days: np.ndarray,
    params: ConsolidationParams,
    r_center: float = 0.0,
) -> dict[str, np.ndarray]:
    settlements = np.array([consolidation_settlement(np.array([r_center]), t, params)[0] for t in t_days])
    return {"t_days": t_days, "settlement_m": settlements}
