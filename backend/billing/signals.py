"""Bills follow appointments. Billing listens to Appointment saves, so the appointments app never imports billing.

booked     -> a pending invoice for the service whose visit_reason matches the booking reason (none if no match)
moved      -> the pending invoice's due date moves with the visit
cancelled  -> the invoice is cancelled too, if nothing has been paid on it yet (a paid one is left for a refund)
"""
import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from appointments.models import Appointment
from .models import Invoice, InvoiceItem, Service

log = logging.getLogger(__name__)


def service_for_reason(reason):
    reason = (reason or "").strip()
    if not reason:
        return None
    return Service.objects.filter(is_active=True, visit_reason__iexact=reason).order_by("id").first()


def open_visit_invoice(appt):
    svc = service_for_reason(appt.reason)
    if svc is None or Invoice.objects.filter(appointment=appt).exists():
        return None
    inv = Invoice.objects.create(patient=appt.patient, appointment=appt, total_amount=svc.price,
                                 due_date=timezone.localtime(appt.start_time).date())
    InvoiceItem.objects.create(invoice=inv, service=svc, icd10_code=svc.icd10_code, quantity=1,
                               unit_price=svc.price, line_total=svc.price)
    return inv


@receiver(post_save, sender=Appointment)
def bill_appointment(sender, instance, created, raw=False, **kw):
    if raw:  # loaddata restoring saved rows: their invoices are in the copy already
        return
    try:
        # a savepoint: if billing fails, only its own changes roll back, not the booking around it
        with transaction.atomic():
            if created:
                if instance.status != Appointment.Status.CANCELLED:
                    open_visit_invoice(instance)
                return
            pending = Invoice.objects.filter(appointment=instance, status=Invoice.Status.PENDING)
            if instance.status == Appointment.Status.CANCELLED:
                pending.filter(payments__isnull=True).update(status=Invoice.Status.CANCELLED)
            elif instance.status == Appointment.Status.SCHEDULED:
                pending.update(due_date=timezone.localtime(instance.start_time).date())
    except Exception:  # a billing problem must never stop a booking; staff can still bill by hand
        log.exception("Could not update the invoice for appointment %s", instance.pk)
