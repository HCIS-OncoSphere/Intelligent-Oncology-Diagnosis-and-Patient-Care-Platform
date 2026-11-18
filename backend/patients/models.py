import uuid
from django.conf import settings
from django.db import models


def new_mrn():
    # Use 12 hex chars instead of 8 to reduce collision probability from
    # ~1-in-16M to ~1-in-281T. The unique=True DB constraint remains the
    # authoritative collision guard.
    return "MRN-" + uuid.uuid4().hex[:12].upper()


class Patient(models.Model):
    class Gender(models.TextChoices):
        MALE = "M", "Male"
        FEMALE = "F", "Female"
        OTHER = "O", "Other"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="patient")
    mrn = models.CharField(max_length=20, unique=True, default=new_mrn)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=Gender.choices, default=Gender.OTHER)
    phone = models.CharField(max_length=30, blank=True)
    address = models.CharField(max_length=255, blank=True)
    blood_type = models.CharField(max_length=3, blank=True)
    cancer_type = models.CharField(max_length=100, blank=True)
    cancer_stage = models.CharField(max_length=20, blank=True)
    emergency_contact = models.CharField(max_length=100, blank=True)
    # NOTE: emr_patient_id uses null=True + unique=True intentionally.
    # SQLite (and PostgreSQL) treat each NULL as distinct, so multiple rows
    # with NULL are allowed while still enforcing uniqueness for non-NULL
    # values.  The unique constraint is enforced at the DB level only.
    emr_patient_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.mrn} {self.user.get_full_name() or self.user.username}"
