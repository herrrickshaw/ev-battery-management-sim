"""Analytical capacity-fade / resistance-growth projection over N cycles."""
from __future__ import annotations

from typing import List

from ..vehicles import VehicleProfile


def _degradation_point(cycle: int, q_nominal: float, r0_fresh_mohm: float,
                       deg_rate: float, r0_growth_rate: float):
    """Analytical fade after `cycle` cycles -> (soh_q %, usable Ah, aged R0 mΩ, soh_r %, dR0 %)."""
    # Capacity fade: linear (Wöhler-equivalent simplified model)
    soh_q = max(0.0, 100.0 * (1.0 - deg_rate * cycle))
    q_usable = q_nominal * soh_q / 100.0

    # Resistance growth: empirical power-law approximation
    r0_aged = r0_fresh_mohm * (1.0 + r0_growth_rate * cycle)
    soh_r = min(100.0, r0_fresh_mohm / r0_aged * 100.0)
    dr0_pct = (r0_aged - r0_fresh_mohm) / r0_fresh_mohm * 100.0
    return soh_q, q_usable, r0_aged, soh_r, dr0_pct


def _soh_status(soh_q: float, warn_pct: float, crit_pct: float) -> str:
    """Status label for capacity SOH [%]."""
    if soh_q < crit_pct:
        return "CRITICAL"
    if soh_q < warn_pct:
        return "WARNING"
    return "OK"


def simulate_degradation(
    profile: VehicleProfile,
    n_cycles: int = 300,
    deg_rate: float = 0.001,
    r0_growth_rate: float = 0.001,
    print_every: int = 25,
) -> List[dict]:
    """
    Model battery capacity fade and resistance growth over N charge/discharge cycles.

    Uses an analytical degradation model (not a per-second simulation) to quickly
    project SOH evolution across hundreds of cycles.

    Parameters
    ----------
    profile : VehicleProfile
        Vehicle/pack profile (determines nominal capacity and SOH thresholds).
    n_cycles : int
        Number of charge/discharge cycles to simulate.
    deg_rate : float
        Fraction of capacity lost per equivalent full cycle.
        Default 0.001 (0.1 %/cycle ≈ 10× accelerated vs real LFP for demo visibility).
    r0_growth_rate : float
        Fraction of R0 increase per cycle.
        Default 0.001 — R0 doubles by cycle ~1000.
    print_every : int
        Print a table row every N cycles.

    Returns
    -------
    List of dicts with cycle, soh_capacity_pct, capacity_ah, soh_resistance_pct,
    r0_mohm, status.
    """
    cell = profile.cell_config
    q_nominal = cell.nominal_capacity_ah * profile.n_cells_parallel
    r0_fresh_mohm = cell.r0 * 1000.0
    eol_pct = profile.pack_cfg.soh_warning_pct

    print(f"\n{'='*72}")
    print(f"  DEGRADATION SIMULATION — {profile.name}")
    print(f"  {n_cycles} cycles  |  deg_rate={deg_rate*100:.2f}%/cycle  "
          f"|  Q₀={q_nominal:.0f} Ah  |  R₀={r0_fresh_mohm:.2f} mΩ")
    print(f"  (Accelerated model: ~{round(0.02/deg_rate/100):,} real cycles = 1 simulated cycle "
          f"for LFP if actual loss is 0.002%/cycle)")
    print(f"{'='*72}")

    headers = ["Cycle", "SOH-Q%", "Cap(Ah)", "SOH-R%", "R0(mΩ)", "dR0%", "Status"]
    print(f"  {'|'.join(f'{h:>10}' for h in headers)}")
    print("  " + "-" * (11 * len(headers)))

    history: List[dict] = []

    warn_pct = profile.pack_cfg.soh_warning_pct
    crit_pct = profile.pack_cfg.soh_critical_pct

    for cycle in range(1, n_cycles + 1):
        soh_q, q_usable, r0_aged, soh_r, dr0_pct = _degradation_point(
            cycle, q_nominal, r0_fresh_mohm, deg_rate, r0_growth_rate)

        if cycle == 1 or cycle % print_every == 0 or cycle == n_cycles:
            status = _soh_status(soh_q, warn_pct, crit_pct)

            cols = [
                f"{cycle:>10d}",
                f"{soh_q:>10.1f}",
                f"{q_usable:>10.1f}",
                f"{soh_r:>10.1f}",
                f"{r0_aged:>10.2f}",
                f"{dr0_pct:>10.1f}",
                f"{status:>10}",
            ]
            print("  " + "|".join(cols))
            history.append({
                "cycle": cycle,
                "soh_capacity_pct": round(soh_q, 2),
                "capacity_ah": round(q_usable, 2),
                "soh_resistance_pct": round(soh_r, 2),
                "r0_mohm": round(r0_aged, 3),
                "status": status,
            })

    # End-of-life projections
    eol_cycle = int((100.0 - eol_pct) / (deg_rate * 100.0)) if deg_rate > 0 else 99999
    print(f"\n  Capacity model  : SOH_Q = 100% − {deg_rate*100:.3f}% × N")
    print(f"  Resistance model: R0_N  = R0_fresh × (1 + {r0_growth_rate*100:.3f}% × N)")
    print(f"  EOL at SOH={eol_pct}% : ~{eol_cycle:,} cycles")
    print(f"  Final state (N={n_cycles}): SOH={max(0.0, 100-deg_rate*n_cycles*100):.1f}%  "
          f"R0={r0_fresh_mohm*(1+r0_growth_rate*n_cycles):.2f} mΩ\n")

    return history
