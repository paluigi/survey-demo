"""Async MongoDB repository for survey responses (repository pattern over motor)."""

from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from survey.config import Settings
from survey.models import SurveyFilters, SurveyStats, SurveySubmission


class SurveyRepository:
    """All MongoDB access for the survey, behind an async, object-oriented API."""

    def __init__(self, client: AsyncIOMotorClient, settings: Settings) -> None:
        database: AsyncIOMotorDatabase = client[settings.mongodb_db]
        self._collection = database[settings.collection]

    async def ping(self) -> None:
        await self._collection.database.client.admin.command("ping")

    async def ensure_indexes(self) -> None:
        await self._collection.create_index([("submitted_at", -1)])

    async def insert(self, submission: SurveySubmission) -> None:
        await self._collection.insert_one(submission.model_dump())

    async def count_all(self) -> int:
        return await self._collection.count_documents({})

    async def delete_all(self) -> int:
        result = await self._collection.delete_many({})
        return result.deleted_count

    async def stats(self, filters: SurveyFilters) -> SurveyStats:
        """Per-country counts for visited / wishlist / favourite in one round trip."""
        pipeline: list[dict] = [
            {"$match": filters.to_mongo()},
            {
                "$facet": {
                    "total": [{"$count": "n"}],
                    "visited": self._array_count_pipeline("visited"),
                    "wishlist": self._array_count_pipeline("wishlist"),
                    "favourite": [
                        {"$match": {"favourite": {"$type": "string"}}},
                        {"$group": {"_id": "$favourite", "n": {"$sum": 1}}},
                        {"$sort": {"n": -1, "_id": 1}},
                    ],
                }
            },
        ]
        result = (await self._collection.aggregate(pipeline).to_list(1))[0]
        return SurveyStats(
            total=result["total"][0]["n"] if result["total"] else 0,
            visited={row["_id"]: row["n"] for row in result["visited"]},
            wishlist={row["_id"]: row["n"] for row in result["wishlist"]},
            favourite={row["_id"]: row["n"] for row in result["favourite"]},
        )

    @staticmethod
    def _array_count_pipeline(field: str) -> list[dict]:
        """Count documents per value of an array field (empty arrays contribute nothing)."""
        return [
            {"$match": {field: {"$exists": True, "$ne": []}}},
            {"$unwind": f"${field}"},
            {"$group": {"_id": f"${field}", "n": {"$sum": 1}}},
            {"$sort": {"n": -1, "_id": 1}},
        ]
