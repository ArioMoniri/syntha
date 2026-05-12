#!/usr/bin/env bash
# POST every transaction Bundle in an NDJSON file to a FHIR R4 server.
#
# Defaults to the public HAPI FHIR test server at https://hapi.fhir.org/baseR4
# — a free, anyone-can-write playground operated by the HAPI FHIR project.
# Override with $FHIR_BASE to target your own server.
#
# Usage:
#   bash scripts/post_to_fhir.sh                                # uses examples/sample_output/sample_bundles.ndjson
#   bash scripts/post_to_fhir.sh path/to/bundles.ndjson         # custom file
#   FHIR_BASE=http://localhost:8080/fhir bash scripts/post_to_fhir.sh
#
# Requires: curl, jq (optional, prettier output).
set -euo pipefail

FHIR_BASE="${FHIR_BASE:-https://hapi.fhir.org/baseR4}"
NDJSON="${1:-examples/sample_output/sample_bundles.ndjson}"

if [[ ! -f "$NDJSON" ]]; then
    echo "✗ bundles file not found: $NDJSON" >&2
    exit 1
fi

total=$(wc -l < "$NDJSON" | tr -d ' ')
echo "▶ POSTing $total transaction Bundles → $FHIR_BASE"
n=0
fail=0
while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    n=$((n + 1))
    status=$(curl -sS -o /tmp/syntha_post.json -w "%{http_code}" \
        -X POST "$FHIR_BASE" \
        -H "Content-Type: application/fhir+json" \
        --data "$line" || true)
    if [[ "$status" == "200" || "$status" == "201" ]]; then
        printf "  [%3d/%3d] %s ✓\n" "$n" "$total" "$status"
    else
        printf "  [%3d/%3d] %s ✗\n" "$n" "$total" "$status"
        fail=$((fail + 1))
        if [[ $fail -le 3 ]]; then
            cat /tmp/syntha_post.json | sed 's/^/      /'
        fi
    fi
done < "$NDJSON"

echo "✓ done: $((n - fail))/$n succeeded"
