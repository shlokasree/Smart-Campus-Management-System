
import hmac

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from pwdlib import PasswordHash

from database import get_connection
from services.jwt_service import create_access_token
from config import (
    STAFF_REGISTRATION_CODE,
    ADMIN_REGISTRATION_CODE,
)

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)

password_hash = PasswordHash.recommended()


# ==========================================================
# REQUEST MODELS
# ==========================================================

class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=256)
    role: str = "student"
    registration_code: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name is required")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()

        if (
            "@" not in value
            or "." not in value.rsplit("@", 1)[-1]
        ):
            raise ValueError("Enter a valid email address")

        return value

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        value = value.strip().lower()

        if value not in {"student", "staff", "admin"}:
            raise ValueError(
                "Role must be student, staff, or admin"
            )

        return value


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()

        if (
            "@" not in value
            or "." not in value.rsplit("@", 1)[-1]
        ):
            raise ValueError("Enter a valid email address")

        return value


# ==========================================================
# REGISTRATION
# POST /api/auth/register
# ==========================================================

@router.post("/register", status_code=201)
def register(user: RegisterRequest):
    role = user.role

    # Validate authorization before creating privileged accounts.
    if role == "staff":
        expected_code = STAFF_REGISTRATION_CODE

        if not expected_code:
            raise HTTPException(
                status_code=503,
                detail="Staff registration is not configured",
            )

        if (
            not user.registration_code
            or not hmac.compare_digest(
                user.registration_code,
                expected_code,
            )
        ):
            raise HTTPException(
                status_code=403,
                detail="Invalid Staff authorization code",
            )

    elif role == "admin":
        expected_code = ADMIN_REGISTRATION_CODE

        if not expected_code:
            raise HTTPException(
                status_code=503,
                detail="Admin registration is not configured",
            )

        if (
            not user.registration_code
            or not hmac.compare_digest(
                user.registration_code,
                expected_code,
            )
        ):
            raise HTTPException(
                status_code=403,
                detail="Invalid Admin authorization code",
            )

    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE LOWER(email) = %s
            """,
            (user.email,),
        )

        if cursor.fetchone():
            raise HTTPException(
                status_code=409,
                detail="Email already registered",
            )

        hashed_password = password_hash.hash(user.password)

        cursor.execute(
            """
            INSERT INTO users (
                name,
                email,
                password_hash,
                role
            )
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (
                user.name,
                user.email,
                hashed_password,
                role,
            ),
        )

        created_user = cursor.fetchone()

        if not created_user:
            raise HTTPException(
                status_code=500,
                detail="Unable to create account",
            )

        user_id = created_user["id"]

        connection.commit()

        return {
            "message": "Registration successful",
            "user": {
                "id": user_id,
                "name": user.name,
                "email": user.email,
                "role": role,
            },
        }

    except HTTPException:
        if connection is not None:
            connection.rollback()
        raise

    except Exception:
        if connection is not None:
            connection.rollback()

        raise HTTPException(
            status_code=500,
            detail="Registration failed due to a server error",
        )

    finally:
        if connection is not None:
            connection.close()


# ==========================================================
# LOGIN
# POST /api/auth/login
# ==========================================================

@router.post("/login")
def login(user: LoginRequest):
    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                password_hash,
                role
            FROM users
            WHERE LOWER(email) = %s
            """,
            (user.email,),
        )

        database_user = cursor.fetchone()

        if not database_user:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password",
            )

        stored_hash = database_user["password_hash"]

        if not stored_hash:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password",
            )

        try:
            valid_password = password_hash.verify(
                user.password,
                stored_hash,
            )
        except Exception:
            valid_password = False

        if not valid_password:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password",
            )

        role = str(database_user["role"]).strip().lower()

        if role not in {
            "student",
            "staff",
            "admin",
            "faculty",
        }:
            raise HTTPException(
                status_code=403,
                detail="This account role is not enabled",
            )

        access_token = create_access_token(
            {
                "id": database_user["id"],
                "name": database_user["name"],
                "email": database_user["email"],
                "role": role,
            }
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": database_user["id"],
                "name": database_user["name"],
                "email": database_user["email"],
                "role": role,
            },
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Login failed due to a server error",
        )

    finally:
        if connection is not None:
            connection.close()
