from django.conf import settings
from django.db import models

MODALITIES = [("CT", "CT"), ("MR", "MRI"), ("PT", "PET"), ("CR", "X-ray"), ("US", "Ultrasound"), ("OT", "Other")]


class ImagingStudy(models.Model):
    """A DICOM study stored in Orthanc and linked to a patient."""
    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="studies")
    appointment = models.ForeignKey("appointments.Appointment", null=True, blank=True, on_delete=models.SET_NULL)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    orthanc_study_uid = models.CharField(max_length=128, unique=True)
    modality = models.CharField(max_length=2, choices=MODALITIES)
    body_part = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=200, blank=True)
    study_date = models.DateField()


class ImagingSeries(models.Model):
    study = models.ForeignKey(ImagingStudy, on_delete=models.CASCADE, related_name="series")
    orthanc_series_uid = models.CharField(max_length=128, unique=True)
    modality = models.CharField(max_length=2, choices=MODALITIES)
    num_instances = models.PositiveIntegerField(default=0)
