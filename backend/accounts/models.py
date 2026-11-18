from django.contrib.auth.models import AbstractUser
from django.db import models


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

    def __str__(self):
        return f"{self.username} ({self.role})"
