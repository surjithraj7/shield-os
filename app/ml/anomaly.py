from __future__ import annotations

from typing import Iterable

import numpy as np


def zscore_anomalies(
    values: Iterable[float],
    window: int = 10,
    z_threshold: float = 2.5,
) -> list[dict]:
    """Unsupervised anomaly scan using rolling z-score over a sliding window.

    Flags points whose deviation from the trailing local mean exceeds
    ``z_threshold`` standard deviations. Precedes static threshold alarms.
    """
    arr = np.asarray(list(values), dtype=float)
    n = len(arr)
    out: list[dict] = []
    if n < 4:
        return out
    for i in range(1, n):
        lo = max(0, i - window)
        seg = arr[lo:i]
        mu = float(seg.mean())
        sd = float(seg.std())
        if sd < 1e-12:
            sd = 1e-12
        z = (arr[i] - mu) / sd
        out.append(
            {
                "index": i,
                "value": float(arr[i]),
                "mean": mu,
                "zscore": float(z),
                "anomaly": bool(abs(z) >= z_threshold),
            }
        )
    return out


def scan_series(
    values: Iterable[float],
    window: int = 10,
    z_threshold: float = 2.5,
) -> dict:
    points = zscore_anomalies(values, window, z_threshold)
    flagged = [p for p in points if p["anomaly"]]
    max_z = max([abs(p["zscore"]) for p in points], default=0.0)
    return {
        "points": points,
        "flagged_count": len(flagged),
        "total_points": len(points),
        "max_zscore": float(max_z),
        "method": "rolling-zscore",
        "window": window,
        "z_threshold": z_threshold,
        "flagged": flagged,
    }


def severity(zscore: float) -> str:
    if abs(zscore) >= 4.0:
        return "critical"
    if abs(zscore) >= 3.0:
        return "warning"
    return "notice"
