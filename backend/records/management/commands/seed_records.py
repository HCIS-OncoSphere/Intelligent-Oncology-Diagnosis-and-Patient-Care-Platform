from django.core.management import BaseCommand, call_command
from billing.models import ICD10Code, Service


class Command(BaseCommand):
    help = "Prepare synthetic users and the clinical catalog for the Records demo."

    def handle(self, *args, **options):
        call_command("seed_appointments")
        for code, description in [
            ("C25.9", "Malignant neoplasm of pancreas, unspecified"),
            ("Z51.11", "Encounter for antineoplastic chemotherapy"),
        ]:
            ICD10Code.objects.get_or_create(code=code, defaults={"description": description})
        Service.objects.get_or_create(name="Demo consultation", defaults={"price": "500.00"})
