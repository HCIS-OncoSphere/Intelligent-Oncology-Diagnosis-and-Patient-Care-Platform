"""Synthetic demo data for the appointments slice: python manage.py seed_appointments

Creates the demo users admin, dr.salma (Mon-Fri 09:00-17:00) and patient1 if they do not exist.
Safe to run many times. A team-wide `seed` command can replace it once it is merged.
"""
from datetime import date, time

from django.core.management.base import BaseCommand

from accounts.models import User
from appointments.models import Doctor, DoctorAvailability
from patients.models import Patient


class Command(BaseCommand):
    help = "Create the demo admin, doctor (with weekly availability) and patient."

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

        pu, created = User.objects.get_or_create(username="patient1", defaults=dict(
            role="patient", first_name="Omar", last_name="Hassan", email="omar@onco.test"))
        if created:
            pu.set_password("Patient12345")
            pu.save()
        Patient.objects.get_or_create(user=pu, defaults=dict(date_of_birth=date(1985, 4, 2), gender="M",
                                                             phone="01000000000"))
        self.stdout.write(self.style.SUCCESS("Seeded admin, dr.salma (Mon-Fri 09-17) and patient1."))
