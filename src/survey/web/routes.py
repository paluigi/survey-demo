"""Full-page routes: survey form and results page."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from survey.countries import COUNTRIES
from survey.models import AgeBand, EducationLevel, Gender, SurveyFilters, SurveyStats
from survey.repository import SurveyRepository
from survey.web.deps import get_repository, survey_filters
from survey.web.templating import build_templates

router = APIRouter()
templates = build_templates()


@router.get("/", response_class=HTMLResponse)
async def survey_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "countries": COUNTRIES,
            "age_bands": list(AgeBand),
            "genders": list(Gender),
            "education_levels": list(EducationLevel),
        },
    )


@router.get("/results", response_class=HTMLResponse)
async def results_page(
    request: Request,
    filters: SurveyFilters = Depends(survey_filters),
    repository: SurveyRepository = Depends(get_repository),
) -> HTMLResponse:
    stats: SurveyStats = await repository.stats(filters)
    # htmx filter changes request the same URL and only want the refreshable
    # region; a direct visit renders the whole page.
    if request.headers.get("HX-Request") == "true":
        name = "partials/results_data.html"
    else:
        name = "results.html"
    return templates.TemplateResponse(
        request=request,
        name=name,
        context={
            "stats": stats,
            "filters": filters,
            "countries": COUNTRIES,
            "age_bands": list(AgeBand),
            "genders": list(Gender),
            "education_levels": list(EducationLevel),
        },
    )
