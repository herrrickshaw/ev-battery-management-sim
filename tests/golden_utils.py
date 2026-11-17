"""Fingerprint helpers for the bit-identical characterisation tests.

``collect()`` runs short, seeded, offline scenarios and reduces every numeric
result to a SHA-256 of its float64 bytes (exact) plus a few repr'd checkpoints
(tolerance-checked).  ``tests/golden_values.py`` holds the values captured from
the pre-refactor code.  No Kaggle/NASA data is read; all inputs are synthetic.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
from typing import Any

import numpy as np
import pandas as pd


def hash_floats(values: Any) -> str:
    """SHA-256 over the float64 bytes of any numeric sequence/array."""
    arr = np.ascontiguousarray(np.asarray(values, dtype=np.float64))
    return hashlib.sha256(arr.tobytes()).hexdigest()


def hash_frame(df: pd.DataFrame) -> str:
    """SHA-256 over column names and every column's values (numeric -> float64 bytes)."""
    h = hashlib.sha256()
    for col in df.columns:
        h.update(str(col).encode())
        s = df[col]
        if pd.api.types.is_numeric_dtype(s):
            h.update(np.ascontiguousarray(s.to_numpy(dtype=np.float64)).tobytes())
        else:
            h.update("\x1f".join(map(str, s.tolist())).encode())
    return h.hexdigest()


def hash_obj(obj: Any) -> str:
    """SHA-256 of ``repr`` for nested dict/list/float results (repr is exact for floats)."""
    return hashlib.sha256(repr(obj).encode()).hexdigest()


def _pack_history(history) -> dict:
    return {
        "n": len(history),
        "soc": hash_floats([s.pack_soc_mean for s in history]),
        "v": hash_floats([s.pack_voltage_v for s in history]),
        "tmax": hash_floats([s.pack_temp_max_c for s in history]),
        "fan": hash_floats([s.thermal.fan_pwm_pct for s in history]),
        "soh": hash_floats([s.soh.soh_capacity_pct for s in history]),
        "last_soc": repr(history[-1].pack_soc_mean),
    }


def collect() -> dict:
    """Run every seeded scenario and return the fingerprint dictionary."""
    from bms.datasets import load_all_synthetic, validate_bms_model
    from bms.simulation import (
        _simulate_charge_discharge,
        simulate_cold_temperature,
        simulate_degradation,
        simulate_driving_degradation,
        simulate_manufacturer_comparison,
    )
    from bms.vehicles import ELECTRIC_BUS, TWO_WHEELER

    out: dict = {}
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink):
        datasets = load_all_synthetic()
        out["datasets"] = {k: hash_frame(v) for k, v in datasets.items()}
        out["validation"] = hash_obj(validate_bms_model(datasets))
        out["degradation_2w"] = hash_obj(simulate_degradation(TWO_WHEELER, n_cycles=300, deg_rate=0.001))
        out["degradation_bus"] = hash_obj(simulate_degradation(ELECTRIC_BUS, n_cycles=60, deg_rate=0.0005))
        out["cold_2w"] = hash_obj(simulate_cold_temperature(TWO_WHEELER, max_discharge_s=120))
        out["driving_2w"] = hash_obj(simulate_driving_degradation(TWO_WHEELER, simulation_years=10))
        out["manufacturers"] = hash_obj(
            {k: (v["annual_loss_pct"], v["eol_months"], v["soh_by_year"])
             for k, v in simulate_manufacturer_comparison(simulation_years=8).items()}
        )
        out["charge_discharge_2w"] = _pack_history(
            _simulate_charge_discharge(TWO_WHEELER, soc_init=0.15, charge_s=90, discharge_s=90,
                                       discharge_current=20.0, print_interval=60)
        )
    out["stdout_sha"] = hashlib.sha256(sink.getvalue().encode()).hexdigest()
    return out
