from django.test import TestCase
from rest_framework.test import APIClient
from accounts.models import User


class AccountsTestBase(TestCase):
    """
    Shared test base class for the entire team.
    Provides standard test users and JWT authentication helpers.
    """

    def setUp(self):
        super().setUp()
        self.client = APIClient()

        # Standard test users across roles
        self.admin_user = User.objects.create_user(
            username="admin_test",
            password="AdminPassword123!",
            email="admin@oncosphere.local",
            first_name="Admin",
            last_name="System",
            role=User.Role.ADMIN,
        )

        self.clinical_user = User.objects.create_user(
            username="dr_salma_test",
            password="DoctorPassword123!",
            email="salma@oncosphere.local",
            first_name="Salma",
            last_name="Oncologist",
            role=User.Role.CLINICAL,
        )

        self.patient_user = User.objects.create_user(
            username="patient_test",
            password="PatientPassword123!",
            email="patient@oncosphere.local",
            first_name="Ahmed",
            last_name="Ali",
            role=User.Role.PATIENT,
        )

    def login_user(self, username="admin_test", password="AdminPassword123!"):
        """Helper to obtain JWT and configure self.client Authorization header."""
        res = self.client.post("/api/auth/login/", {"username": username, "password": password}, format="json")
        if res.status_code == 200:
            token = res.data["access"]
            self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
            return token
        return None

    def logout_user(self):
        """Helper to clear client credentials."""
        self.client.credentials()
