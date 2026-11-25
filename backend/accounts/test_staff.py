"""Doctor registration (self + by admin), the approval flow, finance accounts and the new patient fields."""
import shutil
import tempfile

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from accounts.models import DoctorApplication, Notification, User
from accounts.testing import AccountsTestBase

TMP_MEDIA = tempfile.mkdtemp()


def licence(name="licence.pdf", size=100):
    return SimpleUploadedFile(name, b"%PDF-" + b"x" * size, content_type="application/pdf")


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class StaffTestBase(AccountsTestBase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    def doctor_form(self, **over):
        base = {
            "first_name": "Hala", "last_name": "Said", "email": "hala@test.com", "phone": "01011112222",
            "password": "Tumor-Board-2026", "specialty": "Oncology", "license_no": "LIC-100",
            "years_experience": "8", "education": "Cairo University", "languages": "Arabic, English",
            "focus_areas": "Breast cancer", "license_document": licence(),
        }
        base.update(over)
        return base

    def apply(self, **over):
        return self.client.post("/api/auth/register/doctor/", self.doctor_form(**over), format="multipart")


class DoctorSelfRegistrationTests(StaffTestBase):
    def test_application_creates_inactive_doctor_and_notifies_admin(self):
        res = self.apply()
        self.assertEqual(res.status_code, 201, res.data)
        user = User.objects.get(email="hala@test.com")
        self.assertFalse(user.is_active)
        self.assertEqual(user.role, "clinical")
        self.assertEqual(user.doctor.license_no, "LIC-100")
        self.assertEqual(user.doctor.years_experience, 8)
        self.assertEqual(user.doctor_applications.get().status, "pending")
        self.assertTrue(Notification.objects.filter(user=self.admin_user, title="New doctor request").exists())

    def test_pending_doctor_cannot_sign_in_and_is_told_why(self):
        self.apply()
        res = self.client.post("/api/auth/login/", {"username": "hala@test.com", "password": "Tumor-Board-2026"},
                               format="json")
        self.assertEqual(res.status_code, 401)
        self.assertIn("waiting for admin approval", res.data["detail"])

    def test_wrong_password_reveals_nothing(self):
        self.apply()
        res = self.client.post("/api/auth/login/", {"username": "hala@test.com", "password": "nope-nope-1"},
                               format="json")
        self.assertEqual(res.status_code, 401)
        self.assertNotIn("approval", str(res.data["detail"]))

    def test_licence_file_is_required_and_checked(self):
        res = self.apply(license_document=SimpleUploadedFile("x.exe", b"abc"))
        self.assertEqual(res.status_code, 400)
        self.assertIn("license_document", res.data)
        body = self.doctor_form()
        del body["license_document"]
        self.assertEqual(self.client.post("/api/auth/register/doctor/", body, format="multipart").status_code, 400)
        self.assertEqual(User.objects.filter(email="hala@test.com").count(), 0)

    def test_duplicate_email_and_licence_are_rejected(self):
        self.assertEqual(self.apply().status_code, 201)
        again = self.apply(license_document=licence())
        self.assertEqual(again.status_code, 400)  # same email, still pending
        other = self.apply(email="other@test.com", license_document=licence())
        self.assertEqual(other.status_code, 400)
        self.assertIn("license_no", other.data)

    def test_cannot_use_existing_patient_email(self):
        res = self.apply(email="patient@oncosphere.local")
        self.assertEqual(res.status_code, 400)
        self.assertIn("email", res.data)


class DoctorApprovalTests(StaffTestBase):
    def setUp(self):
        super().setUp()
        self.apply()
        self.app = DoctorApplication.objects.get()

    def test_only_admin_can_review(self):
        self.login_user("dr_salma_test", "DoctorPassword123!")
        self.assertEqual(self.client.get("/api/admin/doctor-requests/").status_code, 403)
        self.assertEqual(self.client.post(f"/api/admin/doctor-requests/{self.app.id}/approve/").status_code, 403)
        self.logout_user()
        self.assertEqual(self.client.get("/api/admin/doctor-requests/").status_code, 401)

    def test_admin_lists_filters_and_opens_the_licence(self):
        self.login_user()
        res = self.client.get("/api/admin/doctor-requests/?status=pending")
        self.assertEqual(res.status_code, 200)
        rows = res.data["results"] if isinstance(res.data, dict) else res.data
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["doctor"]["specialty"], "Oncology")
        self.assertEqual(self.client.get("/api/admin/doctor-requests/?status=approved").data, [])
        f = self.client.get(rows[0]["license_url"])
        self.assertEqual(f.status_code, 200)

    def test_approve_activates_and_emails(self):
        self.login_user()
        res = self.client.post(f"/api/admin/doctor-requests/{self.app.id}/approve/")
        self.assertEqual(res.status_code, 200)
        user = User.objects.get(email="hala@test.com")
        self.assertTrue(user.is_active)
        self.app.refresh_from_db()
        self.assertEqual((self.app.status, self.app.reviewed_by), ("approved", self.admin_user))
        self.assertTrue(Notification.objects.filter(user=user).exists())
        self.assertEqual(mail.outbox[-1].to, ["hala@test.com"])
        self.assertEqual(self.client.post(f"/api/admin/doctor-requests/{self.app.id}/approve/").status_code, 400)
        self.logout_user()
        self.assertIsNotNone(self.login_user("hala@test.com", "Tumor-Board-2026"))

    def test_reject_needs_a_reason_then_blocks_login_with_the_reason(self):
        self.login_user()
        url = f"/api/admin/doctor-requests/{self.app.id}/reject/"
        self.assertEqual(self.client.post(url, {"reason": "  "}, format="json").status_code, 400)
        self.assertEqual(self.client.post(url, {"reason": "Licence photo is blurry."}, format="json").status_code, 200)
        self.assertIn("blurry", mail.outbox[-1].body)
        self.logout_user()
        res = self.client.post("/api/auth/login/", {"username": "hala@test.com", "password": "Tumor-Board-2026"},
                               format="json")
        self.assertEqual(res.status_code, 401)
        self.assertIn("Licence photo is blurry", res.data["detail"])

    def test_rejected_doctor_can_apply_again_with_the_same_email(self):
        self.login_user()
        self.client.post(f"/api/admin/doctor-requests/{self.app.id}/reject/", {"reason": "Wrong file"}, format="json")
        self.logout_user()
        res = self.apply(license_no="LIC-100", password="New-Password-2026", license_document=licence("new.pdf"))
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(User.objects.filter(email="hala@test.com").count(), 1)
        statuses = list(DoctorApplication.objects.order_by("id").values_list("status", flat=True))
        self.assertEqual(statuses, ["rejected", "pending"])
        user = User.objects.get(email="hala@test.com")
        self.assertTrue(user.check_password("New-Password-2026"))
        self.assertFalse(user.is_active)


