import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Literal

from database import get_connection
from services.jwt_service import decode_access_token
from services.mongodb_service import add_complaint_activity


router = APIRouter(
    prefix="/api/complaints",
    tags=["Complaints"]
)

security = HTTPBearer()


# =========================================================
# GET CURRENT USER FROM JWT
# =========================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    user = decode_access_token(token)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    if user.get("role") not in {"student", "faculty"}:
        raise HTTPException(status_code=403, detail="Student or faculty access required")

    if not isinstance(user.get("id"), int):
        raise HTTPException(status_code=401, detail="Invalid authentication token")

    return user


# =========================================================
# COMPLAINT REQUEST MODEL
# =========================================================

class ComplaintRequest(BaseModel):
    student_name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    title: str = Field(min_length=3, max_length=180)
    category: str = Field(min_length=1, max_length=80)
    location: str = Field(min_length=1, max_length=180)
    description: str = Field(min_length=10, max_length=5000)
    priority: Literal["Low", "Medium", "High"]


# =========================================================
# CREATE COMPLAINT
# =========================================================

@router.post("")
def create_complaint(
    complaint: ComplaintRequest,
    current_user=Depends(get_current_user)
):

    user_id = current_user.get("id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID not found in token"
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        # -------------------------------------------------
        # Verify user exists
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT id, name, email, role
            FROM users
            WHERE id = %s
            """,
            (user_id,)
        )

        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        if user["role"] not in {"student", "faculty"}:
            raise HTTPException(
                status_code=403,
                detail="Only student and faculty accounts can submit complaints"
            )

        # -------------------------------------------------
        # Insert complaint into PostgreSQL
        # -------------------------------------------------

        cursor.execute(
            """
            INSERT INTO complaints (
                user_id,
                student_name,
                email,
                title,
                category,
                location,
                description,
                priority,
                status,
                assigned_staff
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING complaint_id
            """,
            (
                user_id,
                user["name"],
                user["email"],
                complaint.title,
                complaint.category,
                complaint.location,
                complaint.description,
                complaint.priority,
                "Pending",
                None
            )
        )

        complaint_id = cursor.fetchone()["complaint_id"]

        connection.commit()

        # -------------------------------------------------
        # Save complaint activity in MongoDB
        # -------------------------------------------------

        try:

            add_complaint_activity(
                complaint_id,
                "Submitted",
                "Pending",
                "Complaint submitted by student"
            )

        except Exception:

            # MongoDB failure should not cancel
            # the successfully created SQLite complaint.
            logging.warning("Mongo complaint activity could not be recorded")

        # -------------------------------------------------
        # Response
        # -------------------------------------------------

        return {
            "message": "Complaint submitted successfully",
            "complaint_id": complaint_id,
            "status": "Pending",
            "student_name": user["name"],
            "title": complaint.title
        }

    finally:

        cursor.close()
        connection.close()


# =========================================================
# GET MY COMPLAINTS
# =========================================================

@router.get("")
def get_my_complaints(
    current_user=Depends(get_current_user)
):

    user_id = current_user.get("id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID not found in token"
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                complaint_id,
                user_id,
                student_name,
                email,
                title,
                category,
                location,
                description,
                priority,
                status,
                assigned_staff,
                created_at,
                updated_at
            FROM complaints
            WHERE user_id = %s
            ORDER BY complaint_id DESC
            """,
            (user_id,)
        )

        complaints = cursor.fetchall()

        result = []

        for complaint in complaints:

            result.append({
                "complaint_id": complaint["complaint_id"],
                "user_id": complaint["user_id"],
                "student_name": complaint["student_name"],
                "email": complaint["email"],
                "title": complaint["title"],
                "category": complaint["category"],
                "location": complaint["location"],
                "description": complaint["description"],
                "priority": complaint["priority"],
                "status": complaint["status"],
                "assigned_staff": complaint["assigned_staff"],
                "created_at": complaint["created_at"],
                "updated_at": complaint["updated_at"]
            })

        return {
            "complaints": result
        }

    finally:

        cursor.close()
        connection.close()


# =========================================================
# GET SINGLE COMPLAINT
# =========================================================

@router.get("/{complaint_id}")
def get_complaint(
    complaint_id: int,
    current_user=Depends(get_current_user)
):

    user_id = current_user.get("id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID not found in token"
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                complaint_id,
                user_id,
                student_name,
                email,
                title,
                category,
                location,
                description,
                priority,
                status,
                assigned_staff,
                created_at,
                updated_at
            FROM complaints
            WHERE complaint_id = %s
            AND user_id = %s
            """,
            (
                complaint_id,
                user_id
            )
        )

        complaint = cursor.fetchone()

        if not complaint:

            raise HTTPException(
                status_code=404,
                detail="Complaint not found"
            )

        return {
            "complaint_id": complaint["complaint_id"],
            "user_id": complaint["user_id"],
            "student_name": complaint["student_name"],
            "email": complaint["email"],
            "title": complaint["title"],
            "category": complaint["category"],
            "location": complaint["location"],
            "description": complaint["description"],
            "priority": complaint["priority"],
            "status": complaint["status"],
            "assigned_staff": complaint["assigned_staff"],
            "created_at": complaint["created_at"],
            "updated_at": complaint["updated_at"]
        }

    finally:

        cursor.close()
        connection.close()
