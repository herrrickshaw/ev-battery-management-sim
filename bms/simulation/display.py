"""Console-table helpers shared by the scenario modules (pure formatting, no model logic)."""
from __future__ import annotations

from ..bms_controller import BMSPackState
from ..vehicles import VehicleProfile


def _soh_marker(soh: float, warn_pct: float, crit_pct: float) -> str:
    """Table marker for an SOH value [%]: "!" below critical, "~" below warning, else ""."""
    if soh < crit_pct:
        return "!"
    if soh < warn_pct:
        return "~"
    return ""


def _header(profile: VehicleProfile):
    print(f"\n{profile.summary()}")
    cols = ["Time(s)", "State", "SOC%", "V_pack(V)", "I(A)", "T_max(C)", "Fan%", "Alerts"]
    print(f"  {'|'.join(f'{c:>10}' for c in cols)}")
    print("  " + "-" * (11 * len(cols)))


def _row(state: BMSPackState, t: float, interval: int):
    if int(t) % interval != 0:
        return
    alert_str = ",".join(a.name for a in state.alerts) if state.alerts else "-"
    cols = [
        f"{t:>10.0f}",
        f"{state.supervisor.state.name:>10}",
        f"{state.pack_soc_mean*100:>10.1f}",
        f"{state.pack_voltage_v:>10.2f}",
        f"{state.pack_current_a:>10.1f}",
        f"{state.pack_temp_max_c:>10.1f}",
        f"{state.thermal.fan_pwm_pct:>10.1f}",
        f"{alert_str:>10}",
    ]
    print("  " + "|".join(cols))