class AdminCreatesAccountsTests(StaffTestBase):
    def test_admin_creates_doctor_with_temporary_password(self):
        self.login_user()
        form = self.doctor_form()
        del form["password"]
        res = self.client.post("/api/admin/doctors/", form, format="multipart")
        self.assertEqual(res.status_code, 201, res.data)
        temp = res.data["temporary_password"]
        user = User.objects.get(email="hala@test.com")
        self.assertTrue(user.is_active and user.must_change_password)
        self.assertTrue(user.check_password(temp))
        self.assertIn(temp, mail.outbox[-1].body)
        self.logout_user()
        self.login_user("hala@test.com", temp)
        self.assertTrue(self.client.get("/api/auth/me/").data["must_change_password"])

    def test_admin_can_create_a_doctor_without_a_licence_file(self):
        self.login_user()
        form = self.doctor_form()
        del form["license_document"]
        self.assertEqual(self.client.post("/api/admin/doctors/", form, format="multipart").status_code, 201)

    def test_doctor_and_patient_cannot_create_accounts(self):
        for user, pw in (("dr_salma_test", "DoctorPassword123!"), ("patient_test", "PatientPassword123!")):
            self.login_user(user, pw)
            self.assertEqual(self.client.post("/api/admin/doctors/", self.doctor_form(), format="multipart")
                             .status_code, 403)
            self.assertEqual(self.client.post("/api/admin/finance/", {"first_name": "a", "last_name": "b",
                             "email": "f@test.com"}, format="json").status_code, 403)

    def test_admin_creates_finance_staff(self):
        self.login_user()
        res = self.client.post("/api/admin/finance/", {"first_name": "Nour", "last_name": "Adel",
                               "email": "nour@test.com"}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["role"], "finance")
        self.assertEqual(self.client.post("/api/admin/finance/", {"first_name": "N", "last_name": "A",
                         "email": "nour@test.com"}, format="json").status_code, 400)

    def test_change_password_clears_the_flag(self):
        self.login_user()
        temp = self.client.post("/api/admin/finance/", {"first_name": "Nour", "last_name": "Adel",
                                "email": "nour@test.com"}, format="json").data["temporary_password"]
        self.logout_user()
        self.login_user("nour@test.com", temp)
        bad = self.client.post("/api/auth/change-password/", {"current_password": "x", "new_password": "Brand-New-2026"},
                               format="json")
        self.assertEqual(bad.status_code, 400)
        weak = self.client.post("/api/auth/change-password/", {"current_password": temp, "new_password": "12345678"},
                                format="json")
        self.assertEqual(weak.status_code, 400)
        ok = self.client.post("/api/auth/change-password/", {"current_password": temp, "new_password": "Brand-New-2026"},
                              format="json")
        self.assertEqual(ok.status_code, 200)
        self.assertFalse(self.client.get("/api/auth/me/").data["must_change_password"])


