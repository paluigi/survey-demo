"""Shared FastAPI dependencies for the web layer."""

from __future__ import annotations

import enum

from fastapi import Request

from survey.models import AgeBand, EducationLevel, Gender, SurveyFilters
from survey.repository import SurveyRepository


def get_repository(request: Request) -> SurveyRepository:
    return request.app.state.repository


def _enum_or_none(enum_cls: type[enum.Enum], value: str | None) -> enum.Enum | None:
    if not value:
        return None
    try:
        return enum_cls(value)
    except ValueError:
        return None


def survey_filters(
    age_band: str = "",
    gender: str = "",
    education: str = "",
    residence_country: str = "",
    home_country: str = "",
) -> SurveyFilters:
    """Demographic filters from the query string; blank/unknown values are ignored."""
    return SurveyFilters(
        age_band=_enum_or_none(AgeBand, age_band),  # type: ignore[arg-type]
        gender=_enum_or_none(Gender, gender),  # type: ignore[arg-type]
        education=_enum_or_none(EducationLevel, education),  # type: ignore[arg-type]
        residence_country=residence_country.strip().upper() or None,
        home_country=home_country.strip().upper() or None,
    )
