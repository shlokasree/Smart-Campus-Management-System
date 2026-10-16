import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, jsonify, request
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# CampusCare project root & environment
BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "campus_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")


def get_connection():
    connection = psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        cursor_factory=RealDictCursor
    )
    return connection


# Allow frontend JavaScript to access Flask
@app.after_request
def add_cors_headers(response):
    allowed_origins = {
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://127.0.0.1:5500,http://localhost:5500"
        ).split(",")
        if origin.strip()
    }
    origin = request.headers.get("Origin")
    if origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET"
    return response


# -----------------------------------------
# HOME
# -----------------------------------------

@app.route("/")
def home():
    return jsonify({
        "service": "CampusCare Analytics Service",
        "status": "running"
    })


# -----------------------------------------
# OVERALL ANALYTICS
# -----------------------------------------

@app.route("/analytics/summary")
def analytics_summary():

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            "SELECT COUNT(*) AS total FROM complaints"
        )
        total_complaints = cursor.fetchone()["total"]

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM complaints
            WHERE status = 'Pending'
            """
        )
        pending = cursor.fetchone()["total"]

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM complaints
            WHERE status = 'In Progress'
            """
        )
        in_progress = cursor.fetchone()["total"]

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM complaints
            WHERE status = 'Resolved'
            """
        )
        resolved = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT COUNT(*) AS total FROM users"
        )
        total_users = cursor.fetchone()["total"]

        if total_complaints > 0:
            resolution_rate = round(
                (resolved / total_complaints) * 100,
                2
            )
        else:
            resolution_rate = 0

        return jsonify({
            "total_complaints": total_complaints,
            "pending": pending,
            "in_progress": in_progress,
            "resolved": resolved,
            "total_users": total_users,
            "resolution_rate": resolution_rate
        })

    finally:
        connection.close()


# -----------------------------------------
# COMPLAINTS BY CATEGORY
# -----------------------------------------

@app.route("/analytics/categories")
def analytics_categories():

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            SELECT category, COUNT(*) AS count
            FROM complaints
            GROUP BY category
            ORDER BY count DESC
            """
        )

        rows = cursor.fetchall()

        categories = []

        for row in rows:
            categories.append({
                "category": row["category"],
                "count": row["count"]
            })

        return jsonify({
            "categories": categories
        })

    finally:
        connection.close()


# -----------------------------------------
# COMPLAINTS BY STATUS
# -----------------------------------------

@app.route("/analytics/status")
def analytics_status():

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            SELECT status, COUNT(*) AS count
            FROM complaints
            GROUP BY status
            """
        )

        rows = cursor.fetchall()

        status_data = []

        for row in rows:
            status_data.append({
                "status": row["status"],
                "count": row["count"]
            })

        return jsonify({
            "status": status_data
        })

    finally:
        connection.close()


# -----------------------------------------
# COMPLAINTS BY PRIORITY
# -----------------------------------------

@app.route("/analytics/priorities")
def analytics_priorities():

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            SELECT priority, COUNT(*) AS count
            FROM complaints
            GROUP BY priority
            ORDER BY count DESC
            """
        )

        rows = cursor.fetchall()

        priorities = []

        for row in rows:
            priorities.append({
                "priority": row["priority"],
                "count": row["count"]
            })

        return jsonify({
            "priorities": priorities
        })

    finally:
        connection.close()


# -----------------------------------------
# RUN FLASK SERVER
# -----------------------------------------

if __name__ == "__main__":
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5001")),
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true"
    )
