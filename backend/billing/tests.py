from accounts.testing import BaseCase
from billing.models import Invoice, Service


class BillingTests(BaseCase):
    def test_invoice_pay_flow(self):
        svc = Service.objects.create(name="Consult", price="500.00", icd10_code_id="C25.9")
        self.as_doctor()
        r = self.c.post("/api/invoices/", dict(patient=self.pt1.id, items_in=[dict(service=svc.id, quantity=2)]),
                        format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["total_amount"], "1000.00")
        self.assertEqual(r.data["items"][0]["icd10_code"], "C25.9")
        inv = r.data["id"]
        self.as_p1()
        self.assertEqual(self.c.post("/api/invoices/", dict(patient=self.pt1.id, items_in=[]),
                                     format="json").status_code, 403)
        self.assertEqual(self.c.post(f"/api/invoices/{inv}/pay/", dict(amount="1500", method="card"),
                                     format="json").status_code, 400)
        self.assertEqual(self.c.post(f"/api/invoices/{inv}/pay/", dict(amount="400", method="card"),
                                     format="json").data["status"], "pending")
        self.assertEqual(self.c.post(f"/api/invoices/{inv}/pay/", dict(amount="600", method="card"),
                                     format="json").data["status"], "paid")
        self.as_p2()
        self.assertEqual(self.c.get(f"/api/invoices/{inv}/").status_code, 404)

    def test_patient_cannot_mark_cash_paid(self):
        svc = Service.objects.create(name="Consult", price="500.00")
        self.as_doctor()
        inv = self.c.post("/api/invoices/", dict(patient=self.pt1.id, items_in=[dict(service=svc.id)]), format="json").data["id"]
        self.as_p1()
        for method in ("cash", "insurance"):
            self.assertEqual(self.c.post(f"/api/invoices/{inv}/pay/", dict(amount="500", method=method),
                                         format="json").status_code, 403)
        self.as_admin()
        r = self.c.post(f"/api/invoices/{inv}/pay/", dict(amount="500", method="cash"), format="json")
        self.assertEqual(r.data["status"], "paid")
        self.assertEqual(r.data["payments"][0]["method"], "cash")
        self.assertEqual(r.data["items"][0]["service_name"], "Consult")

    def test_catalog_is_staff_only(self):
        self.as_p1()
        self.assertEqual(self.c.get("/api/icd10/").status_code, 403)
        self.as_doctor()
        self.assertEqual(self.c.get("/api/icd10/").status_code, 200)


class VisitBillingTests(BaseCase):
    """Booking a visit opens its invoice; moving and cancelling the visit follow through to the bill."""

    def setUp(self):
        super().setUp()
        from datetime import time
        from appointments.models import DoctorAvailability
        for d in range(7):
            DoctorAvailability.objects.create(doctor=self.doctor, day_of_week=d, start_time=time(8), end_time=time(18))
        self.chemo = Service.objects.create(name="Chemotherapy session", price="4200.00", icd10_code_id="Z51.11",
                                            visit_reason="Chemotherapy session")

    def book(self, reason, days=2, hour=10):
        from datetime import timedelta
        from django.utils import timezone
        s = (timezone.localtime() + timedelta(days=days)).replace(hour=hour, minute=0, second=0, microsecond=0)
        return self.c.post("/api/appointments/", dict(doctor=self.doctor.id, start_time=s.isoformat(),
                                                       end_time=(s + timedelta(minutes=30)).isoformat(), reason=reason),
                           format="json")

    def test_booking_opens_a_pending_invoice(self):
        self.as_p1()
        r = self.book("Chemotherapy session")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["bill"]["status"], "pending")
        self.assertEqual(r.data["bill"]["total"], "4200.00")
        inv = self.c.get(f"/api/invoices/?appointment={r.data['id']}").data
        self.assertEqual(len(inv), 1)
        self.assertEqual(inv[0]["items"][0]["icd10_code"], "Z51.11")
        self.assertEqual(inv[0]["visit"]["reason"], "Chemotherapy session")
        self.assertEqual(inv[0]["due_date"], r.data["start_time"][:10])

    def test_reason_without_a_service_has_no_invoice(self):
        self.as_p1()
        r = self.book("new symptom")
        self.assertEqual(r.status_code, 201)
        self.assertIsNone(r.data["bill"])
        self.assertEqual(Invoice.objects.count(), 0)

    def test_cancel_cancels_an_unpaid_invoice_only(self):
        self.as_p1()
        unpaid = self.book("Chemotherapy session").data
        paid = self.book("Chemotherapy session", hour=12).data
        self.c.post(f"/api/invoices/{paid['bill']['invoice']}/pay/", dict(amount="4200.00", method="card"), format="json")
        for a in (unpaid, paid):
            self.c.post(f"/api/appointments/{a['id']}/cancel/")
        self.assertEqual(Invoice.objects.get(pk=unpaid["bill"]["invoice"]).status, "cancelled")
        self.assertEqual(Invoice.objects.get(pk=paid["bill"]["invoice"]).status, "paid")  # left for a refund

    def test_moving_the_visit_moves_the_due_date(self):
        from datetime import timedelta
        from django.utils import timezone
        self.as_p1()
        a = self.book("Chemotherapy session").data
        s = (timezone.localtime() + timedelta(days=5)).replace(hour=11, minute=0, second=0, microsecond=0)
        self.c.post(f"/api/appointments/{a['id']}/reschedule/",
                    dict(start_time=s.isoformat(), end_time=(s + timedelta(minutes=30)).isoformat()), format="json")
        self.assertEqual(Invoice.objects.get(pk=a["bill"]["invoice"]).due_date, s.date())

    def test_visit_prices_readable_by_patients(self):
        self.as_p1()
        r = self.c.get("/api/services/visit-prices/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, [{"reason": "Chemotherapy session", "service": "Chemotherapy session", "price": "4200.00"}])
        self.assertEqual(self.c.get("/api/services/").status_code, 403)  # the full catalog stays staff-only
