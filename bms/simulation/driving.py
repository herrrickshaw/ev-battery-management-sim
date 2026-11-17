"""Analytical SOH projection under different real-world driving patterns (no per-second BMS steps)."""
from __future__ import annotations

from ..driving_profiles import (
    DRIVING_PROFILES,
    annual_soh_loss_pct,
    compute_stress_factors,
    efc_per_year,
    months_to_eol,
)
from ..vehicles import VehicleProfile
from .display import _soh_marker


def _print_driving_banner(profile: VehicleProfile, base_rate_per_efc: float,
                          calendar_aging_pct_year: float, warn_pct: float) -> None:
    print(f"\n{'='*86}")
    print(f"  DRIVING CONDITIONS DEGRADATION — {profile.name}")
    print(f"  Chemistry: {profile.chemistry.symbol}  |  "
          f"base_rate={base_rate_per_efc*100:.4f}%/EFC  |  "
          f"calendar_aging={calendar_aging_pct_year}%/yr  |  "
          f"EOL threshold: SOH={warn_pct}%")
    print(f"{'='*86}")


def _print_profile_summary(conditions_list, warn_pct: float, base_rate_per_efc: float,
                           calendar_aging_pct_year: float) -> dict:
    """Print the per-profile stress table; return ``{name: {annual_loss_pct, eol_months, soh_by_year=[]}}``."""
    h = ["Profile", "C-dis", "T(°C)", "DoD%", "FC%", "StressX", "EFC/yr", "EOL(yr)"]
    w = [24, 7, 7, 6, 5, 9, 8, 9]
    fmt = "  " + "  ".join(f"{{:<{x}}}" for x in w)
    print(fmt.format(*h))
    print("  " + "-" * 84)

    results = {}
    for cond in conditions_list:
        f_c, f_T, f_dod, total = compute_stress_factors(cond)
        efcs = efc_per_year(cond)
        loss = annual_soh_loss_pct(base_rate_per_efc, cond, calendar_aging_pct_year)
        eol_m = months_to_eol(warn_pct, base_rate_per_efc, cond, calendar_aging_pct_year)
        eol_str = f"{eol_m/12:.1f}" if eol_m < 120 * 12 else "Never"
        print(fmt.format(
            cond.name[:24],
            f"{cond.avg_discharge_c_rate:.2f}",
            f"{cond.avg_pack_temp_c:.0f}",
            f"{cond.dod_per_trip*100:.0f}%",
            f"{cond.fast_charge_fraction*100:.0f}%",
            f"{total:.3f}×",
            f"{efcs:.0f}",
            eol_str,
        ))
        results[cond.name] = {"annual_loss_pct": loss, "eol_months": eol_m, "soh_by_year": []}
    return results


def _print_soh_over_time(conditions_list, results: dict, simulation_years: int,
                         print_every_years: int, warn_pct: float, crit_pct: float) -> None:
    """Print the SOH-vs-year table and append ``(year, soh)`` points into ``results``."""
    print()
    months_steps = [m for m in range(0, simulation_years * 12 + 1,
                                     max(1, print_every_years * 12))]

    # Header row
    name_width = 6  # "Year"
    col_width = 10
    header_row = f"  {'Year':>{name_width}}" + "".join(
        f"  {c.name[:col_width]:>{col_width}}" for c in conditions_list
    )
    print(header_row)
    print("  " + "-" * (name_width + (col_width + 2) * len(conditions_list) + 2))

    for month in months_steps:
        year = month / 12
        row = f"  {year:>{name_width}.1f}"
        for cond in conditions_list:
            soh = max(0.0, 100.0 - results[cond.name]["annual_loss_pct"] * year)
            results[cond.name]["soh_by_year"].append((year, round(soh, 1)))
            marker = _soh_marker(soh, warn_pct, crit_pct)
            cell = f"{soh:.1f}{marker}"
            row += f"  {cell:>{col_width}}"
        print(row)

    print(f"\n  Legend: ~ = SOH below warning ({warn_pct}%)   ! = SOH below critical ({crit_pct}%)")


def _print_stress_explanation(calendar_aging_pct_year: float) -> None:
    print(f"""
  Stress model (per profile):
    f_C   = (√C_discharge + √C_charge_blend) / 2   [C-rate damage]
    f_T   = 1.5^((T−25)/10) if T≥25°C; 1+0.03×(25−T) if T<25°C  [Arrhenius]
    f_DoD = DoD²                                    [volume-change fatigue]
    eff_rate/EFC = base_rate × f_C × f_T × f_DoD
    annual_loss  = eff_rate × EFC/yr × 100%  +  {calendar_aging_pct_year}% calendar

  Interpretation:
    Aggressive driving degrades the pack faster on all three axes simultaneously:
    high C-rate + hot pack + deep DoD. The cold-climate profile shows that
    sub-zero temperatures add a lithium-plating penalty even at modest C-rates.
""")


def simulate_driving_degradation(
    profile: VehicleProfile,
    conditions_list=None,
    base_rate_per_efc: float = 1e-4,
    calendar_aging_pct_year: float = 0.5,
    simulation_years: int = 10,
    print_every_years: int = 1,
) -> dict:
    """
    Project SOH evolution under different real-world driving patterns.

    Uses an analytical stress model (no per-second BMS steps) combining:
      - C-rate stress     : f_C  = mean(√C_discharge, √C_charge)
      - Temperature stress: f_T  = 1.5^((T-25)/10) above 25°C; +3%/°C below
      - DoD stress        : f_DoD = DoD²
      - Calendar ageing   : fixed term added regardless of cycling

    Parameters
    ----------
    profile : VehicleProfile
        Pack being evaluated (provides chemistry and SOH thresholds).
    conditions_list : list[DrivingConditions] | None
        Profiles to compare.  Default: all 6 built-in profiles.
    base_rate_per_efc : float
        Degradation fraction per EFC at reference (1C, 25°C, 100% DoD).
        Default 1e-4 (0.01%/EFC) — calibrated so city driving ≈ 1.4%/yr.
    calendar_aging_pct_year : float
        Time-dependent SOH loss [%/yr] regardless of cycling (SEI growth).
    simulation_years : int
        Duration to project [years].
    print_every_years : int
        Row frequency in the SOH-over-time table.

    Returns
    -------
    dict  keyed by profile name → list of (year, soh_pct) tuples.
    """
    if conditions_list is None:
        conditions_list = list(DRIVING_PROFILES.values())

    warn_pct = profile.pack_cfg.soh_warning_pct
    crit_pct = profile.pack_cfg.soh_critical_pct

    _print_driving_banner(profile, base_rate_per_efc, calendar_aging_pct_year, warn_pct)
    results = _print_profile_summary(conditions_list, warn_pct, base_rate_per_efc, calendar_aging_pct_year)
    _print_soh_over_time(conditions_list, results, simulation_years, print_every_years, warn_pct, crit_pct)
    _print_stress_explanation(calendar_aging_pct_year)
    return results
