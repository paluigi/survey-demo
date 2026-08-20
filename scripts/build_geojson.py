"""One-time generator for data/world_countries.geojson.

Downloads Natural Earth 1:50m admin-0 countries (public domain) and produces a
slim GeoJSON FeatureCollection keyed by ISO 3166-1 alpha-2 codes:

- keeps only ``iso2`` and ``name`` properties,
- resolves Natural Earth's ``-99`` ISO quirks via pycountry (alpha-3) lookups,
- maps Kosovo to its user-assigned code ``XK`` and drops non-ISO entities
  (Northern Cyprus, Somaliland, ...),
- drops Antarctica (huge geometry, not a survey destination),
- rounds coordinates to 3 decimals (~100 m) to shrink the file.

Run with:  uv run --with pycountry python scripts/build_geojson.py
"""

from __future__ import annotations

import json
import tempfile
import urllib.request
from pathlib import Path

import pycountry

SRC = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "master/geojson/ne_50m_admin_0_countries.geojson"
)
OUT = Path(__file__).resolve().parent.parent / "data" / "world_countries.geojson"

# Natural Earth admin units without an ISO 3166-1 alpha-2 code.
DROP_ISO3 = {"ATA", "CYN", "SOL", "PSX", "SAH", "ESB", "KAS", "SDS", "SDE"}
# ISO 3166-1 does not assign Kosovo a code; XK is the de-facto user-assigned one.
FIXUP_ISO3 = {"KOS": "XK"}


def _round_coords(obj: object, ndigits: int = 3) -> object:
    if isinstance(obj, list):
        if obj and isinstance(obj[0], (int, float)):
            return [round(v, ndigits) for v in obj]
        return [_round_coords(item, ndigits) for item in obj]
    return obj


def _iso2(props: dict) -> str | None:
    for key in ("ISO_A2", "ISO_A2_EH"):
        code = props.get(key, "")
        if len(code) == 2 and code.isalpha() and code.isupper():
            return code
    iso3 = props.get("ADM0_A3", "")
    if iso3 in FIXUP_ISO3:
        return FIXUP_ISO3[iso3]
    country = pycountry.countries.get(alpha_3=iso3)
    return country.alpha_2 if country else None


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "ne_50m.geojson"
        print(f"Downloading {SRC} ...")
        urllib.request.urlretrieve(SRC, path)
        data = json.loads(path.read_text())

    features, skipped = [], []
    seen: set[str] = set()
    for feature in data["features"]:
        props = feature["properties"]
        iso3 = props.get("ADM0_A3", "")
        if iso3 in DROP_ISO3:
            skipped.append(f"{iso3} (dropped)")
            continue
        code = _iso2(props)
        if code is None:
            skipped.append(f"{iso3} {props.get('NAME', '')} (no ISO2)")
            continue
        if code in seen:  # keep the first feature for a code (mainland)
            skipped.append(f"{iso3} (duplicate of {code})")
            continue
        seen.add(code)
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "iso2": code,
                    "name": props.get("NAME_LONG") or props.get("NAME", code),
                },
                "geometry": _round_coords(feature["geometry"]),
            }
        )

    features.sort(key=lambda f: f["properties"]["iso2"])
    OUT.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":"))
    )
    print(f"Wrote {len(features)} countries ({OUT.stat().st_size / 1e6:.1f} MB) -> {OUT}")
    if skipped:
        print("Skipped units:", ", ".join(skipped))


if __name__ == "__main__":
    main()
