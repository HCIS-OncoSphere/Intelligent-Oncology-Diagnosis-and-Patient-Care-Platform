"""Appointments: doctors, weekly availability and bookings (F3)."""
from django.conf import settings
from django.db import models


class Doctor(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="doctor")
    specialty = models.CharField(max_length=100)
    license_no = models.CharField(max_length=50, unique=True)
    # Shown on the doctor's profile page; the doctor fills these in.
    bio = models.TextField(blank=True)
    years_experience = models.PositiveSmallIntegerField(null=True, blank=True)
    education = models.CharField(max_length=200, blank=True)
    languages = models.CharField(max_length=200, blank=True)    # comma-separated, e.g. "Arabic, English"
    focus_areas = models.CharField(max_length=300, blank=True)  # comma-separated, e.g. "Breast cancer, Lung cancer"

    def __str__(self):
        return f"Dr. {self.user.get_full_name() or self.user.username}"


class DoctorAvailability(models.Model):
    """One weekly working window, e.g. Monday 09:00-17:00 (day_of_week 0=Monday ... 6=Sunday)."""
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="availability")
    day_of_week = models.PositiveSmallIntegerField()  # 0=Monday ... 6=Sunday
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ["doctor", "day_of_week", "start_time"]


class Appointment(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No-show"

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="appointments")
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="appointments")
    booked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SCHEDULED)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            # the double-booking check and the list filters search by doctor + time
            models.Index(fields=["doctor", "start_time"], name="appt_doctor_start_idx"),
            models.Index(fields=["start_time"], name="appt_start_idx"),
        ]
