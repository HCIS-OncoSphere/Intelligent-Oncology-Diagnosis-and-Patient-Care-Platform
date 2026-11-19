from decimal import Decimal

from django.conf import settings
from django.db import models


class ICD10Code(models.Model):
    code = models.CharField(max_length=10, primary_key=True)
    description = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True)


class Service(models.Model):
    name = models.CharField(max_length=150)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    icd10_code = models.ForeignKey(ICD10Code, null=True, blank=True, on_delete=models.SET_NULL)
    is_active = models.BooleanField(default=True)


class Invoice(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    invoice_number = models.CharField(max_length=20, unique=True, blank=True)
    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="invoices")
    appointment = models.ForeignKey("appointments.Appointment", null=True, blank=True, on_delete=models.SET_NULL)
    record = models.ForeignKey("records.MedicalRecord", null=True, blank=True, on_delete=models.SET_NULL)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    issue_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()

    def save(self, *a, **kw):
        super().save(*a, **kw)
        if not self.invoice_number:
            self.invoice_number = f"INV-{self.pk:06d}"
            super().save(update_fields=["invoice_number"])

    @property
    def paid_amount(self):
        return self.payments.aggregate(s=models.Sum("amount"))["s"] or Decimal("0.00")


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    icd10_code = models.ForeignKey(ICD10Code, null=True, blank=True, on_delete=models.SET_NULL)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        CARD = "card", "Card"
        INSURANCE = "insurance", "Insurance"

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=10, choices=Method.choices)
    transaction_ref = models.CharField(max_length=60, unique=True, null=True, blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    paid_at = models.DateTimeField(auto_now_add=True)
