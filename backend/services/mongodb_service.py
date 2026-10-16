import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "campuscare")


if not MONGO_URI:
    raise ValueError("MONGO_URI is not configured in .env")


client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)

database = client[MONGO_DB]

complaint_activity_collection = database["complaint_activity"]


def test_mongodb_connection():
    client.admin.command("ping")
    return True


def add_complaint_activity(
    complaint_id,
    action,
    status,
    message
):
    document = {
        "complaint_id": complaint_id,
        "action": action,
        "status": status,
        "message": message
    }

    result = complaint_activity_collection.insert_one(document)

    return str(result.inserted_id)


def get_complaint_activity(complaint_id):
    activities = complaint_activity_collection.find(
        {"complaint_id": complaint_id}
    ).sort("_id", 1)

    return [
        {
            "id": str(activity["_id"]),
            "complaint_id": activity["complaint_id"],
            "action": activity["action"],
            "status": activity["status"],
            "message": activity["message"]
        }
        for activity in activities
    ]
