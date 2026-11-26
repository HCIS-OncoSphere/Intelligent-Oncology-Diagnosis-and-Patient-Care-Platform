"""Reports. Feature F7: dashboards and CSV export.

Reports read the tables of other apps (billing, records). Those apps are imported only when
they are installed, so the reports keep working (with zeros for the missing parts) before they are merged.

  GET /api/reports/summary/?days=30   staff. Appointment numbers cover the last `days` days;
                                      patients and billing totals are all time.
  GET /api/reports/export/?type=invoices|appointments|patients       staff (CSV)
"""
import csv
from datetime import timedelta

from django.apps import apps
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsStaffRole
from appointments.models import Appointment
from patients.models import Patient

EXPORT_TYPES = ("invoices", "appointments", "patients")


def _model(app_label, name):
    """Return another slice's model, or None while that app is not installed yet."""
    return apps.get_model(app_label, name) if apps.is_installed(app_label) else None


def _counts(qs, field):
    return {k: n for k, n in qs.values_list(field).annotate(n=Count("id")).order_by(field)}


class SummaryView(APIView):
    """Aggregations for the dashboards (F7)."""
    permission_classes = [IsStaffRole]

    def get(self, request):
        try:
            days = max(1, min(365, int(request.query_params.get("days", 30))))
        except ValueError:
            return Response({"days": ["Must be a whole number of days."]}, status=400)
        now = timezone.now()
        since = now - timedelta(days=days)

        # every appointment number covers the chosen period: visits that started in the last `days` days.
        # Future bookings are counted separately in upcoming_appointments.
        appts = Appointment.objects.filter(start_time__gte=since, start_time__lt=now)
        per_day = (appts.annotate(d=TruncDate("start_time"))
                   .values("d").annotate(n=Count("id")).order_by("d"))
        per_doctor = (appts.exclude(status=Appointment.Status.CANCELLED)
                      .values("doctor_id", "doctor__user__first_name", "doctor__user__last_name", "doctor__user__username")
                      .annotate(n=Count("id")).order_by("-n"))
        # totals and the no-show rate come from the group-by results below, so they cost no extra queries
        by_status = _counts(appts, "status")
        by_gender = _counts(Patient.objects.all(), "gender")
        done = by_status.get(Appointment.Status.COMPLETED, 0) + by_status.get(Appointment.Status.NO_SHOW, 0)
        no_show_rate = round(by_status.get(Appointment.Status.NO_SHOW, 0) / done, 3) if done else 0

        data = {
            "period_days": days,
            "patients_total": sum(by_gender.values()),
            "patients_by_gender": by_gender,
            "patients_by_cancer_type": _counts(Patient.objects.exclude(cancer_type=""), "cancer_type"),
            "appointments_total": sum(by_status.values()),
            "appointments_by_status": by_status,
            "appointments_per_day": [{"date": r["d"].isoformat(), "count": r["n"]} for r in per_day],
            "appointments_by_doctor": [
                {"doctor": r["doctor_id"],
                 "name": f'{r["doctor__user__first_name"]} {r["doctor__user__last_name"]}'.strip()
                 or r["doctor__user__username"],
                 "count": r["n"]} for r in per_doctor],
            "upcoming_appointments": Appointment.objects.filter(start_time__gte=now, status=Appointment.Status.SCHEDULED).count(),
            "no_show_rate": no_show_rate,
            "top_diagnoses": [],
            "invoices_by_status": {},
            "revenue_collected": 0,
            "revenue_outstanding": 0,
            "revenue_by_month": [],
            "modules": {"billing": apps.is_installed("billing"), "records": apps.is_installed("records")},
        }
        # kept for older clients that read the 30-day key name from the guide
        data["appointments_per_day_30d"] = data["appointments_per_day"]

        RecordDiagnosis = _model("records", "RecordDiagnosis")
        if RecordDiagnosis is not None:
            top = (RecordDiagnosis.objects.values("icd10_code", "icd10_code__description")
                   .annotate(n=Count("id")).order_by("-n")[:5])
            data["top_diagnoses"] = [{"code": r["icd10_code"], "description": r["icd10_code__description"],
                                      "count": r["n"]} for r in top]

        Invoice, Payment = _model("billing", "Invoice"), _model("billing", "Payment")
        if Invoice is not None and Payment is not None:
            data["invoices_by_status"] = _counts(Invoice.objects.all(), "status")
            collected = Payment.objects.aggregate(s=Sum("amount"))["s"] or 0
            billed_pending = Invoice.objects.filter(status="pending").aggregate(s=Sum("total_amount"))["s"] or 0
            paid_on_pending = Payment.objects.filter(invoice__status="pending").aggregate(s=Sum("amount"))["s"] or 0
            data["revenue_collected"] = collected
            data["revenue_outstanding"] = billed_pending - paid_on_pending  # what patients still owe
            months = (Payment.objects.annotate(m=TruncMonth("paid_at")).values("m")
                      .annotate(total=Sum("amount")).order_by("m"))
            data["revenue_by_month"] = [{"month": r["m"].strftime("%Y-%m"), "total": r["total"]} for r in months]
        return Response(data)


class ExportView(APIView):
    """CSV export: /api/reports/export/?type=invoices|appointments|patients"""
    permission_classes = [IsStaffRole]

    def get(self, request):
        kind = request.query_params.get("type", "appointments")
        if kind not in EXPORT_TYPES:
            return Response({"detail": f"Unknown type. Use one of: {', '.join(EXPORT_TYPES)}."}, status=400)
        Invoice = _model("billing", "Invoice")
        if kind == "invoices" and Invoice is None:
            return Response({"detail": "Invoices are not available yet (billing app not installed)."}, status=400)

        stamp = timezone.localtime().strftime("%Y%m%d")
        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="{kind}_{stamp}.csv"'
        resp.write("﻿")  # BOM so Excel opens UTF-8 (Arabic names) correctly
        w = csv.writer(resp)
        if kind == "invoices":
            w.writerow(["invoice_number", "patient_mrn", "total", "status", "issue_date", "due_date"])
            for i in Invoice.objects.select_related("patient").order_by("id"):
                w.writerow([i.invoice_number, i.patient.mrn, i.total_amount, i.status, i.issue_date, i.due_date])
        elif kind == "appointments":
            w.writerow(["id", "patient_mrn", "patient_name", "doctor", "doctor_license", "start", "end", "status",
                        "reason"])
            appointments = Appointment.objects.select_related("patient__user", "doctor__user")
            # Clinical accounts are doctors, so their download should contain only their own schedule.
            if request.user.role == "clinical":
                appointments = appointments.filter(doctor__user=request.user)
            for a in appointments.order_by("start_time"):
                w.writerow([a.id, a.patient.mrn, a.patient.user.get_full_name() or a.patient.user.username,
                            str(a.doctor), a.doctor.license_no, timezone.localtime(a.start_time).isoformat(),
                            timezone.localtime(a.end_time).isoformat(), a.status, a.reason])
        else:
            w.writerow(["mrn", "gender", "date_of_birth", "cancer_type", "cancer_stage", "created_at"])
            for p in Patient.objects.order_by("id"):
                w.writerow([p.mrn, p.gender, p.date_of_birth, p.cancer_type, p.cancer_stage, p.created_at.date()])
        return resp
