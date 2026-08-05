from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.engine.mindlin import (
    SoilParams,
    ShieldParams,
    immediate_settlement_trough,
    peak_immediate_settlement,
)


@dataclass
class GroutParams:
    """Time-dependent constitutive model for two-component backfill grout.

    The grout is pumped as a low-viscosity liquid, stays pumpable for a short
    window, then gels and hardens. Early-age behaviour controls how much of the
    tail-void volume loss reaches the surface within the first 6-24 hours, so
    the static ``volume_loss_pct`` of the Mindlin engine becomes a function of
    grout age.
    """

    pumpable_window_hours: float = 4.0
    gel_time_hours: float = 6.0
    final_stiffness_mpa: float = 12.0
    stiffness_rate: float = 0.45
    stiffness_shape: float = 1.4
    initial_viscosity_pas: float = 0.4
    gel_viscosity_pas: float = 600.0
    viscosity_rate: float = 0.9
    max_support_fraction: float = 0.85
    density_kn_m3: float = 20.0
    temperature_c: float = 20.0


def _logistic(x: float, rate: float, x0: float) -> float:
    """Smooth S-curve bounded in (0, 1)."""
    return 1.0 / (1.0 + np.exp(-rate * (x - x0)))


def viscosity(t_hours: float, p: GroutParams) -> float:
    """Dynamic viscosity [Pa.s]. Liquid during the pumpable window, then it
    gels toward the gel viscosity on an S-curve centred on ``gel_time_hours``.
    """
    if t_hours < p.pumpable_window_hours:
        growth = _logistic(t_hours, 2.0 / max(p.pumpable_window_hours, 1e-6), p.pumpable_window_hours * 0.5)
        return float(p.initial_viscosity_pas + growth * (p.initial_viscosity_pas * 0.5))
    rise = p.gel_viscosity_pas - p.initial_viscosity_pas
    return float(
        p.initial_viscosity_pas
        + rise * _logistic(t_hours, p.viscosity_rate, p.gel_time_hours)
    )


def stiffness_mpa(t_hours: float, p: GroutParams) -> float:
    """Early-age compressive/backfill stiffness E(t) [MPa] via a hardening
    S-curve. Reaches ``final_stiffness_mpa`` asymptotically."""
    s = _logistic(t_hours, p.stiffness_rate, p.gel_time_hours)
    return float(p.final_stiffness_mpa * s ** max(p.stiffness_shape, 0.01))


def hardening_fraction(t_hours: float, p: GroutParams) -> float:
    """Normalised degree of backfill support (0 liquid -> 1 fully hardened)."""
    s = _logistic(t_hours, p.stiffness_rate, p.gel_time_hours)
    return float(s ** max(p.stiffness_shape, 0.01))


def effective_volume_loss(volume_loss_pct: float, t_hours: float, p: GroutParams) -> float:
    """Tail-void ground loss that still reaches the surface at grout age
    ``t_hours``. A liquid grout transfers nearly the whole loss; a hardened
    grout caps the recoverable fraction at ``max_support_fraction``."""
    support = hardening_fraction(t_hours, p) * p.max_support_fraction
    return float(max(0.0, volume_loss_pct * (1.0 - support)))


def hydration_timeseries(
    t_hours: np.ndarray | list[float], p: GroutParams
) -> dict[str, np.ndarray]:
    t = np.asarray(t_hours, dtype=float)
    return {
        "t_hours": t,
        "viscosity_pas": np.array([viscosity(x, p) for x in t]),
        "stiffness_mpa": np.array([stiffness_mpa(x, p) for x in t]),
        "hardening_fraction": np.array([hardening_fraction(x, p) for x in t]),
    }


def grout_corrected_trough(
    stations: np.ndarray,
    y: np.ndarray,
    t_grout_hours: float,
    shield: ShieldParams,
    soil: SoilParams,
    grout: GroutParams,
    calibration: float = 1.0,
    base_volume_loss_pct: float | None = None,
) -> dict[str, np.ndarray]:
    """Recompute the immediate Mindlin trough with the tail-void ground loss
    replaced by the time-dependent grout-hardening effective loss."""
    volume_loss_pct = shield.volume_loss_pct if base_volume_loss_pct is None else base_volume_loss_pct
    eff_loss = effective_volume_loss(volume_loss_pct, t_grout_hours, grout)
    return immediate_settlement_trough(
        stations,
        y,
        shield,
        soil,
        calibration=calibration,
        volume_loss_pct=eff_loss,
    )


def grout_impact(
    station: float,
    t_grout_hours: float,
    shield: ShieldParams,
    soil: SoilParams,
    grout: GroutParams,
    calibration: float = 1.0,
) -> dict[str, float]:
    """Compare the static (liquid-grout) peak settlement against the
    grout-hardening corrected peak at grout age ``t_grout_hours``."""
    static = peak_immediate_settlement(
        station, shield, soil, calibration, volume_loss_pct=shield.volume_loss_pct
    )["total_mm"]
    corrected = peak_immediate_settlement(
        station, shield, soil, calibration, volume_loss_pct=effective_volume_loss(
            shield.volume_loss_pct, t_grout_hours, grout
        )
    )["total_mm"]
    reduction = static - corrected
    reduction_pct = reduction / static * 100.0 if static > 1e-9 else 0.0
    return {
        "station": station,
        "t_grout_hours": t_grout_hours,
        "static_peak_mm": float(static),
        "grout_corrected_peak_mm": float(corrected),
        "reduction_mm": float(reduction),
        "reduction_pct": float(reduction_pct),
        "effective_volume_loss_pct": float(
            effective_volume_loss(shield.volume_loss_pct, t_grout_hours, grout)
        ),
        "stiffness_mpa": float(stiffness_mpa(t_grout_hours, grout)),
        "hardening_fraction": float(hardening_fraction(t_grout_hours, grout)),
    }
