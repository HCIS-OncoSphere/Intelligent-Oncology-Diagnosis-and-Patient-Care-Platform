from accounts.models import User
from accounts.testing import AccountsTestBase


class AccountsAuthTests(AccountsTestBase):
    def test_login_success_returns_jwt_tokens(self):
        token = self.login_user("admin_test", "AdminPassword123!")
        self.assertIsNotNone(token)
        self.assertTrue(len(token) > 20)

    def test_login_invalid_credentials(self):
        token = self.login_user("admin_test", "WrongPassword!")
        self.assertIsNone(token)

    def test_token_refresh(self):
        login_res = self.client.post("/api/auth/login/", {"username": "admin_test", "password": "AdminPassword123!"}, format="json")
        self.assertEqual(login_res.status_code, 200)
        refresh = login_res.data["refresh"]

        refresh_res = self.client.post("/api/auth/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(refresh_res.status_code, 200)
        self.assertIn("access", refresh_res.data)

    def test_get_me_authenticated(self):
        self.login_user("dr_salma_test", "DoctorPassword123!")
        res = self.client.get("/api/auth/me/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["username"], "dr_salma_test")
        self.assertEqual(res.data["role"], "clinical")

    def test_get_me_unauthenticated_fails(self):
        res = self.client.get("/api/auth/me/")
        self.assertEqual(res.status_code, 401)

    def test_patient_self_registration(self):
        payload = {
            "username": "chosen_by_client",  # ignored: the system makes the username
            "password": "SecurePassword123!",
            "email": "new_patient@test.com",
            "first_name": "Mona",
            "last_name": "Kamal",
            "date_of_birth": "1995-05-15",
            "gender": "F",
            "phone": "01012345678",
        }
        res = self.client.post("/api/auth/register/", payload, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["username"], "new_patient")  # from the email
        self.assertEqual(res.data["role"], "patient")
        self.assertFalse(User.objects.filter(username="chosen_by_client").exists())

    def test_username_gets_a_number_when_taken(self):
        payload = {
            "password": "SecurePassword123!",
            "email": "Admin_Test@other.com",  # "admin_test" already exists
            "first_name": "Test",
            "last_name": "User",
            "date_of_birth": "1990-01-01",
        }
        res = self.client.post("/api/auth/register/", payload, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["username"], "admin_test2")


class RegistrationValidationTests(AccountsTestBase):
    def payload(self, **over):
        base = {
            "password": "Tumor-Board-2026",
            "email": "laila@test.com",
            "first_name": "Laila",
            "last_name": "Hassan",
            "date_of_birth": "1990-03-02",
            "gender": "F",
            "phone": "01055556666",
        }
        base.update(over)
        return base

    def register(self, **over):
        return self.client.post("/api/auth/register/", self.payload(**over), format="json")

    def test_registration_creates_patient_profile(self):
        from patients.models import Patient
        res = self.register()
        self.assertEqual(res.status_code, 201)
        p = Patient.objects.get(user__username="laila")  # from laila@test.com
        self.assertEqual(p.gender, "F")
        self.assertTrue(p.mrn.startswith("MRN-"))

    def test_password_rules_shown_on_the_page_are_enforced(self):
        # too short, and only numbers
        for pw in ("Ab1!", "1234567890"):
            res = self.register(password=pw)
            self.assertEqual(res.status_code, 400, pw)
            self.assertIn("password", res.data)

    def test_no_similarity_or_common_password_errors(self):
        # only the rules on the page apply: no "too similar to the username" / "too common" messages
        for i, pw in enumerate(("laila123", "password123")):
            res = self.register(email=f"laila{i}@test.com", password=pw)
            self.assertEqual(res.status_code, 201, (pw, res.data))

    def test_duplicate_email_is_case_insensitive(self):
        res = self.register(email="PATIENT@oncosphere.local")
        self.assertIn("email", res.data)

    def test_arabic_names_allowed_but_email_must_be_english(self):
        res = self.register(first_name="منة", last_name="حسن")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(User.objects.get(username="laila").first_name, "منة")
        res = self.register(email="منة@test.com")
        self.assertEqual(res.status_code, 400)
        self.assertIn("email", res.data)

    def test_invalid_gender_and_future_birth_date_rejected(self):
        res = self.register(gender="Female", date_of_birth="2999-01-01")
        self.assertEqual(res.status_code, 400)
        self.assertIn("gender", res.data)
        self.assertIn("date_of_birth", res.data)

    def test_missing_birth_date_rejected(self):
        payload = self.payload()
        del payload["date_of_birth"]
        res = self.client.post("/api/auth/register/", payload, format="json")
        self.assertIn("date_of_birth", res.data)

    def test_registered_user_can_sign_in_with_email(self):
        self.register(email="Laila@Test.com")
        res = self.client.post("/api/auth/login/", {"username": "laila@test.com", "password": "Tumor-Board-2026"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertIn("access", res.data)

    def test_registration_cannot_create_staff(self):
        res = self.register(role="admin")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(User.objects.get(username="laila").role, "patient")


class AccountsUserManagementTests(AccountsTestBase):
    def test_admin_can_list_users(self):
        self.login_user("admin_test", "AdminPassword123!")
        res = self.client.get("/api/users/")
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(len(res.data), 3)

    def test_admin_can_create_clinical_user(self):
        self.login_user("admin_test", "AdminPassword123!")
        payload = {
            "username": "dr_tarek",
            "password": "Doctor12345!",
            "email": "tarek@oncosphere.local",
            "first_name": "Tarek",
            "last_name": "Omar",
            "role": "clinical",
            "phone": "01234567890",
            "specialty": "Radiation Oncology",
            "license_no": "MED-9988",
        }
        res = self.client.post("/api/users/", payload, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["username"], "dr_tarek")
        self.assertEqual(res.data["role"], "clinical")

    def test_non_admin_forbidden_from_users_endpoint(self):
        # Patient
        self.login_user("patient_test", "PatientPassword123!")
        res = self.client.get("/api/users/")
        self.assertEqual(res.status_code, 403)

        # Clinical
        self.login_user("dr_salma_test", "DoctorPassword123!")
        res = self.client.get("/api/users/")
        self.assertEqual(res.status_code, 403)

    def test_admin_can_toggle_user_active_status(self):
        self.login_user("admin_test", "AdminPassword123!")
        res = self.client.patch(f"/api/users/{self.patient_user.id}/", {"is_active": False}, format="json")
        self.assertEqual(res.status_code, 200)
        self.patient_user.refresh_from_db()
        self.assertFalse(self.patient_user.is_active)
