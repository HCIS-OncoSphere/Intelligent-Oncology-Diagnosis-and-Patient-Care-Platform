from django.db.models.signals import post_save
from django.dispatch import receiver

from appointments.models import Appointment
from patients.models import Patient
from records.models import ClinicalOrder, OrderResult
from . import hl7_core as h
from .dispatch import dispatch, patient_fields


def _safe(fn):
    def wrapper(*a, **kw):
        # raw=True means `loaddata` is restoring saved rows (e.g. a database copy):
        # those HL7 messages were already sent and are in the copy, so don't send new ones.
        if kw.get("raw"):
            return
        try:
            fn(*a, **kw)
        except Exception:  # integration must never break clinical workflows
            import logging
            logging.getLogger(__name__).exception("HL7 signal failed")
    return wrapper


@receiver(post_save, sender=Patient)
@_safe
def on_patient(sender, instance, created, **kw):
    trig = "A04" if created else "A08"
    dispatch(h.build_adt(trig, patient_fields(instance)), "ADT", trig, patient=instance)


def _appt(a, trig):
    d = patient_fields(a.patient)
    d.update(id=a.id, start=a.start_time.strftime("%Y%m%d%H%M"), minutes=int((a.end_time - a.start_time).total_seconds() // 60),
             doctor=a.doctor.license_no, reason=a.reason)
    dispatch(h.build_siu(trig, d), "SIU", trig, patient=a.patient, appointment=a)


@receiver(post_save, sender=Appointment)
@_safe
def on_appointment(sender, instance, created, **kw):
    if created:
        _appt(instance, "S12")
    elif instance.status == Appointment.Status.CANCELLED:
        _appt(instance, "S15")


@receiver(post_save, sender=ClinicalOrder)
@_safe
def on_order(sender, instance, created, **kw):
    if created:
        d = patient_fields(instance.patient)
        d.update(order_id=instance.id, order_type=instance.order_type)
        dispatch(h.build_orm(d), "ORM", "O01", patient=instance.patient, order=instance)


@receiver(post_save, sender=OrderResult)
@_safe
def on_result(sender, instance, created, **kw):
    if created:
        o = instance.order
        d = patient_fields(o.patient)
        d.update(order_id=o.id, order_type=o.order_type, result_text=instance.result_text)
        dispatch(h.build_oru(d), "ORU", "R01", patient=o.patient, order=o, result=instance)
