import uuid

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

    # max_length increased from 10 → 20 to safely accommodate all role values
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PATIENT)
    phone = models.CharField(max_length=30, blank=True)

    # Enforce unique email address across all user accounts
    email = models.EmailField(unique=True)

    # Profile pictures. Uploads are resized and re-encoded as JPEG (see accounts/profile.py).
    avatar = models.ImageField(upload_to=avatar_upload_to, blank=True)
    cover = models.ImageField(upload_to=cover_upload_to, blank=True)

    def __str__(self):
        return f"{self.username} ({self.role})"
