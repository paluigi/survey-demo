"""Pydantic models for survey submissions, filters and aggregate statistics."""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from urllib.parse import urlencode

from pydantic import BaseModel, Field, field_validator

from survey.countries import COUNTRY_BY_CODE


class AgeBand(enum.StrEnum):
    AGE_18_24 = "18-24"
    AGE_25_34 = "25-34"
    AGE_35_44 = "35-44"
    AGE_45_54 = "45-54"
    AGE_55_64 = "55-64"
    AGE_65_PLUS = "65+"


class Gender(enum.StrEnum):
    FEMALE = "female"
    MALE = "male"
    NON_BINARY = "non-binary"
    PREFER_NOT_TO_SAY = "prefer-not-to-say"


class EducationLevel(enum.StrEnum):
    SECONDARY = "secondary"
    BACHELOR = "bachelor"
    MASTER = "master"
    DOCTORATE = "doctorate"
    OTHER = "other"


def _clean_country_codes(value: list[str]) -> list[str]:
    seen: list[str] = []
    for code in value:
        cleaned = code.strip().upper()
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return seen


class SurveySubmission(BaseModel):
    """One respondent's answers, exactly as persisted in MongoDB."""

    age_band: AgeBand
    gender: Gender
    education: EducationLevel | None = None
    residence_country: str | None = None
    home_country: str | None = None
    visited: list[str] = Field(default_factory=list)
    wishlist: list[str] = Field(default_factory=list)
    favourite: str | None = None
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("visited", "wishlist")
    @classmethod
    def _valid_country_list(cls, value: list[str]) -> list[str]:
        codes = _clean_country_codes(value)
        unknown = [c for c in codes if c not in COUNTRY_BY_CODE]
        if unknown:
            raise ValueError(f"unknown country code(s): {', '.join(unknown)}")
        return codes

    @field_validator("residence_country", "home_country", "favourite")
    @classmethod
    def _valid_optional_country(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        code = value.strip().upper()
        if code not in COUNTRY_BY_CODE:
            raise ValueError(f"unknown country code: {code}")
        return code

    @field_validator("favourite")
    @classmethod
    def _favourite_must_be_visited(cls, value: str | None, info) -> str | None:
        if value is not None:
            visited = info.data.get("visited") or []
            if value not in visited:
                raise ValueError("favourite country must be one of the countries you have visited")
        return value


class SurveyFilters(BaseModel):
    """Demographic filters applied on the results page (all optional)."""

    age_band: AgeBand | None = None
    gender: Gender | None = None
    education: EducationLevel | None = None
    residence_country: str | None = None
    home_country: str | None = None

    def to_mongo(self) -> dict:
        match: dict = {}
        for field in ("age_band", "gender", "education"):
            value = getattr(self, field)
            if value is not None:
                match[field] = value.value
        for field in ("residence_country", "home_country"):
            value = getattr(self, field)
            if value is not None:
                match[field] = value
        return match

    @property
    def query_string(self) -> str:
        params = {
            key: value.value if isinstance(value := getattr(self, key), enum.Enum) else value
            for key in ("age_band", "gender", "education", "residence_country", "home_country")
            if getattr(self, key) is not None
        }
        return urlencode(params)

    @property
    def is_active(self) -> bool:
        return any(
            getattr(self, key) is not None
            for key in ("age_band", "gender", "education", "residence_country", "home_country")
        )


class CountryRow(BaseModel):
    """Numeric results for one country (the table row)."""

    code: str
    name: str
    visited: int = 0
    want: int = 0
    favourite: int = 0


class SurveyStats(BaseModel):
    """Aggregated counts for the current filter selection."""

    total: int = 0
    visited: dict[str, int] = Field(default_factory=dict)
    wishlist: dict[str, int] = Field(default_factory=dict)
    favourite: dict[str, int] = Field(default_factory=dict)

    @property
    def countries_touched(self) -> int:
        codes = set(self.visited) | set(self.wishlist) | set(self.favourite)
        return len(codes)

    @property
    def favourites_cast(self) -> int:
        return sum(self.favourite.values())

    def rows(self) -> list[CountryRow]:
        rows = {
            code: CountryRow(code=code, name=COUNTRY_BY_CODE.get(code, code))
            for code in set(self.visited) | set(self.wishlist) | set(self.favourite)
        }
        for code, count in self.visited.items():
            rows[code].visited = count
        for code, count in self.wishlist.items():
            rows[code].want = count
        for code, count in self.favourite.items():
            rows[code].favourite = count
        return sorted(
            rows.values(),
            key=lambda r: (-r.favourite, -r.visited, -r.want, r.name),
        )

    def row_for(self, code: str) -> CountryRow:
        return CountryRow(
            code=code,
            name=COUNTRY_BY_CODE.get(code, code),
            visited=self.visited.get(code, 0),
            want=self.wishlist.get(code, 0),
            favourite=self.favourite.get(code, 0),
        )
