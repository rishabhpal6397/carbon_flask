"""
CarbonIQ – Calculation Model
Manages the 'calculations' MongoDB collection.

MongoDB Schema (calculations collection):
{
    "_id":        ObjectId,
    "user_id":    str,            # FK → users._id (stored as string)
    "inputs":     {               # raw user inputs
        "travel_km":       float,
        "vehicle":         str,
        "electricity":     float,
        "diet":            str,
        "clothes_monthly": int,
        "waste_weekly":    int,
        "grocery_bill":    float,
        "sex":             str
    },
    "results": {
        "emissions":     { Travel, Electricity, Diet, Total },
        "optimization":  { optimized_total, reduction_kg, reduction_pct },
        "prediction":    { current, predicted, delta, trend },
        "recommendations": [ ... ],
        "score":         { value, category, label }
    },
    "created_at": datetime
}
"""

from datetime import datetime
from bson import ObjectId
from extensions import mongo

class Calculation:

    @staticmethod
    def save(user_id: str, inputs: dict, results: dict) -> str:
        """Persist a new calculation and return its string ID."""
        doc = {
            "user_id":    user_id,
            "inputs":     inputs,
            "results":    results,
            "created_at": datetime.utcnow(),
        }
        result = mongo.db.calculations.insert_one(doc)
        return str(result.inserted_id)

    @staticmethod
    def get_by_user(user_id: str, limit: int = 10) -> list:
        """Return the most recent `limit` calculations for a user (newest first)."""
        cursor = (
            mongo.db.calculations
            .find({"user_id": user_id})
            .sort("created_at", -1)
            .limit(limit)
        )
        records = []
        for doc in cursor:
            doc["_id"]        = str(doc["_id"])
            doc["created_at"] = doc["created_at"].strftime("%d %b %Y, %I:%M %p")
            records.append(doc)
        return records

    @staticmethod
    def get_by_id( calc_id: str, user_id: str) -> dict | None:
        """Fetch a single calculation belonging to user_id (security check)."""
        doc = mongo.db.calculations.find_one(
            {"_id": ObjectId(calc_id), "user_id": user_id}
        )
        if doc:
            doc["_id"]        = str(doc["_id"])
            doc["created_at"] = doc["created_at"].strftime("%d %b %Y, %I:%M %p")
        return doc

    @staticmethod
    def delete(calc_id: str, user_id: str) -> bool:
        """Delete a record only if it belongs to the requesting user."""
        result = mongo.db.calculations.delete_one(
            {"_id": ObjectId(calc_id), "user_id": user_id}
        )
        return result.deleted_count > 0

    @staticmethod
    def monthly_totals(user_id: str) -> list:
        """
        Aggregate monthly CO₂ totals for the past 6 months.
        Returns: [{ "month": "Jan 2025", "total": 320.5 }, ...]
        """
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$sort": {"created_at": -1}},
            {"$limit": 50},   # scan last 50 records at most
            {"$group": {
                "_id": {
                    "year":  {"$year":  "$created_at"},
                    "month": {"$month": "$created_at"},
                },
                "avg_total": {"$avg": "$results.emissions.Total"},
            }},
            {"$sort": {"_id.year": 1, "_id.month": 1}},
            {"$limit": 6},
        ]
        results = list(mongo.db.calculations.aggregate(pipeline))

        import calendar
        formatted = []
        for r in results:
            month_name = calendar.month_abbr[r["_id"]["month"]]
            formatted.append({
                "month": f"{month_name} {r['_id']['year']}",
                "total": round(r["avg_total"], 2),
            })
        return formatted
