from __future__ import annotations

import json

import numpy as np

RECOMMEND_KEYS = [
    "thrust_kn",
    "torque_knm",
    "advance_speed_mm_min",
    "grouting_pressure_mpa",
    "grouting_volume_m3",
    "face_pressure_kpa",
]

KEY_LABELS = {
    "thrust_kn": "Thrust",
    "torque_knm": "Torque",
    "advance_speed_mm_min": "Advance Speed",
    "grouting_pressure_mpa": "Grouting Pressure",
    "grouting_volume_m3": "Grouting Volume",
    "face_pressure_kpa": "Face Pressure",
}


def _band(values, frac=0.20):
    vals = np.asarray(values, dtype=float)
    if len(vals) == 0:
        return None, None
    med = float(np.median(vals))
    lo = med * (1.0 - frac)
    hi = med * (1.0 + frac)
    return float(med), (float(lo), float(hi))


def recommend_for_target(
    source_rows: list[dict],
    geology_factor: float = 1.0,
    band_frac: float = 0.20,
) -> dict:
    """A/B/C experience transfer.

    Distills operational statistics from a mined segment (segment A / left line)
    into auto-suggested shield parameters for the target segment (segment B /
    right line), scaled by a geology transfer factor.
    """
    result = {}
    for key in RECOMMEND_KEYS:
        values = [r[key] for r in source_rows if r.get(key) is not None]
        med, band = _band(values, band_frac)
        if med is None:
            continue
        if key in ("grouting_pressure_mpa", "grouting_volume_m3"):
            med, band = med * geology_factor, (band[0] * geology_factor, band[1] * geology_factor)
        result[key] = {
            "label": KEY_LABELS[key],
            "median": round(med, 2),
            "band_lo": round(band[0], 2),
            "band_hi": round(band[1], 2),
            "confidence_samples": len(values),
        }
    return {
        "geology_factor": geology_factor,
        "method": "A/B/C experience transfer (percentile distillation + geology scaling)",
        "params": result,
        "source_samples": len(source_rows),
    }


def transfer_record(
    source_line: str,
    source_segment: str,
    target_line: str,
    target_segment: str,
    recommendation: dict,
) -> dict:
    return {
        "source_line": source_line,
        "source_segment": source_segment,
        "target_line": target_line,
        "target_segment": target_segment,
        "params_json": json.dumps(recommendation),
    }
