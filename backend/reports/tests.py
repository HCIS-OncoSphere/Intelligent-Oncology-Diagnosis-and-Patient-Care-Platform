"""Reports tests. The billing and records parts are checked only when those apps are installed."""
from datetime import timedelta

from django.apps import apps
from django.utils import timezone

from accounts.testing import AccountsTestBase
from appointments.models import Appointment, Doctor


class ReportTests(AccountsTestBase):
    def setUp(self):
        super().setUp()
        self.doctor = Doctor.objects.create(user=self.clinical_user, specialty="Oncology", license_no="L1")
        now = timezone.now()
        for days, status in [(1, "scheduled"), (-1, "completed"), (-2, "no_show"), (-3, "cancelled")]:
            s = now + timedelta(days=days)
            Appointment.objects.create(patient=self.patient_profile_1, doctor=self.doctor, booked_by=self.clinical_user,
                                       start_time=s, end_time=s + timedelta(minutes=30), status=status, reason="x")

    def test_summary_numbers(self):
        self.login_user("admin_test", "AdminPassword123!")
        r = self.client.get("/api/reports/summary/")
        self.assertEqual(r.status_code, 200)
        d = r.data
        self.assertEqual(d["patients_total"], 2)
        self.assertEqual(d["patients_by_gender"], {"F": 1, "M": 1})
        self.assertEqual(d["appointments_total"], 4)
        self.assertEqual(d["appointments_by_status"],
                         {"cancelled": 1, "completed": 1, "no_show": 1, "scheduled": 1})
        self.assertEqual(d["upcoming_appointments"], 1)
        self.assertEqual(d["no_show_rate"], 0.5)
        self.assertEqual(d["appointments_by_doctor"][0]["count"], 3)  # cancelled ones are not counted
        self.assertEqual(sum(x["count"] for x in d["appointments_per_day"]), 4)

    def test_summary_period_parameter(self):
        self.login_user("dr_salma_test", "DoctorPassword123!")
        self.assertEqual(self.client.get("/api/reports/summary/?days=7").data["period_days"], 7)
        self.assertEqual(self.client.get("/api/reports/summary/?days=abc").status_code, 400)

    def test_patient_and_anonymous_blocked(self):
        self.assertEqual(self.client.get("/api/reports/summary/").status_code, 401)
        self.login_user("patient_test", "PatientPassword123!")
        self.assertEqual(self.client.get("/api/reports/summary/").status_code, 403)
        self.assertEqual(self.client.get("/api/reports/export/?type=patients").status_code, 403)

    def test_csv_exports(self):
        self.login_user("dr_salma_test", "DoctorPassword123!")
        pts = self.client.get("/api/reports/export/?type=patients")
        self.assertEqual(pts.status_code, 200)
        self.assertTrue(pts["Content-Type"].startswith("text/csv"))
        text = pts.content.decode("utf-8-sig")
        self.assertTrue(text.startswith("mrn,gender"))
        self.assertIn(self.patient_profile_1.mrn, text)
        appts = self.client.get("/api/reports/export/?type=appointments").content.decode("utf-8-sig")
        self.assertEqual(len(appts.strip().splitlines()), 5)  # header + 4 rows
        self.assertEqual(self.client.get("/api/reports/export/?type=foo").status_code, 400)
        inv = self.client.get("/api/reports/export/?type=invoices")
        self.assertEqual(inv.status_code, 200 if apps.is_installed("billing") else 400)
