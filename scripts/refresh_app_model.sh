#!/usr/bin/env bash
# Rebuild the bundled model JSON files consumed by the Tauri app.
#
# 1. Ensure both cohort models exist in output/<cohort>/models/
# 2. Export each as JSON via `syntha export-model`
# 3. Drop the JSONs into app/src/ where vite + main.ts pick them up
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT/src:${PYTHONPATH:-}"

mkdir -p app/src

for cohort in tolerant strict; do
    registry="output/${cohort}/models"
    if [[ ! -d "${registry}/copula_${cohort}" ]]; then
        echo "▶ fitting copula_${cohort} (output/${cohort} missing)"
        python3 -m syntha.cli generate \
            --input "data/raw/pristine_${cohort}_episodes.csv" \
            --output "output/${cohort}" \
            --n 200 --cohort "${cohort}" --seed 42 \
            --fhir-format ndjson > /dev/null
    fi
    echo "▶ exporting model_${cohort}.json"
    python3 -m syntha.cli export-model \
        --registry "${registry}" \
        --name "copula_${cohort}" \
        --output "app/src/model_${cohort}.json" \
        --quantiles 200
done

ls -lh app/src/model_*.json
