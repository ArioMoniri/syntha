#!/usr/bin/env bash
# Build the syntha .dxt for Anthropic Connector directory submission.
#
# Usage: ./mcp/build.sh [version-tag]
#
# Tries Anthropic's official packager first (@anthropic-ai/dxt on npm);
# falls back to a manual zip-based build if that's unavailable.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MCP_DIR="$REPO_ROOT/mcp"
cd "$MCP_DIR"

VERSION="${1:-$(python3 -c 'import json; print(json.load(open("manifest.json"))["version"])')}"
OUT="syntha-${VERSION}.dxt"
echo "▶ building ${OUT} from $MCP_DIR"

# Prefer the official packager.
if command -v npx >/dev/null 2>&1; then
    echo "▶ trying @anthropic-ai/dxt …"
    if npx -y @anthropic-ai/dxt validate manifest.json 2>/dev/null; then
        npx -y @anthropic-ai/dxt pack . "$OUT"
        echo "✓ produced $OUT via official packager"
        ls -lh "$OUT"
        exit 0
    fi
    echo "  (official packager not available or schema mismatch — falling back)"
fi

# Fallback: manual DXT format is a zip of:
#   manifest.json
#   server/ (the Python entry point + any bundled resources)
#   icon.png (optional)
# We bundle the syntha-ehr install pointer rather than the wheel itself —
# Claude Desktop will pip-install the listed package at install time.
echo "▶ manual zip-based build …"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cp manifest.json "$TMP/"
[ -f icon.png ] && cp icon.png "$TMP/"
[ -f icon.svg ] && cp icon.svg "$TMP/"
mkdir -p "$TMP/server"
cat > "$TMP/server/requirements.txt" <<'PY'
syntha-ehr[mcp]>=0.5.10
PY
cat > "$TMP/server/entry.json" <<JSON
{
  "command": "syntha-mcp",
  "args": []
}
JSON

(cd "$TMP" && zip -qr "$OUT" .)
mv "$TMP/$OUT" .
echo "✓ produced $OUT via manual build"
ls -lh "$OUT"
