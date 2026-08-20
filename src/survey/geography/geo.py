"""World map geometry: loads the vendored GeoJSON and merges response counts."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from survey.models import SurveyStats

GEOJSON_PATH = Path(__file__).resolve().parents[3] / "data" / "world_countries.geojson"


@lru_cache(maxsize=1)
def world_feature_collection() -> dict:
    return json.loads(GEOJSON_PATH.read_text())


def choropleth(stats: SurveyStats) -> dict:
    """The world FeatureCollection with visited/want/favourite counts per country."""
    features = []
    for feature in world_feature_collection()["features"]:
        code = feature["properties"]["iso2"]
        properties = {
            **feature["properties"],
            "visited": stats.visited.get(code, 0),
            "want": stats.wishlist.get(code, 0),
            "favourite": stats.favourite.get(code, 0),
        }
        features.append({**feature, "properties": properties})
    return {"type": "FeatureCollection", "features": features}
