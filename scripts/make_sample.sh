#!/usr/bin/env bash
# Generate a small (100-episode) sample output and copy it to
# examples/sample_output/ for committing to the repo.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT/src:${PYTHONPATH:-}"

mkdir -p examples/sample_output

python3 -m syntha.cli generate \
    --input data/raw/pristine_tolerant_episodes.csv \
    --output output/sample \
    --n 100 --cohort tolerant --seed 12345 \
    --fhir-format ndjson

cp output/sample/synthetic_tolerant_episodes.csv examples/sample_output/sample_episodes.csv
cp output/sample/fhir/bundles.ndjson examples/sample_output/sample_bundles.ndjson
cp output/sample/validation_report.json examples/sample_output/sample_validation_report.json
cp output/sample/models/copula_tolerant/card.json examples/sample_output/sample_model_card.json

# Pretty-print the first bundle as a standalone JSON for readability in the repo.
python3 - <<'PY'
import json
with open("examples/sample_output/sample_bundles.ndjson") as f:
    bundle = json.loads(f.readline())
with open("examples/sample_output/sample_bundle_pretty.json", "w") as f:
    json.dump(bundle, f, indent=2, ensure_ascii=False)
PY

echo "✓ sample output written to examples/sample_output/"
ls -lh examples/sample_output/
