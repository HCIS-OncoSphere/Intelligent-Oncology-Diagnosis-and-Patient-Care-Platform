"""Synthetic demo data for the appointments slice: python manage.py seed_appointments

Creates the demo users admin, dr.salma (Mon-Fri 09:00-17:00) and patients patient1..patient5 if they do not exist.
Safe to run many times. A team-wide `seed` command can replace it once it is merged.
"""
from datetime import date, time

from django.core.management.base import BaseCommand

from accounts.models import User
from appointments.models import Doctor, DoctorAvailability
from patients.models import Patient

# username, first name, last name, birth date, gender, phone, cancer type (synthetic)
DEMO_PATIENTS = [
    ("patient1", "Omar", "Hassan", date(1985, 4, 2), "M", "01000000000", ""),
    ("patient2", "Mona", "Adel", date(1978, 9, 14), "F", "01000000002", "Breast"),
    ("patient3", "Youssef", "Karim", date(1960, 1, 30), "M", "01000000003", "Lung"),
    ("patient4", "Nour", "Samir", date(1992, 6, 21), "F", "01000000004", "Thyroid"),
    ("patient5", "Hany", "Fouad", date(1971, 12, 5), "M", "01000000005", "Colorectal"),
]


class Command(BaseCommand):
    help = "Create the demo admin, doctor (with weekly availability) and patients."

    def handle(self, *args, **opts):
        admin, created = User.objects.get_or_create(username="admin", defaults=dict(
            role="admin", is_staff=True, is_superuser=True, email="admin@onco.test"))
        if created:
            admin.set_password("Admin12345")
            admin.save()

        du, created = User.objects.get_or_create(username="dr.salma", defaults=dict(
            role="clinical", first_name="Salma", last_name="Nabil", email="salma@onco.test"))
        if created:
            du.set_password("Doctor12345")
            du.save()
        doc, _ = Doctor.objects.get_or_create(user=du, defaults=dict(specialty="Oncology", license_no="EG-ONC-001"))
        for d in range(0, 5):  # Monday-Friday 09:00-17:00
            DoctorAvailability.objects.get_or_create(doctor=doc, day_of_week=d,
                                                     defaults=dict(start_time=time(9), end_time=time(17)))

        for username, first, last, born, gender, phone, cancer in DEMO_PATIENTS:
            pu, created = User.objects.get_or_create(username=username, defaults=dict(
                role="patient", first_name=first, last_name=last, email=f"{username}@onco.test"))
            if created:
                pu.set_password("Patient12345")
                pu.save()
            Patient.objects.get_or_create(user=pu, defaults=dict(date_of_birth=born, gender=gender, phone=phone,
                                                                 cancer_type=cancer))
        self.stdout.write(self.style.SUCCESS("Seeded admin, dr.salma (Mon-Fri 09-17) and patient1..patient5."))
