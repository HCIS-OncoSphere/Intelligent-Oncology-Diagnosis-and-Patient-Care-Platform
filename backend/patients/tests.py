from accounts.testing import AccountsTestBase
from patients.models import Patient


class PatientManagementTests(AccountsTestBase):
    def test_patient_mrn_generated_automatically(self):
        self.assertTrue(self.patient_profile_1.mrn.startswith("MRN-"))
        self.assertEqual(len(self.patient_profile_1.mrn), 16)  # "MRN-" + 12 hex chars

    def test_patient_sees_only_own_profile_in_list(self):
        self.login_user("patient_test", "PatientPassword123!")
        res = self.client.get("/api/patients/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], self.patient_profile_1.id)
        self.assertEqual(res.data[0]["mrn"], self.patient_profile_1.mrn)

    def test_patient_cannot_access_other_patient_detail(self):
        self.login_user("patient_test", "PatientPassword123!")
        # Patient 1 tries to access Patient 2's profile
        res = self.client.get(f"/api/patients/{self.patient_profile_2.id}/")
        self.assertEqual(res.status_code, 404)

    def test_patient_can_update_own_contact_details(self):
        self.login_user("patient_test", "PatientPassword123!")
        payload = {
            "phone": "01099998888",
            "address": "123 Cairo St",
            "emergency_contact": "Brother: 01011112222",
        }
        res = self.client.patch(f"/api/patients/{self.patient_profile_1.id}/", payload, format="json")
        self.assertEqual(res.status_code, 200)
        self.patient_profile_1.refresh_from_db()
        self.assertEqual(self.patient_profile_1.phone, "01099998888")
        self.assertEqual(self.patient_profile_1.address, "123 Cairo St")
        self.assertEqual(self.patient_profile_1.emergency_contact, "Brother: 01011112222")

    def test_patient_cannot_tamper_with_mrn(self):
        self.login_user("patient_test", "PatientPassword123!")
        original_mrn = self.patient_profile_1.mrn
        res = self.client.patch(f"/api/patients/{self.patient_profile_1.id}/", {"mrn": "MRN-FORGED"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.patient_profile_1.refresh_from_db()
        self.assertEqual(self.patient_profile_1.mrn, original_mrn)

    def test_doctor_can_view_all_patients(self):
        self.login_user("dr_salma_test", "DoctorPassword123!")
        res = self.client.get("/api/patients/")
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(len(res.data), 2)
        patient_ids = [p["id"] for p in res.data]
        self.assertIn(self.patient_profile_1.id, patient_ids)
        self.assertIn(self.patient_profile_2.id, patient_ids)

    def test_admin_can_view_all_patients(self):
        self.login_user("admin_test", "AdminPassword123!")
        res = self.client.get("/api/patients/")
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(len(res.data), 2)

    def test_unauthenticated_request_is_unauthorized(self):
        res = self.client.get("/api/patients/")
        self.assertEqual(res.status_code, 401)
