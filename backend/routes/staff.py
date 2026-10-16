from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from database import get_connection
from services.jwt_service import decode_access_token


router = APIRouter(
    prefix="/api/staff",
    tags=["Staff"]
)

security = HTTPBearer()


# ==========================================
# GET CURRENT USER
# ==========================================

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

    return user


# ==========================================
# CHECK STAFF ACCESS
# ==========================================

def get_staff_user(
    current_user=Depends(get_current_user)
):

    role = current_user.get("role")

    if role not in ["staff", "admin"]:
        raise HTTPException(
            status_code=403,
            detail="Staff access required"
        )

    return current_user


# ==========================================
# GET ALL COMPLAINTS
# ==========================================

@router.get("/complaints")
def get_all_complaints(
    current_user=Depends(get_staff_user)
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


# ==========================================
# STATUS MODEL
# ==========================================

class StatusUpdate(BaseModel):

    status: str


# ==========================================
# UPDATE COMPLAINT STATUS
# ==========================================

@router.put("/complaints/{complaint_id}/status")
def update_complaint_status(
    complaint_id: int,
    status_data: StatusUpdate,
    current_user=Depends(get_staff_user)
):

    allowed_statuses = [
        "Pending",
        "In Progress",
        "Resolved"
    ]

    if status_data.status not in allowed_statuses:

        raise HTTPException(
            status_code=400,
            detail="Invalid complaint status"
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT complaint_id
            FROM complaints
            WHERE complaint_id = %s
        """, (complaint_id,))

        complaint = cursor.fetchone()

        if not complaint:

            raise HTTPException(
                status_code=404,
                detail="Complaint not found"
            )

        cursor.execute("""
            UPDATE complaints
            SET
                status = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE complaint_id = %s
        """, (
            status_data.status,
            complaint_id
        ))

        connection.commit()

        return {
            "message": "Complaint status updated successfully",
            "complaint_id": complaint_id,
            "status": status_data.status
        }

    finally:

        connection.close()