from django.db import models


class MedicalRecord(models.Model):
    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="records")
    doctor = models.ForeignKey("appointments.Doctor", on_delete=models.PROTECT)
    appointment = models.ForeignKey("appointments.Appointment", null=True, blank=True, on_delete=models.SET_NULL)
    notes = models.TextField(blank=True)
    follow_up_recommendation = models.CharField(max_length=500, blank=True)
    follow_up_appointment = models.ForeignKey(
        "appointments.Appointment", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="follow_up_records",
    )
    created_at = models.DateTimeField(auto_now_add=True)


class RecordDiagnosis(models.Model):
    record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name="diagnoses")
    icd10_code = models.ForeignKey("billing.ICD10Code", on_delete=models.PROTECT)
    is_primary = models.BooleanField(default=False)

    class Meta:
        unique_together = [("record", "icd10_code")]


class Prescription(models.Model):
    record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name="prescriptions")
    medication = models.CharField(max_length=150)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration = models.CharField(max_length=100)
    instructions = models.TextField(blank=True)


class TreatmentPlan(models.Model):
    class Type(models.TextChoices):
        CHEMO = "chemotherapy", "Chemotherapy"
        RADIO = "radiotherapy", "Radiotherapy"
        SURGERY = "surgery", "Surgery"
        IMMUNO = "immunotherapy", "Immunotherapy"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="plans")
    doctor = models.ForeignKey("appointments.Doctor", on_delete=models.PROTECT)
    record = models.ForeignKey(MedicalRecord, null=True, blank=True, on_delete=models.SET_NULL)
    type = models.CharField(max_length=20, choices=Type.choices)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)


class ClinicalOrder(models.Model):
    class Type(models.TextChoices):
        LAB = "lab", "Lab test"
        IMAGING = "imaging", "Imaging"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        ORDERED = "ordered", "Ordered"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="orders")
    doctor = models.ForeignKey("appointments.Doctor", on_delete=models.PROTECT)
    order_type = models.CharField(max_length=10, choices=Type.choices)
    description = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ORDERED)
    ordered_at = models.DateTimeField(auto_now_add=True)


class OrderResult(models.Model):
    order = models.ForeignKey(ClinicalOrder, on_delete=models.CASCADE, related_name="results")
    result_text = models.TextField()
    reported_at = models.DateTimeField(auto_now_add=True)
