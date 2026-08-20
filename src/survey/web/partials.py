"""htmx partial endpoints: submission and the per-country map side cards."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError

from survey.models import SurveyFilters, SurveyStats, SurveySubmission
from survey.repository import SurveyRepository
from survey.web.deps import get_repository, survey_filters
from survey.web.templating import build_templates

router = APIRouter()
templates = build_templates()


@router.post("/submit", response_class=HTMLResponse)
async def submit(
    request: Request,
    age_band: str = Form(...),
    gender: str = Form(...),
    education: str = Form(""),
    residence_country: str = Form(""),
    home_country: str = Form(""),
    favourite: str = Form(""),
    visited: list[str] = Form(default=[]),
    wishlist: list[str] = Form(default=[]),
    repository: SurveyRepository = Depends(get_repository),
) -> HTMLResponse:
    def optional(value: str) -> str | None:
        return value or None

    try:
        submission = SurveySubmission(
            age_band=age_band,
            gender=gender,
            education=optional(education),
            residence_country=optional(residence_country),
            home_country=optional(home_country),
            visited=visited,
            wishlist=wishlist,
            favourite=optional(favourite),
        )
    except ValidationError as exc:
        if request.headers.get("HX-Request") == "true":
            # Keep the filled-in form intact: retarget the error card to the
            # feedback slot instead of replacing the whole form wrapper.
            return templates.TemplateResponse(
                request=request,
                name="partials/error.html",
                context={"errors": _messages(exc)},
                status_code=422,
                headers={"HX-Retarget": "#form-feedback", "HX-Reswap": "innerHTML"},
            )
        return RedirectResponse("/?error=validation", status_code=303)

    await repository.insert(submission)
    if request.headers.get("HX-Request") == "true":
        return templates.TemplateResponse(
            request=request,
            name="partials/success.html",
            context={"favourite": submission.favourite},
        )
    return RedirectResponse("/thanks", status_code=303)


@router.get("/thanks", response_class=HTMLResponse)
async def thanks(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="thanks.html", context={})


@router.get("/partials/map-cards", response_class=HTMLResponse)
async def map_cards(
    request: Request,
    country: str,
    filters: SurveyFilters = Depends(survey_filters),
    repository: SurveyRepository = Depends(get_repository),
) -> HTMLResponse:
    stats: SurveyStats = await repository.stats(filters)
    code = country.strip().upper()
    return templates.TemplateResponse(
        request=request,
        name="partials/map_cards.html",
        context={"row": stats.row_for(code), "total": stats.total, "filters": filters},
    )


def _messages(exc: ValidationError) -> list[str]:
    messages = []
    for error in exc.errors(include_url=False):
        location = " → ".join(str(part) for part in error["loc"])
        label = {
            "age_band": "age band",
            "gender": "gender",
            "education": "education",
            "residence_country": "country of residence",
            "home_country": "home country",
            "visited": "visited countries",
            "wishlist": "wishlist countries",
            "favourite": "favourite country",
        }.get(location, location or "form")
        messages.append(f"{label}: {error['msg']}")
    return messages
