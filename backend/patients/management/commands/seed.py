"""Synthetic demo data:  python manage.py seed"""
from datetime import date, time
from django.core.management.base import BaseCommand

from accounts.models import User
from appointments.models import Doctor, DoctorAvailability
from billing.models import ICD10Code, Service
from patients.models import Patient


class Command(BaseCommand):
    def handle(self, *args, **opts):
        admin, _ = User.objects.get_or_create(username="admin", defaults=dict(role="admin", is_staff=True, is_superuser=True, email="admin@onco.test"))
        admin.set_password("Admin12345"); admin.save()

        du, _ = User.objects.get_or_create(username="dr.salma", defaults=dict(role="clinical", first_name="Salma", last_name="Nabil", email="salma@onco.test"))
        du.set_password("Doctor12345"); du.save()
        doc, _ = Doctor.objects.get_or_create(user=du, defaults=dict(specialty="Oncology", license_no="EG-ONC-001"))
        for d in range(0, 5):  # Mon-Fri 09:00-17:00
            DoctorAvailability.objects.get_or_create(doctor=doc, day_of_week=d, defaults=dict(start_time=time(9), end_time=time(17)))

        pu, _ = User.objects.get_or_create(username="patient1", defaults=dict(role="patient", first_name="Omar", last_name="Hassan", email="omar@onco.test"))
        pu.set_password("Patient12345"); pu.save()
        Patient.objects.get_or_create(user=pu, defaults=dict(date_of_birth=date(1985, 4, 2), gender="M", phone="01000000000", cancer_type="Pancreatic", cancer_stage="II"))

        for code, desc in [("C25.9", "Malignant neoplasm of pancreas, unspecified"), ("C34.90", "Malignant neoplasm of unspecified part of bronchus or lung"), ("Z51.11", "Encounter for antineoplastic chemotherapy")]:
            ICD10Code.objects.get_or_create(code=code, defaults=dict(description=desc, category="Neoplasms"))
        for name, price, code in [("Oncology consultation", "500.00", "C25.9"), ("CT scan - abdomen", "1800.00", "C25.9"), ("Chemotherapy session", "4200.00", "Z51.11")]:
            Service.objects.get_or_create(name=name, defaults=dict(price=price, icd10_code_id=code))
        self.stdout.write(self.style.SUCCESS("Seeded: admin / dr.salma / patient1"))

        # sample clinical data for patient1 (idempotent)
        from records.models import MedicalRecord, RecordDiagnosis, Prescription, TreatmentPlan
        pt = Patient.objects.get(user=pu)
        if not MedicalRecord.objects.filter(patient=pt).exists():
            rec = MedicalRecord.objects.create(patient=pt, doctor=doc, notes="Initial oncology consultation. CT abdomen requested.")
            RecordDiagnosis.objects.create(record=rec, icd10_code_id="C25.9", is_primary=True)
            Prescription.objects.create(record=rec, medication="Ondansetron", dosage="8 mg", frequency="twice daily", duration="7 days")
            TreatmentPlan.objects.create(patient=pt, doctor=doc, record=rec, type="chemotherapy", description="FOLFIRINOX x6 cycles", start_date=date(2026, 12, 1))
