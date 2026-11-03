"""Smoke and unit tests for bms.simulation helpers, the CLI and the dataset loaders.

Offline only: loaders are pointed at an empty directory so they fall back to
the seeded synthetic generators; nothing is downloaded.
"""
from __future__ import annotations

import pytest

from bms import simulation
from bms.datasets import loaders
from bms.datasets.synthetic import DATASET_REGISTRY
from bms.datasets.validation import validate_bms_model
from bms.vehicles import TWO_WHEELER


class TestHelpers:
    def test_soh_marker(self):
        assert simulation._soh_marker(95.0, 80.0, 70.0) == ""
        assert simulation._soh_marker(75.0, 80.0, 70.0) == "~"
        assert simulation._soh_marker(65.0, 80.0, 70.0) == "!"

    def test_soh_status(self):
        assert simulation._soh_status(95.0, 80.0, 70.0) == "OK"
        assert simulation._soh_status(75.0, 80.0, 70.0) == "WARNING"
        assert simulation._soh_status(65.0, 80.0, 70.0) == "CRITICAL"

    def test_degradation_point_linear_fade(self):
        soh_q, q_usable, r0_aged, soh_r, dr0 = simulation._degradation_point(100, 10.0, 2.0, 0.001, 0.001)
        assert soh_q == pytest.approx(90.0)
        assert q_usable == pytest.approx(9.0)
        assert r0_aged == pytest.approx(2.2)
        assert dr0 == pytest.approx(10.0)
        assert soh_r == pytest.approx(100 / 1.1)

    def test_degradation_history_rows(self, capsys):
        hist = simulation.simulate_degradation(TWO_WHEELER, n_cycles=50, print_every=25)
        assert [h["cycle"] for h in hist] == [1, 25, 50]
        assert "DEGRADATION SIMULATION" in capsys.readouterr().out


class TestCli:
    @pytest.mark.parametrize("flag,banner", [
        ("--degradation", "DEGRADATION SIMULATION"),
        ("--driving", "DRIVING CONDITIONS DEGRADATION"),
        ("--manufacturers", "MANUFACTURER BMS COMPARISON"),
        ("--datasets", "BMS MODEL VALIDATION REPORT"),
    ])
    def test_mode_flags_print_banner(self, flag, banner, capsys):
        simulation.main([flag])
        out = capsys.readouterr().out
        assert "BMS MULTI-VEHICLE CAPABILITY COMPARISON" in out
        assert banner in out

    def test_mode_priority_degradation_first(self, capsys):
        simulation.main(["--degradation", "--driving"])
        out = capsys.readouterr().out
        assert "DEGRADATION SIMULATION" in out and "DRIVING CONDITIONS" not in out

    def test_unknown_vehicle_rejected(self):
        with pytest.raises(SystemExit):
            simulation.main(["--vehicle", "nope"])


class TestLoaders:
    def test_every_spec_falls_back_to_synthetic(self, tmp_path, capsys):
        for spec in loaders.LOADER_SPECS.values():
            df = loaders._load(spec, str(tmp_path))
            assert len(df) > 0
        assert capsys.readouterr().out.count("using synthetic") == len(loaders.LOADER_SPECS)

    def test_reads_first_csv_when_present(self, tmp_path, capsys):
        sub = tmp_path / "nested"
        sub.mkdir()
        (sub / "a.csv").write_text("x,y\n1,2\n3,4\n")
        df = loaders.load_nasa(str(tmp_path))
        assert list(df.columns) == ["x", "y"] and len(df) == 2
        assert "loaded real data" in capsys.readouterr().out

    def test_loader_specs_cover_synthetic_registry(self):
        assert len(loaders.LOADER_SPECS) == len(DATASET_REGISTRY)


class TestValidationRunner:
    def test_only_present_datasets_are_validated(self):
        data = {"degradation": DATASET_REGISTRY["degradation"]()}
        assert list(validate_bms_model(data)) == ["degradation_model"]
        assert validate_bms_model({}) == {}


def test_simulation_package_reexports_old_names():
    for name in ("simulate_two_wheeler", "simulate_four_wheeler_retrofit", "simulate_electric_bus",
                 "simulate_degradation", "simulate_cold_temperature", "simulate_driving_degradation",
                 "simulate_manufacturer_comparison", "print_comparison_table", "main", "VEHICLE_MAP",
                 "_simulate_charge_discharge", "_soh_marker", "_soh_status", "_degradation_point", "_plot"):
        assert hasattr(simulation, name), name
