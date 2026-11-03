"""Per-vehicle CC-CV charge / constant-current discharge scenarios (per-second BMS steps)."""
from __future__ import annotations

from typing import List, Optional

import numpy as np

from ..bms_controller import BMSPackState
from ..vehicles import (
    ELECTRIC_BUS,
    FOUR_WHEELER_RETRO,
    TWO_WHEELER,
    VehicleProfile,
    make_bms_controller,
)
from .display import _header, _row


def _simulate_charge_discharge(
    profile: VehicleProfile,
    soc_init: float = 0.20,
    dt: float = 1.0,
    charge_s: int = 5400,
    discharge_s: int = 3600,
    discharge_current: Optional[float] = None,
    print_interval: int = 600,
) -> List[BMSPackState]:
    """Run a CC-CV charge followed by constant-current discharge."""

    # Slight SOC spread across cells to show balancing
    n = profile.n_cells_series
    spread = 0.02
    socs = [float(np.clip(soc_init + spread * (i / max(n - 1, 1) - 0.5), 0.0, 1.0))
            for i in range(n)]

    bms = make_bms_controller(profile, soc_init=socs, ambient_temp_c=25.0)
    history: List[BMSPackState] = []

    _header(profile)

    # ---- Phase 1: CC-CV Charge ----
    cc_i = profile.cell_config.i_max_charge * profile.n_cells_parallel
    cv_term = abs(profile.cell_config.i_cv_term) * profile.n_cells_parallel
    in_cv = False
    cv_start = 0.0
    t = 0.0

    for tick in range(charge_s):
        t = tick * dt
        if not in_cv:
            charge_current = cc_i
        else:
            decay = np.exp(-(t - cv_start) / 1200.0)
            charge_current = cc_i * decay
            if abs(charge_current) < cv_term:
                break

        state = bms.step(current=charge_current, dt=dt, charge_requested=True)
        history.append(state)
        _row(state, t, print_interval)

        if not in_cv and max(state.cell_voltages_v) >= profile.cell_config.v_max:
            in_cv = True
            cv_start = t
        if state.pack_soc_mean >= 0.95:
            break

    print(f"\n  >> Charge done  SOC={history[-1].pack_soc_mean*100:.1f}%  "
          f"V={history[-1].pack_voltage_v:.1f}V  T={history[-1].pack_temp_max_c:.1f}°C")

    # ---- Phase 2: Balancing at rest ----
    for _ in range(min(300, charge_s)):
        t += dt
        state = bms.step(current=0.0, dt=dt)
        history.append(state)
        if state.balancing.v_spread < 0.003:
            break

    # ---- Phase 3: CC Discharge ----
    if discharge_current is None:
        discharge_current = profile.cell_config.i_max_discharge * profile.n_cells_parallel * 0.5

    for tick in range(discharge_s):
        t += dt
        state = bms.step(current=discharge_current, dt=dt, discharge_requested=True)
        history.append(state)
        _row(state, t, print_interval)
        if state.pack_soc_mean <= 0.05 or state.fault_active:
            break

    last = history[-1]
    print(f"\n  >> Discharge done  SOC={last.pack_soc_mean*100:.1f}%  "
          f"Fault={last.fault_description}  "
          f"SOH={last.soh.soh_capacity_pct:.2f}%  "
          f"Fan={last.thermal.fan_pwm_pct:.0f}%\n")

    return history


# ---------------------------------------------------------------------------
# Per-vehicle simulation functions
# ---------------------------------------------------------------------------

def simulate_two_wheeler(**kwargs) -> List[BMSPackState]:
    """Electric scooter / e-bike: 15S LFP, 48V, 1.5 kW."""
    return _simulate_charge_discharge(
        TWO_WHEELER,
        soc_init=0.15,
        charge_s=3600,
        discharge_s=2400,
        discharge_current=20.0,     # 0.67C — typical scooter load
        print_interval=600,
        **kwargs,
    )


def simulate_four_wheeler_retrofit(**kwargs) -> List[BMSPackState]:
    """
    Retrofit IC→EV car: 36S Lead-Acid, 72V/130Ah, 10 kW BLDC.
    Source: IJAREEIE Vol. 8, Issue 4, April 2019.
    3-stage CC → CV(Topping) → Float charging.
    """
    return _simulate_charge_discharge(
        FOUR_WHEELER_RETRO,
        soc_init=0.30,
        charge_s=28800,             # paper: 8 hours full charge
        discharge_s=10800,          # paper: ~3 hours at normal load
        discharge_current=43.0,     # ~10kW / 72V ≈ 138A → 43A avg
        print_interval=3600,
        **kwargs,
    )


def simulate_electric_bus(**kwargs) -> List[BMSPackState]:
    """Electric bus: 128S2P LFP, 409.6V, 150 kW, 163.8 kWh."""
    return _simulate_charge_discharge(
        ELECTRIC_BUS,
        soc_init=0.20,
        charge_s=7200,
        discharge_s=3600,
        discharge_current=100.0,    # ~41 kW city cruising load (peak is 366 A)
        print_interval=600,
        **kwargs,
    )
