# EV battery-management-system (BMS) simulation

A pure-Python/NumPy simulation of an electric-vehicle battery-management system: a 2-RC Thevenin cell model,
an Extended-Kalman-Filter state-of-charge (SOC) estimator, state-of-health (SOH) tracking, passive cell
balancing, power derating, thermal management and a supervisory state machine, wired together as a pack
controller. It is aimed at students and engineers who want a readable reference BMS and a way to compare
vehicle classes and chemistries. It prints console tables and (optionally) a comparison plot; there is no UI.

> Status: research-only snapshot (educational use; not safety-certified, not for real battery packs).
> The accelerated degradation figures are demonstrations, not calibrated life predictions. Validation runs
> on seeded synthetic data shaped like six Kaggle datasets; the real Kaggle/NASA data is **not** hosted here.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/herrrickshaw/ev-battery-management-sim/blob/main/notebooks/colab_test.ipynb)
&nbsp; New to AI-assisted exploration of a repo? See [HOW_TO_USE_WITH_AI.md](HOW_TO_USE_WITH_AI.md).

## What it does
- Simulates a pack step by step (`BMSController.step`): per-cell 2-RC voltage model, EKF SOC, SOH, balancing, power limits, fan/heater control and a supervisor with fault codes (over/under voltage, over/under temperature, over-current, isolation) and driver alerts.
- Ships eight chemistry profiles (`LFP`, `PbA`, `NMC`, `Na-Ion`, `LMFP`, `LTO`, `Li-S`, `SS-NMC`) and four vehicle presets (`2W` 15S LFP scooter, `4W_RETRO` 36S lead-acid retrofit, `4W_MODERN`, `BUS` 128S2P LFP).
- Runs CC-CV charge / constant-current discharge scenarios, an analytical degradation sweep, a cold-temperature discharge sweep (+25 to -30 C) and a driving-style SOH projection (6 profiles, 10 years).
- Compares Ather 450X, Ola S1 Pro, Tesla Model 3 SR and BYD Han EV pack specs and projected SOH.
- Validates the models against synthetic stand-ins for six Kaggle battery datasets (EKF SOC RMSE, capacity-fade fit, voltage RMSE, RUL error, multi-module health detection); real CSVs are used automatically if you download them.
- Includes a NASA battery-life notebook that turns the original MATLAB `.mat` files into CSVs.

## Quick start
```bash
git clone https://github.com/herrrickshaw/ev-battery-management-sim.git
cd ev-battery-management-sim
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"          # numpy, pandas, pytest, ruff; add ".[plots]" for --plot
python -m bms.simulation --degradation
```
Other modes of the same CLI (`python -m bms.simulation ...`):

| Flag | What it runs |
|---|---|
| *(none)* | capability table, then the 2W, 4W_RETRO and BUS charge/discharge runs (the retrofit run simulates 8 h of charging, so it takes a while) |
| `--vehicle {2W,4W_RETRO,BUS}` | one vehicle only |
| `--plot` | with the default all-vehicle run, save `reports/bms_multi_vehicle.png` (needs matplotlib) |
| `--degradation` / `--cold` / `--driving` | lifecycle sweeps for the 2W and bus packs |
| `--manufacturers` | Ather / Ola / Tesla / BYD comparison |
| `--datasets` | generate synthetic datasets and print the validation report |

Mode flags (`--degradation`, `--cold`, `--driving`, `--manufacturers`, `--datasets`) are checked in that order and the first one set wins.

## How it works
```
BMSController.step(current, dt)
  per cell : cell_model (2-RC) -> soc_estimator (EKF) ; thermal ; cell_balancer
  pack     : soh_estimator -> power_limits -> supervisor (state machine) -> BMSPackState
```
| Stage | Module |
|---|---|
| Parameters (cell, pack, EKF, OCV-SOC table) | `bms/config.py` |
| Equivalent-circuit cell model | `bms/cell_model.py` |
| EKF SOC estimation | `bms/soc_estimator.py` |
| Capacity / resistance SOH | `bms/soh_estimator.py` |
| Passive balancing | `bms/cell_balancer.py` |
| Charge/discharge limits (SOC, temperature, SOH derating) | `bms/power_limits.py` |
| PWM fan / heater control | `bms/thermal.py` |
| State machine: INIT, IDLE, PRE_CHARGE, CHARGING_CC/CV/FLOAT, DISCHARGING, BALANCING, FAULT, SHUTDOWN | `bms/supervisor.py` |
| Chemistry / vehicle / manufacturer / driving presets | `bms/chemistries.py`, `vehicles.py`, `manufacturer_profiles.py`, `driving_profiles.py` |
| Pack controller | `bms/bms_controller.py` |
| Scenarios and CLI | `bms/simulation.py` |
| Synthetic generators, loaders, validation | `bms/datasets/` |

