# survey-demo

Demo travel survey: collects demographic characteristics and travel preferences
(countries already visited, countries the respondent would like to visit, and
the single favourite country), and shows the aggregate results as interactive
world maps — shaded by how many people selected each country — plus a numeric
table, filterable by demographics.

Built with **FastAPI + MongoDB** on the backend and **htmx + Pico CSS + MapLibre GL**
on the frontend (hypermedia-driven, zero build step, fully self-contained offline:
all JS/CSS assets and the map geometry are vendored in the image).

## Quickstart (Docker)

```bash
docker compose up -d
```

then open http://localhost:8000 — the survey is at `/`, results at `/results`.

The stack runs the published image `paluigi/survey-demo` (multi-arch:
`linux/amd64` and `linux/arm64`) together with MongoDB 7. To pre-fill the
results page with 80 realistic fake responses:

```bash
docker compose --profile seed run --rm seed
```

## Local development

Requires [uv](https://docs.astral.sh/uv/) and a reachable MongoDB.

```bash
uv sync
MONGODB_URI=mongodb://localhost:27017 uv run uvicorn survey.main:app --reload
```

Re-generate the map geometry or the country list (after bumping sources):

```bash
uv run --with pycountry python scripts/build_geojson.py   # data/world_countries.geojson
uv run --with pycountry python scripts/gen_countries.py   # src/survey/countries.py
```

Seed fake responses locally:

```bash
uv run python -m survey.seed --count 60 [--force]
```

## How it works

- **Survey (`/`)** — demographics (age band, gender, education, country of
  residence, home country) plus two searchable country checklists and a
  favourite-country dropdown that only offers countries ticked as visited
  (validated again server-side). Submitted via `hx-post`; the thank-you card
  is swapped in without a page reload, and the form degrades to a plain HTML
  POST + redirect when JavaScript is unavailable.
- **Results (`/results`)** — a MapLibre GL world choropleth (no tiles: a
  GeoJSON source served by `/api/map/choropleth` with per-country counts
  merged in). The metric switches between *Visited / Want to visit /
  Favourite*; shading uses a step-expression ramp recomputed from the data
  max. Clicking a country (or a table row) selects it — background dims,
  a side card with counts and percentages loads via htmx, and the URL gets
  a shareable `?country=` / `?cat=` parameter. Filters (age band, gender,
  education, residence, home country) re-render the table through htmx and
  reload the map data; a numeric table lists every selected country.
- **Storage** — responses live in MongoDB (`responses` collection); counts
  are computed with `$facet` aggregation pipelines (`$unwind` + `$group` per
  country). All database access goes through an async repository
  (`src/survey/repository.py`, motor).
- **Theming** — Pico CSS `data-theme` dark/light toggle, persisted in
  `localStorage`; the map background, borders and zero-bucket color follow
  the theme.

## Configuration

| Variable             | Default                     | Purpose                    |
| -------------------- | --------------------------- | -------------------------- |
| `MONGODB_URI`        | `mongodb://localhost:27017` | MongoDB connection string  |
| `MONGODB_DB`         | `survey_demo`               | database name              |
| `MONGODB_COLLECTION` | `responses`                 | collection name            |

## Project layout

```
src/survey/            FastAPI app (models, repository, web routes/partials/api)
data/                  vendored world map geometry (Natural Earth, public domain)
templates/             Jinja2 templates (pages + htmx partials)
static/                app JS/CSS + vendored htmx, Pico CSS, MapLibre GL
scripts/               asset vendoring + geojson/country generation
Dockerfile             multi-arch image (python:3.12-slim + uv)
docker-compose.yml     app + mongo (+ optional `seed` profile)
```

Vendored frontend assets and their licenses are listed in
`static/vendor/VENDORED.md`; map geometry is derived from
[Natural Earth](https://www.naturalearthdata.com/) (public domain).
