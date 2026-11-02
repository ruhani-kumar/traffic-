from datetime import datetime
import os
from zoneinfo import ZoneInfo

from pymongo import MongoClient
from pymongo.collection import Collection

import config

COLLECTIONS = {
    "routes": "route_snapshots",
    "locations": "location_snapshots",
    "incident_summary": "incident_summaries",
    "raw_responses": "raw_responses",
    "coverage_routes": "coverage_route_snapshots",
    "coverage_points": "point_snapshots",
    "incidents": "incident_snapshots",
    "incident_runs": "incident_runs",
}


def _collection(kind: str) -> Collection:
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        raise RuntimeError(
            "MONGODB_URI is not set. Add your MongoDB Atlas connection string to .env."
        )

    database_name = os.environ.get("MONGODB_DATABASE", "jadavpur_traffic")
    client = MongoClient(uri, serverSelectionTimeoutMS=config.REQUEST_TIMEOUT * 1000)
    collection_name = COLLECTIONS.get(kind)
    if collection_name is None:
        client.close()
        raise ValueError(f"Unsupported MongoDB collection kind: {kind}")

    collection = client[database_name][collection_name]
    collection.create_index("observed_at")
    if kind in {"routes", "coverage_routes"}:
        collection.create_index([("route_name", 1), ("observed_at", -1)])
    elif kind == "coverage_points":
        collection.create_index([("point_name", 1), ("observed_at", -1)])
    elif kind == "locations":
        collection.create_index([("location", 1), ("observed_at", -1)])
    elif kind == "raw_responses":
        collection.create_index([("api", 1), ("name", 1), ("observed_at", -1)])
    return collection


def save(kind: str, rows: list[dict]) -> int:
    if not rows:
        return 0

    documents = []
    for row in rows:
        document = dict(row)
        document["observed_at"] = datetime.strptime(
            row["run_time_ist"], "%Y-%m-%d %H:%M:%S"
        ).replace(tzinfo=ZoneInfo(config.TIMEZONE))
        documents.append(document)

    collection = _collection(kind)
    try:
        result = collection.insert_many(documents)
        return len(result.inserted_ids)
    finally:
        collection.database.client.close()


def save_incident_run(ctx: dict, incidents: list[dict]) -> None:
    collection = _collection("incident_runs")
    document = {
        **ctx,
        "observed_at": datetime.strptime(
            ctx["run_time_ist"], "%Y-%m-%d %H:%M:%S"
        ).replace(tzinfo=ZoneInfo(config.TIMEZONE)),
        "incident_count": len(incidents),
        "incidents": incidents,
    }
    try:
        collection.insert_one(document)
    finally:
        collection.database.client.close()


def has_rows_starting(kind: str, time_prefix: str) -> bool:
    # True if a document's run_time_ist starts with time_prefix,
    # e.g. "2026-11-02 18" = "anything saved during 6 pm on 2 Nov?"
    collection = _collection(kind)
    try:
        return collection.find_one({"run_time_ist": {"$regex": f"^{time_prefix}"}}, {"_id": 1}) is not None
    finally:
        collection.database.client.close()
