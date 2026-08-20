"""Seed MongoDB with realistic fake survey responses.

Usage:  uv run python -m survey.seed [--count 60] [--seed 42] [--force]

Skips seeding when responses already exist, unless --force is given.
"""

from __future__ import annotations

import argparse
import asyncio
import random
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from motor.motor_asyncio import AsyncIOMotorClient

from survey.config import Settings
from survey.models import AgeBand, EducationLevel, Gender, SurveySubmission
from survey.repository import SurveyRepository

# Rough tourism-attractiveness weights (default 1 for unlisted countries).
POPULARITY: dict[str, int] = {
    "FR": 30,
    "ES": 28,
    "IT": 28,
    "US": 26,
    "DE": 22,
    "GB": 22,
    "AT": 16,
    "GR": 16,
    "PT": 15,
    "NL": 14,
    "CH": 14,
    "TR": 13,
    "TH": 13,
    "JP": 13,
    "CN": 12,
    "MX": 12,
    "CZ": 11,
    "HR": 11,
    "PL": 10,
    "BE": 10,
    "IE": 9,
    "SE": 9,
    "NO": 9,
    "DK": 9,
    "MA": 8,
    "EG": 8,
    "AE": 8,
    "CA": 10,
    "BR": 8,
    "AR": 7,
    "AU": 9,
    "NZ": 7,
    "IN": 8,
    "VN": 8,
    "ID": 8,
    "SG": 9,
    "MY": 7,
    "PH": 6,
    "KR": 8,
    "HU": 8,
    "ZA": 6,
    "KE": 5,
    "IS": 6,
    "FI": 6,
    "CY": 6,
    "MT": 6,
    "LU": 5,
    "MC": 3,
}

# Where respondents are from / live (default 1 for unlisted countries).
HOME_WEIGHTS: dict[str, int] = {
    "IT": 14,
    "DE": 10,
    "FR": 9,
    "GB": 8,
    "ES": 8,
    "US": 8,
    "NL": 5,
    "PL": 5,
    "BE": 4,
    "AT": 3,
    "CH": 3,
    "SE": 3,
    "RO": 3,
    "PT": 3,
    "IN": 4,
    "BR": 3,
    "CN": 3,
    "JP": 2,
    "CA": 3,
    "AU": 2,
    "ZA": 2,
    "TR": 2,
    "MX": 2,
    "EG": 2,
}


def _weighted_sample(codes: Sequence[str], weights: Sequence[float], k: int) -> list[str]:
    k = min(k, len(codes))
    picked: set[str] = set()
    remaining = list(zip(codes, weights, strict=True))
    while len(picked) < k:
        chosen = random.choices(
            remaining, weights=[w for _, w in remaining], k=max(1, (k - len(picked)) // 2)
        )
        picked.update(code for code, _ in chosen)
        remaining = [(code, weight) for code, weight in remaining if code not in picked]
        if not remaining:
            break
    return sorted(picked)


def generate(count: int, seed: int) -> list[SurveySubmission]:
    random.seed(seed)
    from survey.countries import COUNTRIES

    codes = [code for code, _ in COUNTRIES]
    home_weights = [HOME_WEIGHTS.get(code, 1) for code in codes]
    pop_weights = [POPULARITY.get(code, 1) for code in codes]
    now = datetime.now(UTC)

    submissions = []
    for i in range(count):
        home = random.choices(codes, weights=home_weights, k=1)[0]
        residence = (
            home if random.random() < 0.82 else random.choices(codes, weights=home_weights, k=1)[0]
        )
        age_band = random.choices(list(AgeBand), weights=[22, 30, 20, 13, 9, 6], k=1)[0]
        gender = random.choices(list(Gender), weights=[48, 45, 4, 3], k=1)[0]
        education = random.choices(
            [*list(EducationLevel), None], weights=[18, 35, 30, 8, 5, 4], k=1
        )[0]
        n_visited = min(1 + int(random.expovariate(1 / 7.0)), 38)
        visited = {home, *_weighted_sample(codes, pop_weights, n_visited)}
        wishlist_pool = [
            (code, weight)
            for code, weight in zip(codes, pop_weights, strict=True)
            if code not in visited
        ]
        n_wish = min(random.randint(1, 14), len(wishlist_pool))
        wishlist = _weighted_sample(
            [code for code, _ in wishlist_pool], [weight for _, weight in wishlist_pool], n_wish
        )
        visited_list = sorted(visited)
        favourite = random.choices(
            visited_list, weights=[POPULARITY.get(c, 1) for c in visited_list], k=1
        )[0]
        submissions.append(
            SurveySubmission(
                age_band=age_band,
                gender=gender,
                education=education,
                residence_country=residence,
                home_country=home,
                visited=visited_list,
                wishlist=wishlist,
                favourite=favourite,
                submitted_at=now - timedelta(days=random.uniform(0, 30), seconds=i),
            )
        )
    return submissions


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=60)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--force", action="store_true", help="seed even if responses exist")
    args = parser.parse_args()

    settings = Settings.from_env()
    client = AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
    repository = SurveyRepository(client, settings)

    existing = await repository.count_all()
    if existing and not args.force:
        print(f"Collection already has {existing} responses; use --force to seed anyway.")
        return
    if args.force and existing:
        deleted = await repository.delete_all()
        print(f"Deleted {deleted} existing responses.")

    submissions = generate(args.count, args.seed)
    for submission in submissions:
        await repository.insert(submission)
    print(f"Inserted {len(submissions)} fake responses.")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