Design notes: the simulation functions return plain data (histories, dicts) and print tables separately; dataset
loaders are table-driven (`LOADER_SPECS`) and fall back to the seeded synthetic generator (default seed 42) when a
dataset directory has no CSV, so every command runs offline.

## Repository layout
| Path | Purpose |
|---|---|
| `bms/` | the simulation package (modules above) |
| `bms/datasets/` | `synthetic.py` (six seeded generators), `loaders.py` (real CSV or synthetic), `validation.py` (metrics and report) |
| `tests/` | `test_bms.py` unit tests; `test_golden.py` bit-identical seeded regression tests; `test_simulation_cli.py` CLI/loader tests |
| `nasa-battery-life-prediction-dataset-cleaning.ipynb` | NASA `.mat` to CSV notebook (outputs kept as published) |
| `notebooks/colab_test.ipynb` | Colab smoke test |
| `scripts/fetch_kaggle_data.sh` | download the six Kaggle datasets (`--verify` checks them against the manifest) |
| `download_kaggle_datasets.sh`, `fix_and_push_kaggle.sh` | older helpers, kept for compatibility (see Limitations) |
| `data/` | `kaggle_manifest.csv` (path, git blob SHA-1, size of the 7,579 files once hosted here); `data/kaggle/` is gitignored |

## Data sources
| Source | What is taken | Access route | Licence / caveat |
|---|---|---|---|
| [NASA battery dataset](https://www.kaggle.com/datasets/patrickfleith/nasa-battery-dataset) | 18650 cell cycling data | `scripts/fetch_kaggle_data.sh` into `data/kaggle/nasa` | Kaggle terms; not redistributed here |
| [Li-ion degradation](https://www.kaggle.com/datasets/programmer3/lithium-ion-battery-degradation-dataset) | cycle-level SOH, capacity, resistance | `data/kaggle/degradation` | as above |
| [EV battery charging](https://www.kaggle.com/datasets/ziya07/ev-battery-charging-data) | charging sessions | `data/kaggle/ev_charging` | as above |
| [Battery RUL](https://www.kaggle.com/datasets/ignaciovinuales/battery-remaining-useful-life-rul) | RUL feature set | `data/kaggle/rul` | as above |
| [BMS v2.1](https://www.kaggle.com/datasets/akhileshdkapse/version21-bms-dataset) | per-cell telemetry | `data/kaggle/bms_v21` | as above |
| [Synthetic distributed BMS](https://www.kaggle.com/datasets/micamadi/synthetic-distributed-battery-management-system) | multi-module sensor streams | `data/kaggle/dist_bms` | as above |

Datasets were in-repo until 2026-07-22 (560 MB) and are now referenced at source. Kaggle data is mutable, so
`--verify` flags changed files as a signal to review.

## Configuration
No environment variables. Cell, pack and EKF parameters live in `bms/config.py` (`DEFAULT_CELL`, `DEFAULT_PACK`,
`DEFAULT_EKF`) and in the per-chemistry / per-vehicle profiles. Downloading real data needs a Kaggle API token
(`~/.kaggle/kaggle.json`), which stays on your machine and is never committed.

## Testing
```bash
pytest -q          # 136 tests
ruff check .
```
`tests/test_golden.py` re-runs seeded scenarios and compares SHA-256 fingerprints with values captured from the
pre-refactor code. Exact bit-identity is asserted on macOS arm64 (where they were captured); on other platforms
set `BMS_GOLDEN_STRICT=1` to force it.

## Limitations and known issues
- Models and parameters are simplified (linear capacity fade, empirical R0 growth); degradation demos are accelerated about 10x and are not life predictions.
- Validation numbers come from synthetic data unless you download the Kaggle CSVs; they show internal consistency, not field accuracy.
- `fix_and_push_kaggle.sh` fetches, checks out a fixed historical branch name and pushes; do not run it without reading it.
- The Colab notebook looks for `requirements.txt`, which does not exist (it falls through to `pyproject.toml`).
- `--vehicle 4W_RETRO` and the default run simulate many hours of 1-second steps and are slow.
- Python 3.9+ is declared; CI targets 3.9 and 3.12.

## Related repositories
Sibling BMS projects in the same account: [bms-battery-management](https://github.com/herrrickshaw/bms-battery-management)
and [cell-guardian](https://github.com/herrrickshaw/cell-guardian). They are separate codebases; nothing is shared.

## Licence
No licence file yet; all rights reserved. The NASA notebook derives from a public Kaggle notebook whose licence has not been checked.
