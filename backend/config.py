
import os
from pathlib import Path

from dotenv import load_dotenv

# CampusCare project root
BASE_DIR = Path(__file__).resolve().parent.parent

# Load secrets from CampusCare/.env
load_dotenv(BASE_DIR / ".env")

# JWT configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "").strip()

if not SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY must be set in the root CampusCare/.env file"
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Staff and Admin registration authorization codes
STAFF_REGISTRATION_CODE = os.getenv(
    "CAMPUSCARE_STAFF_REGISTRATION_CODE", ""
).strip()

ADMIN_REGISTRATION_CODE = os.getenv(
    "CAMPUSCARE_ADMIN_REGISTRATION_CODE", ""
).strip()
