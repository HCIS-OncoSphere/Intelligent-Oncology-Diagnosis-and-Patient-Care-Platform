import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


# Random file names, so photo URLs can't be guessed from the user id.
# (Top-level functions because migrations store a reference to them.)
def avatar_upload_to(instance, filename):
    return f"avatars/{instance.pk or 'new'}/{uuid.uuid4().hex}.jpg"


def cover_upload_to(instance, filename):
    return f"covers/{instance.pk or 'new'}/{uuid.uuid4().hex}.jpg"


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        CLINICAL = "clinical", "Clinical Staff"
        PATIENT = "patient", "Patient"
        FINANCE = "finance", "Financial Staff"

    # max_length increased from 10 → 20 to safely accommodate all role values
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PATIENT)
    phone = models.CharField(max_length=30, blank=True)

    # Accounts an admin creates get a temporary password; the person must replace it at first sign-in.
    must_change_password = models.BooleanField(default=False)

    # Enforce unique email address across all user accounts
    email = models.EmailField(unique=True)

    # Profile pictures. Uploads are resized and re-encoded as JPEG (see accounts/profile.py).
    avatar = models.ImageField(upload_to=avatar_upload_to, blank=True)
    cover = models.ImageField(upload_to=cover_upload_to, blank=True)

    def __str__(self):
        return f"{self.username} ({self.role})"


def license_upload_to(instance, filename):
    # random name, so a licence scan's URL can't be guessed; the extension is checked by the serializer
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"licenses/{uuid.uuid4().hex}.{ext}"


class DoctorApplication(models.Model):
    """A doctor's self-registration, waiting for an admin's decision. The login account and Doctor profile
    exist already (account inactive) so that approving is one switch; a rejected doctor may apply again,
    which adds a new application and keeps the old one as history."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="doctor_applications")
    license_document = models.FileField(upload_to=license_upload_to)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    rejection_reason = models.CharField(max_length=500, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name="+")

    class Meta:
        ordering = ["-submitted_at", "-id"]

    def __str__(self):
        return f"{self.user.username} ({self.status})"


class Notification(models.Model):
    """A message shown inside the app (the bell in the header)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=120)
    message = models.CharField(max_length=500, blank=True)
    link = models.CharField(max_length=120, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
