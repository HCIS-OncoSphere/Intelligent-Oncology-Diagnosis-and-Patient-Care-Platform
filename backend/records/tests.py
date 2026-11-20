from datetime import timedelta
from django.utils import timezone

from accounts.testing import AccountsTestBase
from appointments.models import Doctor
from billing.models import ICD10Code
from appointments.models import Appointment
from billing.models import Service


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
        appt.refresh_from_db(); self.assertEqual(appt.status, "completed")
        inv = self.c.post(f"/api/records/{rec['id']}/invoice/", dict(items_in=[dict(service=svc.id, quantity=1)]), format="json")
        self.assertEqual(inv.status_code, 201)
        self.assertEqual(inv.data["items"][0]["icd10_code"], "C25.9")
        self.assertEqual(inv.data["total_amount"], "500.00")

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
