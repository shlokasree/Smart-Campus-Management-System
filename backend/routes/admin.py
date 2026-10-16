from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from database import get_connection
from services.jwt_service import decode_access_token


router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"]
)

security = HTTPBearer()


# =========================================================
# ADMIN AUTHENTICATION
# =========================================================

def get_admin_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    user = decode_access_token(token)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    if user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return user


# =========================================================
# GET ALL COMPLAINTS
# =========================================================

@router.get("/complaints")
def get_all_complaints(
    current_user=Depends(get_admin_user)
):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
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
            ORDER BY complaint_id DESC
        """)

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
        connection.close()


# =========================================================
# GET ALL USERS
# =========================================================

@router.get("/users")
def get_all_users(
    current_user=Depends(get_admin_user)
):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                id,
                name,
                email,
                role,
                created_at
            FROM users
            ORDER BY id DESC
        """)

        users = cursor.fetchall()

        result = []

        for user in users:
            result.append({
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"],
                "created_at": user["created_at"]
            })

        return {
            "users": result
        }

    finally:
        connection.close()


# =========================================================
# ADMIN DASHBOARD STATISTICS
# =========================================================

@router.get("/stats")
def get_admin_stats(
    current_user=Depends(get_admin_user)
):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        # Total complaints
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM complaints
        """)
        total_complaints = cursor.fetchone()["total"]

        # Pending complaints
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM complaints
            WHERE status = 'Pending'
        """)
        pending = cursor.fetchone()["total"]

        # In Progress complaints
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM complaints
            WHERE status = 'In Progress'
        """)
        in_progress = cursor.fetchone()["total"]

        # Resolved complaints
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM complaints
            WHERE status = 'Resolved'
        """)
        resolved = cursor.fetchone()["total"]

        # Total users
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM users
        """)
        total_users = cursor.fetchone()["total"]

        # Calculate resolved percentage
        if total_complaints > 0:
            resolved_ratio = round(
                (resolved / total_complaints) * 100
            )
        else:
            resolved_ratio = 0

        return {
            "total_complaints": total_complaints,
            "total_users": total_users,
            "pending": pending,
            "in_progress": in_progress,
            "resolved": resolved,
            "resolved_ratio": resolved_ratio
        }

    finally:
        connection.close()


# =========================================================
# UPDATE COMPLAINT STATUS
# =========================================================

class StatusRequest(BaseModel):
    status: str


@router.put("/complaints/{complaint_id}/status")
def update_complaint_status(
    complaint_id: int,
    request: StatusRequest,
    current_user=Depends(get_admin_user)
):
    allowed_statuses = [
        "Pending",
        "In Progress",
        "Resolved"
    ]

    if request.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid status"
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT complaint_id
            FROM complaints
            WHERE complaint_id = %s
            """,
            (complaint_id,)
        )

        complaint = cursor.fetchone()

        if not complaint:
            raise HTTPException(
                status_code=404,
                detail="Complaint not found"
            )

        cursor.execute(
            """
            UPDATE complaints
            SET status = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE complaint_id = %s
            """,
            (request.status, complaint_id)
        )

        connection.commit()

        return {
            "message": "Complaint status updated successfully",
            "complaint_id": complaint_id,
            "status": request.status
        }

    finally:
        connection.close()