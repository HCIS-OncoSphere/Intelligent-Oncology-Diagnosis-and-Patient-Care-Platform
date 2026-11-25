import socketserver, threading
from datetime import timedelta
from django.test import override_settings
from django.utils import timezone

from accounts.testing import BaseCase
from integration import hl7_core as h
from integration.models import Hl7Message


class EMR(socketserver.BaseRequestHandler):
    """Tiny fake EMR for tests: validates and ACKs."""
    def handle(self):
        buf = b""
        while h.EB not in buf:
            buf += self.request.recv(4096)
        raw = h.unframe(buf)
        ok, err = h.validate(raw)
        self.request.sendall(h.frame(h.build_ack(raw, ok, err)))


class Hl7Tests(BaseCase):
    def test_patient_registration_logs_adt_a04(self):
        r = self.c.post("/api/auth/register/", dict(username="new", password="Secret1234", email="n@x.com", first_name="N", last_name="M", date_of_birth="2000-01-01", gender="F"), format="json")
        self.assertEqual(r.status_code, 201)
        m = Hl7Message.objects.filter(message_type="ADT", trigger_event="A04").latest("id")
        self.assertEqual(m.status, "queued")          # HL7_ENABLED is off by default
        self.assertTrue(h.validate(m.raw_message)[0])

    def test_loaddata_does_not_send_new_messages(self):
        # Restoring a database copy (dumpdata -> loaddata) must not create duplicate HL7 messages.
        import json, os, tempfile
        from django.core import serializers
        from django.core.management import call_command
        data = serializers.serialize("json", type(self.pt1).objects.filter(pk=self.pt1.pk))
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            f.write(data)
        try:
            before = Hl7Message.objects.count()
            call_command("loaddata", f.name, verbosity=0)
            self.assertEqual(Hl7Message.objects.count(), before)
        finally:
            os.remove(f.name)

    def test_profile_update_logs_adt_a08(self):
        self.as_p1()
        self.c.patch(f"/api/patients/{self.pt1.id}/", dict(address="Cairo"), format="json")
        self.assertTrue(Hl7Message.objects.filter(trigger_event="A08", patient=self.pt1).exists())

    def test_appointment_siu_and_cancel(self):
        self.as_p1()
        s = timezone.now() + timedelta(days=2)
        a = self.c.post("/api/appointments/", dict(doctor=self.doctor.id, start_time=s.isoformat(), end_time=(s + timedelta(minutes=30)).isoformat()), format="json")
        self.assertEqual(a.status_code, 201)
        self.assertTrue(Hl7Message.objects.filter(trigger_event="S12").exists())
        self.c.post(f"/api/appointments/{a.data['id']}/cancel/")
        self.assertTrue(Hl7Message.objects.filter(trigger_event="S15").exists())

    def test_order_orm_and_result_oru(self):
        self.as_doctor()
        o = self.c.post("/api/orders/", dict(patient=self.pt1.id, order_type="lab", description="CBC"), format="json")
        self.assertTrue(Hl7Message.objects.filter(message_type="ORM").exists())
        self.c.post(f"/api/orders/{o.data['id']}/result/", dict(result_text="WBC 6.1 | normal"), format="json")
        oru = Hl7Message.objects.get(message_type="ORU")
        self.assertTrue(h.validate(oru.raw_message)[0])      # '|' in the text was escaped, message still valid

    def test_send_to_emr_acked(self):
        srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), EMR)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        with override_settings(HL7_ENABLED=True, HL7_HOST="127.0.0.1", HL7_PORT=srv.server_address[1]):
            self.as_doctor()
            self.c.post("/api/orders/", dict(patient=self.pt1.id, order_type="imaging"), format="json")
        srv.shutdown(); srv.server_close()
        m = Hl7Message.objects.filter(message_type="ORM").latest("id")
        self.assertEqual(m.status, "acked")
        self.assertEqual(m.acks.first().ack_code, "AA")

    def test_emr_down_marks_failed_but_api_still_works(self):
        with override_settings(HL7_ENABLED=True, HL7_HOST="127.0.0.1", HL7_PORT=1):
            self.as_doctor()
            r = self.c.post("/api/orders/", dict(patient=self.pt1.id, order_type="lab"), format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Hl7Message.objects.filter(message_type="ORM").latest("id").status, "failed")

    def test_log_visibility(self):
        self.as_p1()
        self.assertEqual(self.c.get("/api/hl7/messages/").status_code, 403)
        self.as_doctor()
        self.assertEqual(self.c.get("/api/hl7/messages/").status_code, 200)
