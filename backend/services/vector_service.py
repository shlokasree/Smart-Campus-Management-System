import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector
from pgvector import Vector


# --------------------------------------------------
# LOAD ENVIRONMENT VARIABLES
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]

load_dotenv(BASE_DIR / ".env")


# --------------------------------------------------
# POSTGRESQL CONNECTION
# --------------------------------------------------

def get_postgres_connection():
    connection = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        database=os.getenv("POSTGRES_DB", "pgvector_code"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD")
    )

    register_vector(connection)

    return connection


# --------------------------------------------------
# SAVE COMPLAINT EMBEDDING
# --------------------------------------------------

def save_complaint_embedding(
    complaint_id,
    description,
    embedding
):
    connection = get_postgres_connection()
    cursor = connection.cursor()

    try:
        vector = Vector(embedding)

        cursor.execute(
            """
            INSERT INTO complaint_embeddings
            (
                complaint_id,
                description,
                embedding
            )
            VALUES (%s, %s, %s)
            """,
            (
                complaint_id,
                description,
                vector
            )
        )

        connection.commit()

    finally:
        cursor.close()
        connection.close()


# --------------------------------------------------
# FIND SIMILAR COMPLAINTS
# --------------------------------------------------

def find_similar_complaints(
    embedding,
    limit=5
):
    connection = get_postgres_connection()
    cursor = connection.cursor()

    try:
        vector = Vector(embedding)

        cursor.execute(
            """
            SELECT
                complaint_id,
                description,
                1 - (embedding <=> %s) AS similarity
            FROM complaint_embeddings
            ORDER BY embedding <=> %s
            LIMIT %s
            """,
            (
                vector,
                vector,
                limit
            )
        )

        rows = cursor.fetchall()

        return [
            {
                "complaint_id": row[0],
                "description": row[1],
                "similarity": float(row[2])
            }
            for row in rows
        ]

    finally:
        cursor.close()
        connection.close()