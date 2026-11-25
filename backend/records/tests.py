from datetime import timedelta
from django.utils import timezone

from accounts.testing import AccountsTestBase
from appointments.models import Appointment, Doctor
from billing.models import ICD10Code, Service


class RecordTests(AccountsTestBase):
    def setUp(self):
        super().setUp()
        self.c = self.client
        self.pt1 = self.patient_profile_1
        self.dr = self.clinical_user
        self.doctor = Doctor.objects.create(user=self.dr, specialty="Oncology", license_no="REC-01")
        for code in ("C25.9", "Z51.11"):
            ICD10Code.objects.create(code=code, description="Test diagnosis")

    def make_record(self, **extra):
        body = dict(patient=self.pt1.id, notes="Visit", diagnoses_in=[dict(icd10_code="C25.9", is_primary=True)],
                    prescriptions_in=[dict(medication="Ondansetron", dosage="8mg", frequency="bid", duration="7d")])
        body.update(extra)
        return self.c.post("/api/records/", body, format="json")

    def test_doctor_creates_record_with_dx_and_rx(self):
        self.client.force_authenticate(self.clinical_user)
        r = self.make_record()
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["diagnoses"][0]["icd10_code"], "C25.9")
        self.assertEqual(r.data["prescriptions"][0]["medication"], "Ondansetron")

    def test_two_primary_diagnoses_rejected(self):
        self.client.force_authenticate(self.clinical_user)
        r = self.make_record(diagnoses_in=[dict(icd10_code="C25.9", is_primary=True), dict(icd10_code="Z51.11", is_primary=True)])
        self.assertEqual(r.status_code, 400)

    def test_patient_reads_own_only_and_cannot_write(self):
        self.client.force_authenticate(self.clinical_user); self.make_record()
        self.client.force_authenticate(self.patient_user)
        self.assertEqual(len(self.c.get("/api/records/").data), 1)
        self.assertEqual(self.make_record().status_code, 403)
        self.client.force_authenticate(self.patient_user_2)
        self.assertEqual(len(self.c.get("/api/records/").data), 0)

    def test_user_without_doctor_profile_cannot_create(self):
        self.client.force_authenticate(self.admin_user)
        self.assertEqual(self.make_record().status_code, 400)

    def test_record_completes_appointment_and_generates_invoice_with_icd10(self):
        s = timezone.now() - timedelta(days=1)
        appt = Appointment.objects.create(patient=self.pt1, doctor=self.doctor, booked_by=self.dr, start_time=s, end_time=s + timedelta(minutes=30))
        svc = Service.objects.create(name="Consult", price="500.00")
        self.client.force_authenticate(self.clinical_user)
        rec = self.make_record(appointment=appt.id).data
        self.assertEqual(rec["appointment"], appt.id)
        self.assertIsNotNone(rec["appointment_start_time"])
        appt.refresh_from_db(); self.assertEqual(appt.status, "completed")
        self.assertEqual(self.make_record(appointment=appt.id).status_code, 400)
        inv = self.c.post(f"/api/records/{rec['id']}/invoice/", dict(items_in=[dict(service=svc.id, quantity=1)]), format="json")
        self.assertEqual(inv.status_code, 201)
        self.assertEqual(inv.data["items"][0]["icd10_code"], "C25.9")
        self.assertEqual(inv.data["total_amount"], "500.00")

    def test_visit_cannot_link_to_another_doctor_or_patient_or_unstarted_appointment(self):
        other_doctor = Doctor.objects.create(user=self.admin_user, specialty="Oncology", license_no="REC-02")
        yesterday, tomorrow = timezone.now() - timedelta(days=1), timezone.now() + timedelta(days=1)
        self.client.force_authenticate(self.dr)
        for patient, doctor, start in [
            (self.pt1, other_doctor, yesterday),
            (self.patient_user_2.patient, self.doctor, yesterday),
            (self.pt1, self.doctor, tomorrow),
        ]:
            with self.subTest(patient=patient.id, doctor=doctor.id, start=start):
                appt = Appointment.objects.create(patient=patient, doctor=doctor, start_time=start,
                                                  end_time=start + timedelta(minutes=30), booked_by=self.dr)
                self.assertEqual(self.make_record(appointment=appt.id).status_code, 400)
                appt.refresh_from_db()
                self.assertEqual(appt.status, Appointment.Status.SCHEDULED)

    def test_follow_up_needs_owning_patient_to_confirm_and_can_be_rebooked_after_cancellation(self):
        self.client.force_authenticate(self.dr)
        record = self.make_record(follow_up_recommendation="Follow up in two weeks").data
        self.assertIsNone(record["follow_up_appointment"])
        self.assertFalse(Appointment.objects.exists())
        endpoint = f"/api/records/{record['id']}/book-follow-up/"
        start = timezone.now() + timedelta(days=14)
        slot = {"start_time": start.isoformat(), "end_time": (start + timedelta(minutes=30)).isoformat()}
        self.assertEqual(self.c.post(endpoint, slot, format="json").status_code, 403)
        self.client.force_authenticate(self.patient_user_2)
        self.assertEqual(self.c.post(endpoint, slot, format="json").status_code, 404)

        self.client.force_authenticate(self.patient_user)
        own_record = self.c.get(f"/api/records/{record['id']}/").data
        self.assertEqual(own_record["follow_up_recommendation"], "Follow up in two weeks")
        response = self.c.post(endpoint, slot, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIn(response.data["id"], [row["id"] for row in self.c.get("/api/appointments/?status=scheduled").data])
        chart = self.c.get("/api/records/chart/").data
        self.assertEqual(chart["visits"][0]["follow_up_appointment"]["id"], response.data["id"])
        appt = Appointment.objects.get(pk=response.data["id"])
        self.assertEqual((appt.booked_by, appt.patient, appt.doctor), (self.patient_user, self.pt1, self.doctor))
        own_record = self.c.get(f"/api/records/{record['id']}/").data
        self.assertEqual(own_record["follow_up_appointment"]["id"], appt.id)
        self.assertEqual(self.c.post(endpoint, slot, format="json").status_code, 400)
        self.assertEqual(self.c.post(f"/api/appointments/{appt.id}/cancel/", {}, format="json").status_code, 200)
        replacement = self.c.post(endpoint, slot, format="json")
        self.assertEqual(replacement.status_code, 201, replacement.data)
        self.assertNotEqual(replacement.data["id"], appt.id)

    def test_treatment_plan_flow(self):
        self.client.force_authenticate(self.clinical_user)
        r = self.c.post("/api/treatment-plans/", dict(patient=self.pt1.id, type="chemotherapy", description="6 cycles", start_date="2026-12-01", end_date="2027-03-01"), format="json")
        self.assertEqual(r.status_code, 201)
        bad = self.c.post("/api/treatment-plans/", dict(patient=self.pt1.id, type="surgery", start_date="2026-12-01", end_date="2026-11-01"), format="json")
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(self.c.patch(f"/api/treatment-plans/{r.data['id']}/", dict(status="completed"), format="json").data["status"], "completed")
        self.client.force_authenticate(self.patient_user)
        self.assertEqual(len(self.c.get("/api/treatment-plans/").data), 1)

    def test_orders_and_results(self):
        self.client.force_authenticate(self.clinical_user)
        o = self.c.post("/api/orders/", dict(patient=self.pt1.id, order_type="lab", description="CBC"), format="json")
        self.assertEqual(o.status_code, 201)
        self.assertEqual(self.c.post(f"/api/orders/{o.data['id']}/result/", dict(result_text=""), format="json").status_code, 400)
        done = self.c.post(f"/api/orders/{o.data['id']}/result/", dict(result_text="WBC 6.1"), format="json")
        self.assertEqual(done.data["status"], "completed")
        self.client.force_authenticate(self.patient_user)
        self.assertEqual(self.c.post(f"/api/orders/{o.data['id']}/result/", dict(result_text="x"), format="json").status_code, 403)

    def test_chart_matches_staff_selection_and_ignores_patient_override(self):
        self.client.force_authenticate(self.dr)
        for patient in (self.pt1, self.patient_profile_2):
            self.assertEqual(self.make_record(patient=patient.pk).status_code, 201)
            self.assertEqual(self.c.post("/api/orders/", {"patient": patient.pk, "order_type": "lab"}).status_code, 201)
            self.assertEqual(self.c.post("/api/treatment-plans/", {
                "patient": patient.pk, "type": "other", "start_date": "2026-11-01",
            }).status_code, 201)

        for patient, other in ((self.pt1, self.patient_profile_2), (self.patient_profile_2, self.pt1)):
            self.client.force_authenticate(self.dr)
            staff = self.c.get(f"/api/records/chart/?patient={patient.pk}").data
            self.client.force_authenticate(patient.user)
            own = self.c.get(f"/api/records/chart/?patient={other.pk}").data
            self.assertEqual(own["mrn"], patient.mrn)
            self.assertEqual(own["viewer"], patient.user_id)
            for section in ("visits", "orders", "plans"):
                self.assertEqual([row["patient"] for row in own[section]], [patient.pk])
                self.assertEqual(own[section], staff[section])
