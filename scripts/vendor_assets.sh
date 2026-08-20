#!/usr/bin/env bash
# Vendor third-party frontend assets into static/vendor/ with pinned versions.
# Re-run any time you want to bump a version; VENDORED.md records what is shipped.
set -euo pipefail

VENDOR_DIR="$(cd "$(dirname "$0")/../static/vendor" && pwd)"

latest_version() {
    # Resolve the latest stable version of an npm package from the jsDelivr API.
    curl -fsSL "https://data.jsdelivr.com/v1/packages/npm/$1/resolved?specifier=$2" |
        python3 -c 'import json,sys; print(json.load(sys.stdin)["version"])'
}

fetch() { # fetch <url> <dest>
    echo "Fetching $1"
    curl -fsSL "$1" -o "$2"
}

PICO_VER=$(latest_version "@picocss/pico" "2")
HTMX_VER=$(latest_version "htmx.org" "2")
MAPLIBRE_VER=$(latest_version "maplibre-gl" "5")

fetch "https://cdn.jsdelivr.net/npm/@picocss/pico@${PICO_VER}/css/pico.min.css" \
    "$VENDOR_DIR/pico.min.css"
fetch "https://cdn.jsdelivr.net/npm/@picocss/pico@${PICO_VER}/LICENSE.md" \
    "$VENDOR_DIR/pico.LICENSE.md"

fetch "https://cdn.jsdelivr.net/npm/htmx.org@${HTMX_VER}/dist/htmx.min.js" \
    "$VENDOR_DIR/htmx.min.js"
fetch "https://cdn.jsdelivr.net/npm/htmx.org@${HTMX_VER}/LICENSE" \
    "$VENDOR_DIR/htmx.LICENSE"

fetch "https://cdn.jsdelivr.net/npm/maplibre-gl@${MAPLIBRE_VER}/dist/maplibre-gl.js" \
    "$VENDOR_DIR/maplibre-gl.js"
fetch "https://cdn.jsdelivr.net/npm/maplibre-gl@${MAPLIBRE_VER}/dist/maplibre-gl.css" \
    "$VENDOR_DIR/maplibre-gl.css"
fetch "https://cdn.jsdelivr.net/npm/maplibre-gl@${MAPLIBRE_VER}/LICENSE.txt" \
    "$VENDOR_DIR/maplibre-gl.LICENSE.txt"

cat >"$VENDOR_DIR/VENDORED.md" <<EOF
# Vendored frontend assets

| Asset | Package | Version | License |
|---|---|---|---|
| pico.min.css | @picocss/pico | ${PICO_VER} | MIT |
| htmx.min.js | htmx.org | ${HTMX_VER} | BSD 2-Clause |
| maplibre-gl.js/.css | maplibre-gl | ${MAPLIBRE_VER} | BSD 3-Clause |

Downloaded from jsDelivr CDN. Full license texts are stored next to each file.
Regenerate with \`scripts/vendor_assets.sh\`.
EOF

echo "Done: pico ${PICO_VER}, htmx ${HTMX_VER}, maplibre-gl ${MAPLIBRE_VER}"
