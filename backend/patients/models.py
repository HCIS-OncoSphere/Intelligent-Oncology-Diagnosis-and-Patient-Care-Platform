import uuid
from django.conf import settings
from django.db import models


def new_mrn():
    return "MRN-" + uuid.uuid4().hex[:8].upper()


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
    emr_patient_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.mrn} {self.user.get_full_name() or self.user.username}"
