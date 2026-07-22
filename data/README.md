# data/ — fetched from Kaggle, not hosted here

`data/kaggle/` is **gitignored**. The datasets are referenced from their
original Kaggle sources instead of being hosted in this repo (they were
in-repo until 2026-07-22 — 7,579 files / 560 MB — which bloated every clone
and duplicated data Kaggle already serves).

| Kaggle dataset | Local target |
|---|---|
| [patrickfleith/nasa-battery-dataset](https://www.kaggle.com/datasets/patrickfleith/nasa-battery-dataset) | `data/kaggle/nasa` |
| [programmer3/lithium-ion-battery-degradation-dataset](https://www.kaggle.com/datasets/programmer3/lithium-ion-battery-degradation-dataset) | `data/kaggle/degradation` |
| [ziya07/ev-battery-charging-data](https://www.kaggle.com/datasets/ziya07/ev-battery-charging-data) | `data/kaggle/ev_charging` |
| [ignaciovinuales/battery-remaining-useful-life-rul](https://www.kaggle.com/datasets/ignaciovinuales/battery-remaining-useful-life-rul) | `data/kaggle/rul` |
| [akhileshdkapse/version21-bms-dataset](https://www.kaggle.com/datasets/akhileshdkapse/version21-bms-dataset) | `data/kaggle/bms_v21` |
| [micamadi/synthetic-distributed-battery-management-system](https://www.kaggle.com/datasets/micamadi/synthetic-distributed-battery-management-system) | `data/kaggle/dist_bms` |

## Get the data

```bash
pip install kaggle          # + kaggle.json in ~/.kaggle/
scripts/fetch_kaggle_data.sh
```

## Verify

`data/kaggle_manifest.csv` records the path, git blob SHA-1, and byte size of
every file as of the last in-repo snapshot (2026-07-22). After downloading:

```bash
scripts/fetch_kaggle_data.sh --verify
```

Note: Kaggle datasets are mutable — if an upstream author republishes a
dataset, `--verify` will flag CHANGED files. That is a signal to review, not
necessarily an error.
