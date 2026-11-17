"""Cold-temperature discharge sweep: power-limit blocking and under-temperature faults."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..vehicles import VehicleProfile, make_bms_controller


@dataclass
class _ColdRun:
    """Raw (unrounded) outcome of one constant-current discharge at a fixed ambient temperature."""

    t_peak: float
    soc_final: float
    ah_out: float
    discharge_blocked: bool
    charge_blocked: bool
    fault: str


def _run_cold_discharge(profile: VehicleProfile, t_amb: float, discharge_current: float,
                        max_discharge_s: int, soc_init: float) -> _ColdRun:
    """Discharge at `discharge_current` [A] from `soc_init` with the pack at `t_amb` [°C]."""
    bms = make_bms_controller(profile, soc_init=soc_init, ambient_temp_c=t_amb)
    t_peak = t_amb
    fault_str = "-"
    ah_out = 0.0
    soc_final = soc_init
    dis_blocked = False
    chg_blocked = False

    for tick in range(max_discharge_s):
        state = bms.step(
            current=discharge_current, dt=1.0,
            discharge_requested=True,
        )
        t_peak = max(t_peak, state.pack_temp_max_c)

        # Check power limits at first discharging step
        if tick == 7:  # after INIT+PRECHARGE settle
            if state.power_limits.i_max_discharge < 1.0:
                dis_blocked = True
            if state.power_limits.i_max_charge > -1.0:
                chg_blocked = True

        if state.fault_active:
            fault_str = state.fault_description
            soc_final = state.pack_soc_mean
            ah_out += discharge_current / 3600.0
            break

        if state.pack_soc_mean <= 0.05:
            soc_final = state.pack_soc_mean
            ah_out += discharge_current / 3600.0
            break

        soc_final = state.pack_soc_mean
        ah_out += discharge_current / 3600.0

    return _ColdRun(t_peak, soc_final, ah_out, dis_blocked, chg_blocked, fault_str)


def simulate_cold_temperature(
    profile: VehicleProfile,
    ambient_temps_c: Optional[List[float]] = None,
    discharge_current: Optional[float] = None,
    max_discharge_s: int = 1800,
    soc_init: float = 0.80,
) -> dict:
    """
    Compare discharge performance and fault behavior at different ambient temperatures.

    Shows three key cold-temperature effects:
    1. Reduced power limits (PowerLimitsCalculator blocks charge/discharge below t_min).
    2. Increased cell resistance at low temperatures (cell model thermal derating).
    3. BMS fault when temperature is below t_min_discharge (UNDER_TEMPERATURE).

    Parameters
    ----------
    profile : VehicleProfile
        Pack to test.
    ambient_temps_c : list[float]
        Ambient temperatures to sweep (°C).  Default: [25, 5, -10, -20, -30].
    discharge_current : float
        Pack discharge current [A].  Default: 30% of max discharge current.
    max_discharge_s : int
        Maximum simulation duration per temperature [s].
    soc_init : float
        Initial SOC for all runs.

    Returns
    -------
    dict  keyed by ambient temperature.
    """
    if ambient_temps_c is None:
        ambient_temps_c = [25.0, 5.0, -10.0, -20.0, -30.0]
    if discharge_current is None:
        discharge_current = profile.cell_config.i_max_discharge * profile.n_cells_parallel * 0.30

    cell = profile.cell_config
    t_min_dis = cell.t_min_discharge
    t_min_chg = cell.t_min_charge

    print(f"\n{'='*80}")
    print(f"  COLD TEMPERATURE SIMULATION — {profile.name}")
    print(f"  Chemistry: {profile.chemistry.symbol}  |  I_discharge={discharge_current:.0f} A  |  SOC_init={soc_init*100:.0f}%")
    print(f"  t_min_discharge={t_min_dis}°C  |  t_min_charge={t_min_chg}°C")
    print(f"{'='*80}")

    headers = ["T_amb(°C)", "T_start(°C)", "T_peak(°C)", "SOC_f%", "Ah_out",
               "DchgBlocked", "ChgBlocked", "Fault"]
    print(f"  {'|'.join(f'{h:>11}' for h in headers)}")
    print("  " + "-" * (12 * len(headers)))

    results = {}

    for t_amb in ambient_temps_c:
        run = _run_cold_discharge(profile, t_amb, discharge_current, max_discharge_s, soc_init)
        t_start = t_amb
        t_peak, fault_str, ah_out = run.t_peak, run.fault, run.ah_out
        soc_final = run.soc_final
        dis_blocked, chg_blocked = run.discharge_blocked, run.charge_blocked

        cols = [
            f"{t_amb:>11.1f}",
            f"{t_start:>11.1f}",
            f"{t_peak:>11.1f}",
            f"{soc_final*100:>11.1f}",
            f"{ah_out:>11.1f}",
            f"{'YES' if dis_blocked else 'no':>11}",
            f"{'YES' if chg_blocked else 'no':>11}",
            f"{fault_str:>11}",
        ]
        print("  " + "|".join(cols))

        results[t_amb] = {
            "t_amb_c": t_amb,
            "t_peak_c": round(t_peak, 1),
            "soc_final": round(soc_final, 3),
            "ah_out": round(ah_out, 1),
            "discharge_blocked": dis_blocked,
            "charge_blocked": chg_blocked,
            "fault": fault_str,
        }

    print(f"\n  Note: BMS faults at cell T < {t_min_dis}°C (discharge) / T < {t_min_chg}°C (charge).")
    print("  'DchgBlocked': PowerLimits sets i_max_discharge=0 at t_min_discharge threshold.")
    print("  'ChgBlocked' : PowerLimits sets i_max_charge=0 at t_min_charge threshold.")
    print(f"  Resistance increases ~0.5%/°C below t_nominal={cell.t_nominal}°C → more voltage sag.\n")

    return results