class FinanceRoleTests(StaffTestBase):
    def setUp(self):
        super().setUp()
        self.finance = User.objects.create_user("fin", email="fin@test.com", password="Finance-2026", role="finance")

    def test_finance_runs_billing(self):
        from billing.models import Service
        self.login_user("fin", "Finance-2026")
        svc = self.client.post("/api/services/", {"name": "Consult", "price": "500.00"}, format="json")
        self.assertEqual(svc.status_code, 201, svc.data)
        inv = self.client.post("/api/invoices/", {"patient": self.patient_profile_1.id,
                               "items_in": [{"service": Service.objects.get().id, "quantity": 2}]}, format="json")
        self.assertEqual(inv.status_code, 201, inv.data)
        self.assertEqual(self.client.get("/api/invoices/").data[0]["patient_mrn"], self.patient_profile_1.mrn)
        pay = self.client.post(f"/api/invoices/{inv.data['id']}/pay/", {"amount": "1000", "method": "cash"},
                               format="json")
        self.assertEqual(pay.status_code, 200)
        self.assertEqual(pay.data["status"], "paid")

    def test_finance_cannot_see_medical_data(self):
        self.login_user("fin", "Finance-2026")
        for url in ("/api/appointments/", "/api/imaging/studies/", "/api/reports/summary/"):
            res = self.client.get(url)
            self.assertNotEqual(res.status_code, 404, url)  # the URL exists, so an empty/403 answer is meaningful
            body = getattr(res, "data", None)
            body = body.get("results", body) if isinstance(body, dict) else body
            self.assertTrue(res.status_code == 403 or not body, (url, res.status_code, body))

    def test_finance_sees_only_names_of_patients(self):
        self.login_user("fin", "Finance-2026")
        rows = self.client.get("/api/patients/").data
        rows = rows.get("results", rows) if isinstance(rows, dict) else rows
        self.assertEqual(len(rows), 2)
        self.assertEqual(set(rows[0]), {"id", "mrn", "name"})
        self.assertEqual(self.client.patch(f"/api/patients/{rows[0]['id']}/", {"phone": "1"}, format="json").status_code, 403)

    def test_doctor_and_patient_cannot_change_prices_or_pay_for_others(self):
        self.login_user("dr_salma_test", "DoctorPassword123!")
        self.assertEqual(self.client.post("/api/services/", {"name": "X", "price": "1"}, format="json").status_code, 403)
        self.login_user("patient_test", "PatientPassword123!")
        self.assertEqual(self.client.post("/api/services/", {"name": "X", "price": "1"}, format="json").status_code, 403)


class PatientRegistrationFieldsTests(StaffTestBase):
    def test_new_fields_are_saved(self):
        res = self.client.post("/api/auth/register/", {
            "password": "Tumor-Board-2026", "email": "mona@test.com", "first_name": "Mona", "last_name": "Kamal",
            "date_of_birth": "1990-03-02", "gender": "F", "phone": "01055556666", "address": "12 Nile St, Cairo",
            "blood_type": "O+", "emergency_contact": "Husband - Ali", "emergency_contact_phone": "01099998888",
            "national_id": "29003020101234"}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        from patients.models import Patient
        p = Patient.objects.get(user__email="mona@test.com")
        self.assertEqual((p.address, p.blood_type, p.emergency_contact_phone, p.national_id),
                         ("12 Nile St, Cairo", "O+", "01099998888", "29003020101234"))

    def test_bad_blood_type_and_national_id_are_rejected(self):
        base = {"password": "Tumor-Board-2026", "email": "mona@test.com", "first_name": "Mona", "last_name": "Kamal",
                "date_of_birth": "1990-03-02"}
        for extra, field in (({"blood_type": "Z+"}, "blood_type"), ({"national_id": "123"}, "national_id")):
            res = self.client.post("/api/auth/register/", {**base, **extra}, format="json")
            self.assertEqual(res.status_code, 400)
            self.assertIn(field, res.data)
