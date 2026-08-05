from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass
class RingEyeParams:
    nominal_diameter_mm: float = 6400.0
    segment_count: int = 8
    joint_allowance_mm: float = 1.0
    seepage_critical_mm: float = 2.0
    joint_gap_factor: float = 0.35


def analyze_ring(
    ring_no: int,
    chainage_m: float,
    radial_devs_mm: list[float] | np.ndarray,
    angles_deg: list[float] | np.ndarray | None = None,
    params: RingEyeParams | None = None,
) -> dict:
    """Quantify circumferential ring deformation from a radial point-cloud
    scan (deviation from the nominal radius, mm) vs the ideal CAD geometry.

    Ovalization ΔD is the peak-to-peak radial spread scaled to diameter terms;
    joint opening follows from the ovalization distributed across the segment
    joints.
    """
    params = params or RingEyeParams()
    devs = np.asarray(radial_devs_mm, dtype=float)
    if devs.size < 4:
        raise ValueError("radial_devs_mm must contain at least 4 points")

    nominal_r = params.nominal_diameter_mm / 2.0
    radii = nominal_r + devs
    r_min = float(radii.min())
    r_max = float(radii.max())
    delta_d = r_max - r_min
    eccentricity = delta_d / 2.0
    ovalization_pct = delta_d / params.nominal_diameter_mm * 100.0

    avg_r = float(radii.mean())
    rms_dev = float(np.sqrt(np.mean((radii - avg_r) ** 2)))

    joint_gap = delta_d * math.pi / max(params.segment_count, 1) * params.joint_gap_factor

    if joint_gap >= params.seepage_critical_mm:
        seepage_risk = "critical"
        status = "seepage_risk"
    elif joint_gap >= params.joint_allowance_mm:
        seepage_risk = "warning"
        status = "joint_gap"
    else:
        seepage_risk = "normal"
        status = "normal"

    return {
        "ring_no": ring_no,
        "chainage_m": chainage_m,
        "nominal_diameter_mm": params.nominal_diameter_mm,
        "radius_min_mm": round(r_min, 3),
        "radius_max_mm": round(r_max, 3),
        "mean_radius_mm": round(avg_r, 3),
        "rms_deviation_mm": round(rms_dev, 3),
        "delta_d_mm": round(delta_d, 3),
        "eccentricity_mm": round(eccentricity, 3),
        "ovalization_pct": round(ovalization_pct, 4),
        "joint_gap_mm": round(joint_gap, 3),
        "seepage_risk": seepage_risk,
        "status": status,
        "n_measurements": int(devs.size),
        "segments": params.segment_count,
    }


def simulate_scan(
    ovalization_mm: float,
    n_points: int = 48,
    noise_mm: float = 0.4,
    seed: int | None = None,
) -> dict:
    """Generate a synthetic optical/LiDAR radial point cloud for a ring
    deformed into an ellipse with major/minor axis spread ``ovalization_mm``."""
    rng = np.random.default_rng(seed)
    theta = np.linspace(0.0, 2.0 * np.pi, n_points, endpoint=False)
    a = ovalization_mm / 2.0  # semi-major offset (mm)
    # radial deviation of an ellipse vs a circle of equal perimeter is approx.
    dev = a * np.cos(2.0 * theta) + rng.normal(0.0, noise_mm, n_points)
    return {
        "angles_deg": (np.degrees(theta)).tolist(),
        "radial_devs_mm": np.round(dev, 3).tolist(),
    }
