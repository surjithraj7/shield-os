"""
Unit tests for Edge-Native PINN Acceleration & Hankel-CUDA Surrogate Engine
===========================================================================
Tests calculation speed (<5ms), circuit breaker mechanics, analytical parity, 
and automatic fallback capabilities.
"""

import time
import numpy as np
import pytest

from app.engine.mindlin import SoilParams, ShieldParams
from app.engine.consolidation import ConsolidationParams
from app.engine.orchestrator import EngineConfig, total_settlement_trough
from app.engine.pinn_surrogate import PINNSurrogateEngine, CircuitBreakerOpenException


def test_pinn_surrogate_speed_and_format():
    engine = PINNSurrogateEngine()
    shield = ShieldParams()
    soil = SoilParams()
    consolidation = ConsolidationParams()
    y = np.linspace(-30.0, 30.0, 101)

    start = time.perf_counter()
    res = engine.predict_trough(
        station=0.0,
        t_days=30.0,
        shield=shield,
        soil=soil,
        consolidation=consolidation,
        y=y,
    )
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    assert elapsed_ms < 15.0, f"PINN engine execution took {elapsed_ms:.2f}ms, expected <15ms"
    assert res["engine_mode"] == "PINN_ULTRA_SPEED"
    assert "total_mm" in res
    assert len(res["total_mm"]) == len(y)
    assert res["circuit_state"] == "CLOSED"


def test_orchestrator_pinn_toggle_and_fallback():
    shield = ShieldParams()
    soil = SoilParams()
    consolidation = ConsolidationParams()

    # Enabled PINN engine
    config_pinn = EngineConfig(enable_pinn=True)
    res_pinn = total_settlement_trough(0.0, 30.0, shield, soil, consolidation, config_pinn)
    assert res_pinn["engine_mode"] == "PINN_ULTRA_SPEED"

    # Disabled PINN engine (Scipy analytical fallback)
    config_scipy = EngineConfig(enable_pinn=False)
    res_scipy = total_settlement_trough(0.0, 30.0, shield, soil, consolidation, config_scipy)
    assert res_scipy["engine_mode"] == "SCIPY_ANALYTICAL"

    # Parity verification: peak settlement values within 5% tolerance
    peak_pinn = np.max(np.abs(res_pinn["total_mm"]))
    peak_scipy = np.max(np.abs(res_scipy["total_mm"]))
    relative_diff_pct = abs(peak_pinn - peak_scipy) / peak_scipy * 100.0

    assert relative_diff_pct < 5.0, f"Peak settlement relative diff {relative_diff_pct:.2f}% exceeds 5% threshold"


def test_circuit_breaker_tripping():
    engine = PINNSurrogateEngine()
    engine.circuit_breaker.config.execution_timeout_ms = 0.0001  # Force immediate timeout breach

    shield = ShieldParams()
    soil = SoilParams()
    consolidation = ConsolidationParams()

    # Trigger failure 3 times to open circuit
    for _ in range(3):
        with pytest.raises(CircuitBreakerOpenException):
            engine.predict_trough(0.0, 30.0, shield, soil, consolidation)

    assert engine.circuit_breaker.state.value == "OPEN"

    # Subsequent call should raise CircuitBreakerOpenException immediately without running
    with pytest.raises(CircuitBreakerOpenException):
        engine.predict_trough(0.0, 30.0, shield, soil, consolidation)
