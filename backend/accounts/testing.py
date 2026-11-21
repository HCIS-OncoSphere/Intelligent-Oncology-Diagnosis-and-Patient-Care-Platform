"""Shared test fixture. Every app's tests inherit from BaseCase so nobody duplicates setup code."""

from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
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

        self.patient_user_2 = User.objects.create_user(
            username="patient_test_2",
            password="PatientPassword123!",
            email="patient2@oncosphere.local",
            first_name="Sara",
            last_name="Ibrahim",
            role=User.Role.PATIENT,
        )

        # Create Patient profiles if patients app is available.
        # Only ImportError is caught — if the app IS installed, DB errors
        # should not be silenced.
        try:
            from patients.models import Patient
            self.patient_profile_1 = Patient.objects.create(
                user=self.patient_user,
                date_of_birth="1992-04-10",
                gender=Patient.Gender.MALE,
                phone="01111222333",
                emergency_contact="Father: 01000000000",
                cancer_type="Breast",
                cancer_stage="Stage II",
            )
            self.patient_profile_2 = Patient.objects.create(
                user=self.patient_user_2,
                date_of_birth="1988-11-20",
                gender=Patient.Gender.FEMALE,
                phone="01222333444",
                emergency_contact="Spouse: 01111111111",
                cancer_type="Lung",
                cancer_stage="Stage I",
            )
        except ImportError:
            pass

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


def next_weekday_at(hour):
    d = timezone.localtime() + timedelta(days=1)
    while d.weekday() > 4:
        d += timedelta(days=1)
    return d.replace(hour=hour, minute=0, second=0, microsecond=0)


class BaseCase(TestCase):
    def setUp(self):
        from appointments.models import Doctor
        from billing.models import ICD10Code
        from patients.models import Patient
        self.c = APIClient()
        self.admin = User.objects.create_user("adm", email="adm@test.com", password="Admin12345", role="admin")   # no doctor profile
        self.dr = User.objects.create_user("dr", email="dr@test.com", password="Doctor12345", role="clinical")
        self.doctor = Doctor.objects.create(user=self.dr, specialty="Onc", license_no="L1")
        self.p1 = User.objects.create_user("p1", email="p1@test.com", password="Patient12345", role="patient")
        self.p2 = User.objects.create_user("p2", email="p2@test.com", password="Patient12345", role="patient")
        self.pt1 = Patient.objects.create(user=self.p1, date_of_birth="1990-01-01", gender="F")
        self.pt2 = Patient.objects.create(user=self.p2, date_of_birth="1991-01-01", gender="M")
        ICD10Code.objects.create(code="C25.9", description="Pancreas")
        ICD10Code.objects.create(code="Z51.11", description="Chemo")

    def login(self, user, pw):
        r = self.c.post("/api/auth/login/", {"username": user, "password": pw}, format="json")
        self.assertEqual(r.status_code, 200)
        self.c.credentials(HTTP_AUTHORIZATION="Bearer " + r.data["access"])

    def as_admin(self): self.login("adm", "Admin12345")
    def as_doctor(self): self.login("dr", "Doctor12345")
    def as_p1(self): self.login("p1", "Patient12345")
    def as_p2(self): self.login("p2", "Patient12345")