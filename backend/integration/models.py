from django.db import models


class Hl7Message(models.Model):
    control_id = models.CharField(max_length=40, unique=True)
    message_type = models.CharField(max_length=5)          # ADT, SIU, ORM, ORU
    trigger_event = models.CharField(max_length=5)         # A04, S12, O01, R01 ...
    direction = models.CharField(max_length=3, default="out")
    status = models.CharField(max_length=10, default="queued")  # queued | acked | nacked | failed
    raw_message = models.TextField()
    patient = models.ForeignKey("patients.Patient", null=True, blank=True, on_delete=models.SET_NULL)
    appointment = models.ForeignKey("appointments.Appointment", null=True, blank=True, on_delete=models.SET_NULL)
    order = models.ForeignKey("records.ClinicalOrder", null=True, blank=True, on_delete=models.SET_NULL)
    result = models.ForeignKey("records.OrderResult", null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)


class Hl7Ack(models.Model):
    message = models.ForeignKey(Hl7Message, on_delete=models.CASCADE, related_name="acks")
    ack_code = models.CharField(max_length=2)
    error_text = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
