from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AlarmThresholds:
    orange_mm: float = 10.0
    yellow_mm: float = 20.0
    red_mm: float = 30.0


def assess_risk(settlement_mm: float, thresholds: AlarmThresholds | None = None) -> dict[str, str]:
    if thresholds is None:
        thresholds = AlarmThresholds()
    if settlement_mm >= thresholds.red_mm:
        level, color = "high", "red"
    elif settlement_mm >= thresholds.yellow_mm:
        level, color = "warning", "yellow"
    elif settlement_mm >= thresholds.orange_mm:
        level, color = "notice", "orange"
    else:
        level, color = "low", "green"
    return {"risk_level": level, "alert_color": color}
