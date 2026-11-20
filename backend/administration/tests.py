from accounts.testing import AccountsTestBase
from administration.models import AuditLog, SystemSetting


class AdministrationTests(AccountsTestBase):
    ADMIN_PW = "AdminPassword123!"
    DR_PW = "DoctorPassword123!"
    PT_PW = "PatientPassword123!"

    def as_admin(self):
        return self.login_user("admin_test", self.ADMIN_PW)

    def as_doctor(self):
        return self.login_user("dr_salma_test", self.DR_PW)

    def as_patient(self):
        return self.login_user("patient_test", self.PT_PW)

    def test_audit_log_and_settings_admin_only(self):
        # 1. Non-admin performs a write action that succeeds
        self.as_patient()
        r = self.client.patch(
            f"/api/patients/{self.patient_profile_1.id}/",
            {"phone": "01234567899"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)

        # 2. Non-admin cannot view audit logs (403)
        self.assertEqual(self.client.get("/api/audit/").status_code, 403)

        # 3. Admin can view audit logs and finds the recorded action
        self.as_admin()
        log_res = self.client.get("/api/audit/")
        self.assertEqual(log_res.status_code, 200)
        logs = log_res.data
        if isinstance(logs, dict) and "results" in logs:
            logs = logs["results"]

        self.assertTrue(
            any(
                entry["path"] == f"/api/patients/{self.patient_profile_1.id}/"
                and entry["action"] == "PATCH"
                for entry in logs
            )
        )

        # 4. Admin creates a system setting
        setting_res = self.client.post(
            "/api/settings/",
            {"key": "clinic_name", "value": "OncoSphere Cairo", "description": "Hospital Name"},
            format="json",
        )
        self.assertEqual(setting_res.status_code, 201)
        setting_id = setting_res.data["id"]

        # 5. Admin updates the setting
        patch_res = self.client.patch(
            f"/api/settings/{setting_id}/",
            {"value": "OncoSphere Central"},
            format="json",
        )
        self.assertEqual(patch_res.status_code, 200)
        self.assertEqual(patch_res.data["value"], "OncoSphere Central")

        setting_obj = SystemSetting.objects.get(id=setting_id)
        self.assertEqual(setting_obj.updated_by, self.admin_user)

        # 6. Patient cannot access settings (403)
        self.as_patient()
        self.assertEqual(self.client.get("/api/settings/").status_code, 403)
        self.assertEqual(
            self.client.post("/api/settings/", {"key": "x", "value": "y"}, format="json").status_code,
            403,
        )

    def test_auth_endpoints_are_not_logged_in_audit(self):
        # Login and refresh must NOT be logged in AuditLog to protect passwords and tokens
        initial_count = AuditLog.objects.count()
        self.client.post(
            "/api/auth/login/",
            {"username": "admin_test", "password": self.ADMIN_PW},
            format="json",
        )
        self.assertEqual(
            AuditLog.objects.filter(path__startswith="/api/auth/login").count(),
            0,
        )
