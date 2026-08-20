"""Application settings, loaded from the environment (optionally via .env)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    mongodb_uri: str
    mongodb_db: str
    collection: str

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            mongodb_uri=os.environ.get("MONGODB_URI", "mongodb://localhost:27017"),
            mongodb_db=os.environ.get("MONGODB_DB", "survey_demo"),
            collection=os.environ.get("MONGODB_COLLECTION", "responses"),
        )
