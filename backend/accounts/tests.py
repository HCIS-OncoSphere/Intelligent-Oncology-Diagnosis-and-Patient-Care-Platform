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
            "username": "new_patient",
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
        self.assertEqual(res.data["username"], "new_patient")
        self.assertEqual(res.data["role"], "patient")
        self.assertTrue(User.objects.filter(username="new_patient").exists())

    def test_register_duplicate_username_rejected(self):
        payload = {
            "username": "admin_test",
            "password": "SecurePassword123!",
            "email": "other@test.com",
            "first_name": "Test",
            "last_name": "User",
        }
        res = self.client.post("/api/auth/register/", payload, format="json")
        self.assertEqual(res.status_code, 400)


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
