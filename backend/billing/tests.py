from accounts.testing import BaseCase
from billing.models import Service


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

    def test_catalog_is_staff_only(self):
        self.as_p1()
        self.assertEqual(self.c.get("/api/icd10/").status_code, 403)
        self.as_doctor()
        self.assertEqual(self.c.get("/api/icd10/").status_code, 200)
