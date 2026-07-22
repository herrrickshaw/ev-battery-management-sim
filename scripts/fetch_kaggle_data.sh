#!/usr/bin/env bash
# Fetch the six Kaggle battery datasets this repo depends on.
#
# The data is deliberately NOT hosted in this repo (it was until 2026-07-22;
# 7,579 files / 560 MB were removed from the tip). The originals live on
# Kaggle — this script downloads them into data/kaggle/ (gitignored).
#
# Prereqs:
#   pip install kaggle
#   kaggle.json (kaggle.com → Account → API Token) in ~/.kaggle/
#
# Usage:
#   scripts/fetch_kaggle_data.sh            # download all six datasets
#   scripts/fetch_kaggle_data.sh --verify   # verify downloads against data/kaggle_manifest.csv
set -euo pipefail
cd "$(dirname "$0")/.."

# slug:target pairs — keep in sync with bms/datasets/loaders.py
DATASETS="
patrickfleith/nasa-battery-dataset:nasa
programmer3/lithium-ion-battery-degradation-dataset:degradation
ziya07/ev-battery-charging-data:ev_charging
ignaciovinuales/battery-remaining-useful-life-rul:rul
akhileshdkapse/version21-bms-dataset:bms_v21
micamadi/synthetic-distributed-battery-management-system:dist_bms
"

if [ "${1:-}" = "--verify" ]; then
  # Recompute git blob hashes and compare against the manifest committed
  # when the data was still hosted in-repo.
  missing=0; changed=0; checked=0
  while IFS=, read -r path sha bytes; do
    [ "$path" = "path" ] && continue
    if [ ! -f "$path" ]; then missing=$((missing+1)); echo "MISSING  $path"; continue; fi
    actual=$(git hash-object "$path")
    checked=$((checked+1))
    [ "$actual" != "$sha" ] && { changed=$((changed+1)); echo "CHANGED  $path"; }
  done < data/kaggle_manifest.csv
  echo "verified: $checked ok, $missing missing, $changed changed"
  [ $missing -eq 0 ] && [ $changed -eq 0 ]
  exit $?
fi

mkdir -p data/kaggle
for pair in $DATASETS; do
  slug=${pair%%:*}; target=${pair##*:}
  echo "==> $slug -> data/kaggle/$target"
  kaggle datasets download "$slug" -p "data/kaggle/$target" --unzip
done
echo "Done. Run 'scripts/fetch_kaggle_data.sh --verify' to check against the manifest."
