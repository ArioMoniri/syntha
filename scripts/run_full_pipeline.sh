#!/usr/bin/env bash
# Run the full pipeline for both cohorts.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

export PYTHONPATH="$REPO_ROOT/src:${PYTHONPATH:-}"

N="${N:-1000}"
SEED="${SEED:-42}"

for cohort in strict tolerant; do
    input="data/raw/pristine_${cohort}_episodes.csv"
    output="output/${cohort}"
    if [[ ! -f "$input" ]]; then
        echo "✗ missing $input — run scripts/ingest_csvs.sh first" >&2
        continue
    fi
    echo "▶ generating $N $cohort episodes …"
    python3 -m syntha.cli generate \
        --input "$input" --output "$output" \
        --n "$N" --cohort "$cohort" --seed "$SEED"
done
