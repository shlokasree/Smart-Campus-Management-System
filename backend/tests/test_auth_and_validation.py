import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from fastapi import HTTPException
from pydantic import ValidationError

from routes.auth import LoginRequest, RegisterRequest
from routes.complaints import ComplaintRequest, get_current_user
from routes.staff import get_staff_user
from routes.admin import get_admin_user
from services.jwt_service import create_access_token, decode_access_token


class AuthAndValidationTests(unittest.TestCase):
    def test_registration_normalizes_email_and_name(self):
        request = RegisterRequest(
            name="  Campus Student  ",
            email="  STUDENT@EXAMPLE.EDU ",
            password="StrongPass123!",
        )
        self.assertEqual(request.name, "Campus Student")
        self.assertEqual(request.email, "student@example.edu")

    def test_registration_rejects_short_password(self):
        with self.assertRaises(ValidationError):
            RegisterRequest(name="Student", email="student@example.edu", password="short")

    def test_login_normalizes_email(self):
        self.assertEqual(
            LoginRequest(email=" ADMIN@EXAMPLE.EDU ", password="secret").email,
            "admin@example.edu",
        )

    def test_complaint_accepts_supported_priority(self):
        complaint = ComplaintRequest(
            student_name="Student",
            email="student@example.edu",
            title="Broken light",
            category="Electrical",
            location="Library",
            description="The light is broken in the reading room.",
            priority="High",
        )
        self.assertEqual(complaint.priority, "High")

    def test_complaint_rejects_unsupported_priority(self):
        with self.assertRaises(ValidationError):
            ComplaintRequest(
                student_name="Student",
                email="student@example.edu",
                title="Broken light",
                category="Electrical",
                location="Library",
                description="The light is broken in the reading room.",
                priority="Urgent",
            )

    def test_staff_route_accepts_staff_and_admin_only(self):
        self.assertEqual(get_staff_user({"role": "staff"})["role"], "staff")
        self.assertEqual(get_staff_user({"role": "admin"})["role"], "admin")
        with self.assertRaises(HTTPException) as raised:
            get_staff_user({"role": "student"})
        self.assertEqual(raised.exception.status_code, 403)

    @patch("routes.complaints.decode_access_token")
    def test_faculty_can_use_student_complaint_routes(self, decode):
        decode.return_value = {"id": 42, "role": "faculty"}
        user = get_current_user(SimpleNamespace(credentials="signed-token"))
        self.assertEqual(user["role"], "faculty")

    @patch("routes.admin.decode_access_token")
    def test_admin_route_rejects_student_role(self, decode):
        decode.return_value = {"id": 1, "role": "student"}
        with self.assertRaises(HTTPException) as raised:
            get_admin_user(SimpleNamespace(credentials="signed-token"))
        self.assertEqual(raised.exception.status_code, 403)

    def test_jwt_round_trip_and_invalid_token(self):
        token = create_access_token({"id": 42, "role": "student"})
        self.assertEqual(decode_access_token(token)["id"], 42)
        self.assertIsNone(decode_access_token("not-a-jwt"))


if __name__ == "__main__":
    unittest.main()
