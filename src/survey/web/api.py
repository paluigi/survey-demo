"""JSON API endpoints consumed by the frontend JavaScript."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import ORJSONResponse

from survey.geography.geo import choropleth
from survey.models import SurveyFilters, SurveyStats
from survey.repository import SurveyRepository
from survey.web.deps import get_repository, survey_filters

router = APIRouter()


@router.get("/api/map/choropleth", response_class=ORJSONResponse)
async def map_choropleth(
    filters: SurveyFilters = Depends(survey_filters),
    repository: SurveyRepository = Depends(get_repository),
) -> ORJSONResponse:
    """World map geometry with per-country visited/want/favourite counts."""
    stats: SurveyStats = await repository.stats(filters)
    return ORJSONResponse(choropleth(stats))
