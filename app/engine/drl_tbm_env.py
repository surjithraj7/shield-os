"""
Deep Reinforcement Learning (DRL) Environment for Autonomous TBM Parameter Optimization
======================================================================================
Custom Gymnasium Environment (TBMAutoDriveEnv) implementing continuous action space control
(Thrust Rate, Cutterhead RPM, Screw Conveyor Speed) with a multi-objective reward function balancing
advance speed, cutter tool wear, energy efficiency, EPB pressure safety, and surface settlement variance.
"""

from __future__ import annotations

import math
import numpy as np
try:
    import gymnasium as gym
    from gymnasium import spaces
    HAS_GYMNASIUM = True
except ImportError:
    HAS_GYMNASIUM = False
    class gym:
        Env = object
    class spaces:
        class Box:
            def __init__(self, low, high, shape=None, dtype=None): pass

import numpy as np
from typing import Dict, Any, Tuple, Optional


class TBMAutoDriveEnv(gym.Env):
    """
    Gymnasium Environment for Closed-Loop TBM Autonomous Advance Control.
    
    State Space (S in R^10):
      0: Cutterhead Torque [kNm] (0.0 - 5000.0)
      1: Penetration Rate [mm/rev] (0.0 - 25.0)
      2: EPB Earth Pressure Balance [kPa] (50.0 - 600.0)
      3: Soil Elasticity Modulus E [MPa] (5.0 - 150.0)
      4: Cutterhead Vibration Amplitude [mm/s] (0.0 - 50.0)
      5: Vibration Peak Frequency [Hz] (0.0 - 200.0)
      6: Grout Injection Pressure [MPa] (0.5 - 5.0)
      7: Earth Chamber Fill Ratio alpha (0.5 - 1.2)
      8: Cutterhead RPM N [rpm] (0.5 - 4.0)
      9: Total Jack Cylinder Thrust F [kN] (2000.0 - 40000.0)

    Action Space (A in [-1, 1]^3):
      a[0]: Delta Thrust Rate [-1.0, 1.0] -> Mapped to Thrust Force [5000, 35000] kN
      a[1]: Cutterhead RPM [-1.0, 1.0] -> Mapped to [0.8, 3.5] RPM
      a[2]: Screw Conveyor Speed [-1.0, 1.0] -> Mapped to [5.0, 25.0] RPM
    """

    metadata = {"render_modes": ["human"]}

    def __init__(self, target_settlement_limit_mm: float = 12.0):
        super().__init__()
        self.target_settlement_limit_mm = target_settlement_limit_mm

        # 1. Define Observation Space (Normalized Bounds)
        self.low_obs = np.array([0.0, 0.0, 50.0, 5.0, 0.0, 0.0, 0.5, 0.5, 0.5, 2000.0], dtype=np.float32)
        self.high_obs = np.array([5000.0, 25.0, 600.0, 150.0, 50.0, 200.0, 5.0, 1.2, 4.0, 40000.0], dtype=np.float32)
        self.observation_space = spaces.Box(low=self.low_obs, high=self.high_obs, dtype=np.float32)

        # 2. Continuous Action Space A in [-1, 1]^3
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(3,), dtype=np.float32)

        # Weights for Multi-Objective Reward Function
        self.w_advance = 2.5
        self.w_wear = 1.0
        self.w_energy = 0.8
        self.w_settlement = 3.0
        self.w_safety = 5.0

        # State Variables
        self.state = None
        self.current_step = 0
        self.max_steps = 200

    def reset(self, *, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed)
        self.current_step = 0

        # Initial nominal operational state
        self.state = np.array([
            2200.0,  # Torque (kNm)
            8.5,     # Penetration Rate (mm/rev)
            260.0,   # EPB Pressure (kPa)
            35.0,    # Soil Elasticity E (MPa)
            4.2,     # Vibration Amplitude (mm/s)
            45.0,    # Peak Frequency (Hz)
            2.5,     # Grout Pressure (MPa)
            0.92,    # Chamber Fill Ratio
            2.2,     # Cutterhead RPM
            14000.0  # Thrust Force (kN)
        ], dtype=np.float32)

        return self.state.copy(), {"status": "INITIALIZED"}

    def _denormalize_actions(self, action: np.ndarray) -> Tuple[float, float, float]:
        """Maps continuous actions from [-1, 1] to physical actuator operational ranges."""
        # Thrust: [5000, 35000] kN
        thrust_kn = float(5000.0 + (action[0] + 1.0) * 0.5 * (35000.0 - 5000.0))
        # RPM: [0.8, 3.5] rpm
        rpm = float(0.8 + (action[1] + 1.0) * 0.5 * (3.5 - 0.8))
        # Screw RPM: [5.0, 25.0] rpm
        screw_rpm = float(5.0 + (action[2] + 1.0) * 0.5 * (25.0 - 5.0))
        return thrust_kn, rpm, screw_rpm

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        self.current_step += 1
        thrust_kn, rpm, screw_rpm = self._denormalize_actions(action)

        # 1. Physics Step Simulation
        soil_E = self.state[3]
        
        # Advance Speed (v = Penetration * RPM)
        penetration_rate = max(1.0, min(20.0, (thrust_kn / (soil_E * 500.0)) * 10.0))
        advance_speed_mm_min = penetration_rate * rpm  # mm/min

        # Torque calculation T ~ f(Thrust, Soil_E, RPM)
        torque_knm = max(500.0, min(4800.0, 0.08 * thrust_kn + 300.0 * (rpm ** 0.5) + np.random.normal(0, 25)))

        # EPB Chamber Pressure Balance
        # Pressure increases with thrust and chamber fill ratio, drops with screw conveyor discharge speed
        chamber_fill = max(0.6, min(1.15, self.state[7] + (advance_speed_mm_min * 0.005) - (screw_rpm * 0.008)))
        epb_pressure_kpa = max(80.0, min(550.0, chamber_fill * 280.0 + (thrust_kn / 1000.0) * 2.5 - screw_rpm * 3.0))

        # Vibration Spectra
        vib_amp = max(0.5, min(45.0, 3.0 + (torque_knm / 400.0) * rpm + np.random.normal(0, 0.5)))
        vib_freq = max(10.0, min(180.0, rpm * 20.0 + np.random.normal(0, 2)))

        # Ground Surface Settlement Surrogate calculation
        # Settlement increases if EPB pressure drops below required earth pressure (e.g. 240 kPa)
        pressure_deficit = max(0.0, 240.0 - epb_pressure_kpa)
        surface_settlement_mm = max(1.0, 3.5 + (pressure_deficit ** 1.3) * 0.05 + (advance_speed_mm_min / 50.0) * 1.5)

        # Update Internal State Vector
        self.state = np.array([
            torque_knm,
            penetration_rate,
            epb_pressure_kpa,
            soil_E,
            vib_amp,
            vib_freq,
            self.state[6],  # Grout Pressure
            chamber_fill,
            rpm,
            thrust_kn
        ], dtype=np.float32)

        # 2. Multi-Objective Reward Function Formulation
        # R = w_adv * R_advance - w_wear * R_wear - w_energy * R_energy - w_settle * R_settle - w_safety * R_safety
        
        # (a) Advance Efficiency Component
        r_advance = advance_speed_mm_min / 50.0  # Max target speed 50 mm/min
        
        # (b) Cutter Tool Wear Component (Function of torque, RPM, and high frequency vibration)
        r_wear = (torque_knm * rpm) / (5000.0 * 3.5) + 0.1 * (vib_amp / 50.0) ** 2
        
        # (c) Electrical & Mechanical Energy Power Consumption (P = 2*pi*T*N + F*v)
        p_elec_kw = (2.0 * math.pi * torque_knm * (rpm / 60.0)) + (thrust_kn * (advance_speed_mm_min / 60000.0))
        r_energy = p_elec_kw / 2500.0  # Normalized by 2.5 MW rating
        
        # (d) Surface Settlement Penalty Component
        if surface_settlement_mm > self.target_settlement_limit_mm:
            r_settlement = ((surface_settlement_mm - self.target_settlement_limit_mm) / self.target_settlement_limit_mm) ** 2
        else:
            r_settlement = 0.0

        # (e) EPB Safety Envelope Penalty (Min 180 kPa, Max 450 kPa)
        r_safety = 0.0
        if epb_pressure_kpa < 180.0:
            r_safety += ((180.0 - epb_pressure_kpa) / 180.0) ** 2
        elif epb_pressure_kpa > 450.0:
            r_safety += ((epb_pressure_kpa - 450.0) / 450.0) ** 2

        reward = float(
            self.w_advance * r_advance
            - self.w_wear * r_wear
            - self.w_energy * r_energy
            - self.w_settlement * r_settlement
            - self.w_safety * r_safety
        )

        # Termination & Truncation criteria
        terminated = bool(epb_pressure_kpa < 100.0 or surface_settlement_mm > 25.0)  # Structural risk breach
        truncated = bool(self.current_step >= self.max_steps)

        info = {
            "advance_speed_mm_min": advance_speed_mm_min,
            "surface_settlement_mm": surface_settlement_mm,
            "epb_pressure_kpa": epb_pressure_kpa,
            "power_kw": p_elec_kw,
            "tool_wear_rate": r_wear,
            "terminated_reason": "SAFETY_BREACH" if terminated else None
        }

        return self.state.copy(), reward, terminated, truncated, info
