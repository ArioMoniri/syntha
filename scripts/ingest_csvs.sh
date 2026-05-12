#!/usr/bin/env bash
# Copy the WhatsApp-shared pristine-episode CSVs into data/raw/.
# Files in data/raw/ are gitignored so this never commits PHI.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$REPO_ROOT/data/raw"
mkdir -p "$DEST"

STRICT_SRC="${STRICT_SRC:-/Users/ario/Library/Containers/net.whatsapp.WhatsApp/Data/tmp/documents/09A0FD33-6436-4E0E-AC5B-63C311B8D261/pristine_strict_episodes.csv}"
TOLERANT_SRC="${TOLERANT_SRC:-/Users/ario/Library/Containers/net.whatsapp.WhatsApp/Data/tmp/documents/87BF5F8B-4A9B-439C-859E-1861B08A1990/pristine_tolerant_episodes.csv}"

for pair in "strict:$STRICT_SRC" "tolerant:$TOLERANT_SRC"; do
    name="${pair%%:*}"
    src="${pair#*:}"
    target="$DEST/pristine_${name}_episodes.csv"
    if [[ -f "$src" ]]; then
        cp -f "$src" "$target"
        echo "✓ ingested $name → $target"
    else
        echo "✗ missing source for $name: $src" >&2
    fi
done
