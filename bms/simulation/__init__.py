"""
BMS multi-vehicle desktop simulation.

Demonstrates the BMS running across three EV classes:
  1. Electric 2-Wheeler  (48V LFP scooter)
  2. Retrofit 4-Wheeler  (72V Lead-Acid, IJAREEIE 2019 paper)
  3. Electric Bus        (409.6V LFP, 150 kW)

Also includes:
  4. Degradation simulation — SOH capacity/resistance fade over N cycles.
  5. Cold-temperature simulation — performance and fault behavior at low temperatures.
  6. Driving conditions simulation — how driving style affects long-term SOH.
  7. Dataset validation — BMS model accuracy against 6 Kaggle battery datasets.

Run:
    python -m bms.simulation                  # all three vehicles
    python -m bms.simulation --vehicle 2W     # single vehicle
    python -m bms.simulation --plot           # save plots to reports/
    python -m bms.simulation --degradation    # capacity fade over 300 cycles
    python -m bms.simulation --cold           # cold temperature sweep
    python -m bms.simulation --driving        # driving conditions degradation
    python -m bms.simulation --manufacturers  # Ather/Ola/Tesla/BYD comparison
    python -m bms.simulation --datasets       # validate against Kaggle datasets


Package layout (every old ``bms.simulation.<name>`` import still works):
    display.py          console-table helpers
    charge_discharge.py CC-CV charge / discharge scenarios per vehicle class
    degradation.py      analytical cycle-fade projection
    cold.py             cold-temperature sweep
    driving.py          driving-style SOH projection
    manufacturers.py    Ather/Ola/Tesla/BYD comparison
    report.py           capability table and plot
    cli.py              argparse entry point
"""

from __future__ import annotations

from .charge_discharge import (
    _simulate_charge_discharge,
    simulate_electric_bus,
    simulate_four_wheeler_retrofit,
    simulate_two_wheeler,
)
from .cli import VEHICLE_MAP, main
from .cold import simulate_cold_temperature
from .degradation import _degradation_point, _soh_status, simulate_degradation
from .display import _header, _row, _soh_marker
from .driving import simulate_driving_degradation
from .manufacturers import simulate_manufacturer_comparison
from .report import _plot, print_comparison_table

__all__ = [
    "VEHICLE_MAP",
    "main",
    "print_comparison_table",
    "simulate_cold_temperature",
    "simulate_degradation",
    "simulate_driving_degradation",
    "simulate_electric_bus",
    "simulate_four_wheeler_retrofit",
    "simulate_manufacturer_comparison",
    "simulate_two_wheeler",
]
