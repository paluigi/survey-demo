"""Jinja2 template environment with shared globals."""

from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates

from survey.countries import COUNTRY_BY_CODE

TEMPLATES_DIR = Path(__file__).resolve().parents[3] / "templates"

GENDER_LABELS = {
    "female": "Female",
    "male": "Male",
    "non-binary": "Non-binary",
    "prefer-not-to-say": "Prefer not to say",
}


def build_templates() -> Jinja2Templates:
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    templates.env.globals["country_name"] = lambda code: COUNTRY_BY_CODE.get(code, code)
    templates.env.globals["gender_label"] = lambda value: GENDER_LABELS.get(value, str(value))
    return templates
