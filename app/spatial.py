from __future__ import annotations

import numpy as np


def shield_centerline(
    start_x: float,
    end_x: float,
    depth_m: float = 20.0,
    heading_deg: float = 90.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Shield drive axis as a 3D segment in local ENU.

    Heading 90 deg = east (positive x); depth below surface is negative z.
    """
    rad = np.deg2rad(heading_deg)
    dx = end_x - start_x
    a = np.array([start_x, 0.0, -depth_m])
    b = np.array([start_x + dx, dx * np.tan(rad) * 0.0, -depth_m])
    return a, b


def distance_to_segment(p: np.ndarray, a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    ab = b - a
    ap = p - a
    denom = float(np.dot(ab, ab))
    if denom < 1e-12:
        return float(np.linalg.norm(p - a)), 0.0
    t = np.clip(float(np.dot(ap, ab) / denom), 0.0, 1.0)
    proj = a + t * ab
    return float(np.linalg.norm(p - proj)), t


def evaluate_clearances(
    assets: list[dict],
    start_x: float,
    end_x: float,
    depth_m: float = 20.0,
) -> dict:
    a, b = shield_centerline(start_x, end_x, depth_m)
    line_len = float(np.linalg.norm(b - a))

    results = []
    for asset in assets:
        p = np.array([asset["x_enu"], asset["y_enu"], asset["z_enu"]], dtype=float)
        dist, t = distance_to_segment(p, a, b)
        clearance = dist - float(asset.get("radius_m", 0.5))
        limit = float(asset.get("clearance_limit_m", 3.0))
        along = t * line_len
        level = "critical" if clearance <= limit * 0.6 else "warning" if clearance <= limit else "safe"
        results.append(
            {
                "id": asset.get("id"),
                "name": asset["name"],
                "asset_type": asset["asset_type"],
                "distance_m": round(dist, 3),
                "clearance_m": round(clearance, 3),
                "clearance_limit_m": limit,
                "along_chainage_m": round(along, 2),
                "level": level,
                "note": asset.get("note", ""),
            }
        )

    results.sort(key=lambda r: r["clearance_m"])
    critical = [r for r in results if r["level"] == "critical"]
    warning = [r for r in results if r["level"] == "warning"]

    return {
        "centerline": {
            "start": a.tolist(),
            "end": b.tolist(),
            "length_m": round(line_len, 2),
            "depth_m": depth_m,
        },
        "results": results,
        "critical_count": len(critical),
        "warning_count": len(warning),
        "safe_count": len(results) - len(critical) - len(warning),
        "nearest": results[0] if results else None,
    }
