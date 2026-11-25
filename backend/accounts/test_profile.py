import shutil
import tempfile
from datetime import time, timedelta
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from PIL import Image

from accounts.testing import AccountsTestBase
from appointments.models import Appointment, Doctor, DoctorAvailability

MEDIA = tempfile.mkdtemp(prefix="onco-media-")


def picture(fmt="PNG", size=(900, 600), name="photo.png"):
    buf = BytesIO()
    Image.new("RGB", size, (20, 120, 110)).save(buf, fmt)
    return SimpleUploadedFile(name, buf.getvalue(), content_type=f"image/{fmt.lower()}")


@override_settings(MEDIA_ROOT=MEDIA)
class ProfileTests(AccountsTestBase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        super().setUp()
        self.doctor = Doctor.objects.create(user=self.clinical_user, specialty="Oncology", license_no="LIC-1")
        today = timezone.localdate()
        DoctorAvailability.objects.create(doctor=self.doctor, day_of_week=today.weekday(),
                                          start_time=time(0, 0), end_time=time(23, 59))
        start = timezone.now() + timedelta(days=1)
        Appointment.objects.create(patient=self.patient_profile_1, doctor=self.doctor, booked_by=self.admin_user,
                                   start_time=start, end_time=start + timedelta(minutes=30), reason="Follow-up")

    # ---- viewing ----
    def test_patient_sees_own_profile_with_medical_summary(self):
        self.login_user("patient_test", "PatientPassword123!")
        res = self.client.get("/api/profile/")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["is_me"])
        p = res.data["patient"]
        self.assertEqual(p["cancer_type"], "Breast")
        self.assertEqual(len(p["upcoming"]), 1)
        self.assertEqual(p["care_team"][0]["name"], "Salma Oncologist")

    def test_patient_cannot_see_another_patient(self):
        self.login_user("patient_test", "PatientPassword123!")
        res = self.client.get(f"/api/profile/{self.patient_user_2.id}/")
        self.assertEqual(res.status_code, 404)

    def test_patient_sees_doctor_without_schedule(self):
        self.login_user("patient_test", "PatientPassword123!")
        res = self.client.get(f"/api/profile/{self.clinical_user.id}/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["doctor"]["specialty"], "Oncology")
        self.assertNotIn("today", res.data["doctor"])  # schedule names patients
        self.assertNotIn("stats", res.data["doctor"])

    def test_doctor_sees_own_stats_and_can_open_a_patient(self):
        self.login_user("dr_salma_test", "DoctorPassword123!")
        me = self.client.get("/api/profile/").data["doctor"]
        self.assertTrue(me["available_today"])
        self.assertEqual(me["stats"]["patients"], 1)
        res = self.client.get(f"/api/profile/{self.patient_user.id}/")
        self.assertEqual(res.status_code, 200)

    def test_admin_profile_is_private(self):
        self.login_user("dr_salma_test", "DoctorPassword123!")
        self.assertEqual(self.client.get(f"/api/profile/{self.admin_user.id}/").status_code, 404)

    # ---- editing ----
    def test_patient_edits_contact_details(self):
        self.login_user("patient_test", "PatientPassword123!")
        res = self.client.patch("/api/profile/", {"phone": "0100 123", "address": "Cairo",
                                                  "emergency_contact": "Ali 0111"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.patient_profile_1.refresh_from_db()
        self.assertEqual(self.patient_profile_1.address, "Cairo")
        self.assertEqual(self.patient_profile_1.phone, "0100 123")

    def test_patient_cannot_edit_medical_fields_through_profile(self):
        self.login_user("patient_test", "PatientPassword123!")
        self.client.patch("/api/profile/", {"cancer_type": "None", "cancer_stage": "0"}, format="json")
        self.patient_profile_1.refresh_from_db()
        self.assertEqual(self.patient_profile_1.cancer_type, "Breast")

    def test_patient_cannot_set_doctor_fields(self):
        self.login_user("patient_test", "PatientPassword123!")
        res = self.client.patch("/api/profile/", {"bio": "hi"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_doctor_edits_about_section(self):
        self.login_user("dr_salma_test", "DoctorPassword123!")
        res = self.client.patch("/api/profile/", {"bio": "Breast cancer specialist", "years_experience": 12,
                                                  "languages": "Arabic, English"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["doctor"]["years_experience"], 12)

    def test_cannot_edit_someone_else(self):
        self.login_user("dr_salma_test", "DoctorPassword123!")
        res = self.client.patch(f"/api/profile/{self.patient_user.id}/", {"phone": "x"}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_email_must_stay_unique(self):
        self.login_user("patient_test", "PatientPassword123!")
        res = self.client.patch("/api/profile/", {"email": "ADMIN@oncosphere.local"}, format="json")
        self.assertIn("email", res.data)

    # ---- photos ----
    def test_upload_avatar_is_cropped_square_and_replaces_old_file(self):
        self.login_user("patient_test", "PatientPassword123!")
        res = self.client.post("/api/profile/photo/", {"kind": "avatar", "file": picture()}, format="multipart")
        self.assertEqual(res.status_code, 201)
        self.patient_user.refresh_from_db()
        first = self.patient_user.avatar.name
        with Image.open(self.patient_user.avatar.path) as img:
            self.assertEqual(img.size, (512, 512))
            self.assertEqual(img.format, "JPEG")
        self.client.post("/api/profile/photo/", {"kind": "avatar", "file": picture()}, format="multipart")
        self.patient_user.refresh_from_db()
        self.assertNotEqual(first, self.patient_user.avatar.name)
        self.assertFalse(self.patient_user.avatar.storage.exists(first))

    def test_upload_cover(self):
        self.login_user("dr_salma_test", "DoctorPassword123!")
        res = self.client.post("/api/profile/photo/", {"kind": "cover", "file": picture("JPEG", name="c.jpg")},
                               format="multipart")
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.data["cover"].endswith(".jpg"))

    def test_rejects_files_that_are_not_images(self):
        self.login_user("patient_test", "PatientPassword123!")
        fake = SimpleUploadedFile("evil.png", b"<script>alert(1)</script>", content_type="image/png")
        res = self.client.post("/api/profile/photo/", {"kind": "avatar", "file": fake}, format="multipart")
        self.assertEqual(res.status_code, 400)

    def test_rejects_unsupported_format(self):
        self.login_user("patient_test", "PatientPassword123!")
        res = self.client.post("/api/profile/photo/", {"kind": "avatar", "file": picture("GIF", name="a.gif")},
                               format="multipart")
        self.assertEqual(res.status_code, 400)

    def test_remove_avatar(self):
        self.login_user("patient_test", "PatientPassword123!")
        self.client.post("/api/profile/photo/", {"kind": "avatar", "file": picture()}, format="multipart")
        res = self.client.delete("/api/profile/photo/?kind=avatar")
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(res.data["avatar"])

    def test_me_includes_avatar(self):
        self.login_user("patient_test", "PatientPassword123!")
        self.client.post("/api/profile/photo/", {"kind": "avatar", "file": picture()}, format="multipart")
        self.assertTrue(self.client.get("/api/auth/me/").data["avatar"])


class ProfileMoreInfoTests(AccountsTestBase):
    """The extra information on every role's profile."""

    def setUp(self):
        super().setUp()
        from accounts.models import User
        self.doctor = Doctor.objects.create(user=self.clinical_user, specialty="Oncology", license_no="LIC-9")
        start = timezone.now() + timedelta(days=1)
        Appointment.objects.create(patient=self.patient_profile_1, doctor=self.doctor, booked_by=self.admin_user,
                                   start_time=start, end_time=start + timedelta(minutes=30), reason="Follow-up")
        self.finance_user = User.objects.create_user("fin_t", email="fin_t@test.com", password="Finance-2026", role="finance")
        self.patient_profile_1.national_id = "29003020101234"
        self.patient_profile_1.emergency_contact_phone = "01099998888"
        self.patient_profile_1.save()

    def test_patient_sees_the_new_sections_and_full_national_id(self):
        self.login_user("patient_test", "PatientPassword123!")
        pt = self.client.get("/api/profile/").data["patient"]
        for key in ("diagnoses", "plans", "medications", "orders", "imaging", "billing", "visits",
                    "emergency_contact_phone", "national_id", "registered_on"):
            self.assertIn(key, pt)
        self.assertEqual(pt["national_id"], "29003020101234")
        self.assertEqual(pt["billing"]["unpaid_count"], 0)
        self.assertIsNotNone(self.client.get("/api/profile/").data["member_since"])

    def test_doctor_sees_only_the_last_four_digits(self):
        self.login_user("dr_salma_test", "DoctorPassword123!")
        pt = self.client.get(f"/api/profile/{self.patient_user.id}/").data["patient"]
        self.assertEqual(pt["national_id"], "**********1234")

    def test_admin_sees_the_whole_number_and_last_login(self):
        self.login_user()
        res = self.client.get(f"/api/profile/{self.patient_user.id}/").data
        self.assertEqual(res["patient"]["national_id"], "29003020101234")
        self.assertIn("last_login", res)

    def test_patient_edits_emergency_phone_and_national_id(self):
        self.login_user("patient_test", "PatientPassword123!")
        ok = self.client.patch("/api/profile/", {"emergency_contact_phone": "01012345678", "national_id": "30001010101234"}, format="json")
        self.assertEqual(ok.status_code, 200, ok.data)
        self.assertEqual(ok.data["patient"]["emergency_contact_phone"], "01012345678")
        bad = self.client.patch("/api/profile/", {"national_id": "123"}, format="json")
        self.assertEqual(bad.status_code, 400)
        self.login_user("dr_salma_test", "DoctorPassword123!")
        self.assertEqual(self.client.patch("/api/profile/", {"national_id": "30001010101234"}, format="json").status_code, 400)

    def test_doctor_profile_has_upcoming_and_completed(self):
        self.login_user("dr_salma_test", "DoctorPassword123!")
        dr = self.client.get("/api/profile/").data["doctor"]
        self.assertEqual(len(dr["upcoming"]), 1)
        self.assertIn("completed", dr["stats"])
        self.login_user("patient_test", "PatientPassword123!")
        public = self.client.get(f"/api/profile/{self.clinical_user.id}/").data["doctor"]
        self.assertNotIn("upcoming", public)  # patients' names stay private

    def test_admin_and_finance_have_their_own_blocks(self):
        self.login_user()
        adm = self.client.get("/api/profile/").data
        self.assertEqual(adm["admin"]["users"]["patient"], 2)
        self.assertIn("recent_activity", adm["admin"])
        self.login_user("fin_t", "Finance-2026")
        fin = self.client.get("/api/profile/").data
        self.assertIn("collected_total", fin["finance"])
        self.assertIsNone(fin["admin"])
