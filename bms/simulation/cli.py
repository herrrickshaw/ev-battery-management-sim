"""``python -m bms.simulation`` command-line interface."""
from __future__ import annotations

import argparse
from typing import List, Optional

from ..vehicles import ELECTRIC_BUS, TWO_WHEELER
from .charge_discharge import simulate_electric_bus, simulate_four_wheeler_retrofit, simulate_two_wheeler
from .cold import simulate_cold_temperature
from .degradation import simulate_degradation
from .driving import simulate_driving_degradation
from .manufacturers import simulate_manufacturer_comparison
from .report import _plot, print_comparison_table

VEHICLE_MAP = {
    "2W": simulate_two_wheeler,
    "4W_RETRO": simulate_four_wheeler_retrofit,
    "BUS": simulate_electric_bus,
}


def _run_degradation_mode() -> None:
    # Show degradation for 2-wheeler (fast, readable output) and bus (large pack)
    simulate_degradation(TWO_WHEELER, n_cycles=300, deg_rate=0.001)
    simulate_degradation(ELECTRIC_BUS, n_cycles=300, deg_rate=0.0005)


def _run_cold_mode() -> None:
    simulate_cold_temperature(TWO_WHEELER)
    simulate_cold_temperature(ELECTRIC_BUS)


def _run_driving_mode() -> None:
    simulate_driving_degradation(TWO_WHEELER, simulation_years=10)
    simulate_driving_degradation(ELECTRIC_BUS, simulation_years=10)


def _run_manufacturers_mode() -> None:
    simulate_manufacturer_comparison(simulation_years=8)


def _run_datasets_mode() -> None:
    from ..datasets import load_all_synthetic, print_validation_report, validate_bms_model
    print("\n  Generating synthetic Kaggle dataset equivalents...")
    datasets = load_all_synthetic()
    print(f"  Datasets ready: {list(datasets.keys())}")
    for name, df in datasets.items():
        print(f"    {name:<25} {len(df):>8,} rows  {list(df.columns)}")
    results = validate_bms_model(datasets)
    print_validation_report(results)


# (argparse attribute, runner) in priority order — the first flag set wins.
_MODE_RUNNERS = [
    ("degradation", _run_degradation_mode),
    ("cold", _run_cold_mode),
    ("driving", _run_driving_mode),
    ("manufacturers", _run_manufacturers_mode),
    ("datasets", _run_datasets_mode),
]


def main(argv: Optional[List[str]] = None) -> None:
    """CLI entry point (``python -m bms.simulation``)."""
    parser = argparse.ArgumentParser(description="BMS multi-vehicle simulation")
    parser.add_argument("--vehicle", choices=list(VEHICLE_MAP.keys()),
                        help="Run only this vehicle class (default: all)")
    parser.add_argument("--plot", action="store_true", help="Save comparison plot")
    parser.add_argument("--degradation", action="store_true",
                        help="Run degradation simulation (capacity/resistance fade over 300 cycles)")
    parser.add_argument("--cold", action="store_true",
                        help="Run cold-temperature discharge sweep (+25 to −30°C)")
    parser.add_argument("--driving", action="store_true",
                        help="Run driving-conditions degradation projection (10-year SOH table)")
    parser.add_argument("--manufacturers", action="store_true",
                        help="Ather / Ola / Tesla / BYD pack specs and degradation comparison")
    parser.add_argument("--datasets", action="store_true",
                        help="Validate BMS model against 6 Kaggle battery datasets")
    args = parser.parse_args(argv)

    print_comparison_table()

    for flag, runner in _MODE_RUNNERS:
        if getattr(args, flag):
            runner()
            return

    if args.vehicle:
        VEHICLE_MAP[args.vehicle]()
    else:
        histories = {}
        histories["2W"]       = simulate_two_wheeler()
        histories["4W_RETRO"] = simulate_four_wheeler_retrofit()
        histories["BUS"]      = simulate_electric_bus()

        if args.plot:
            _plot(histories)


if __name__ == "__main__":
    main()
