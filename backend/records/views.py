from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsStaffRole
from appointments.models import Appointment
from billing.models import ICD10Code
from billing.views import InvoiceSerializer
from patients.models import Patient
from .models import (ClinicalOrder, MedicalRecord, OrderResult, Prescription, RecordDiagnosis, TreatmentPlan)


def current_doctor(request):
    doc = getattr(request.user, "doctor", None)
    if doc is None:
        raise serializers.ValidationError("Only users with a doctor profile can do this.")
    return doc


class OwnedQuerysetMixin:
    """Staff see everything; patients see only their own rows. Optional ?patient=<id> filter."""
    patient_path = "patient__user"

    def scope(self, qs):
        u = self.request.user
        if u.role not in ("admin", "clinical"):
            return qs.filter(**{self.patient_path: u})
        pid = self.request.query_params.get("patient")
        return qs.filter(**{self.patient_path.replace("__user", "_id"): pid}) if pid else qs

    def get_permissions(self):
        if self.action not in ("list", "retrieve"):
            return [IsStaffRole()]
        return super().get_permissions()


class DiagnosisIn(serializers.Serializer):
    icd10_code = serializers.PrimaryKeyRelatedField(queryset=ICD10Code.objects.all())
    is_primary = serializers.BooleanField(default=False)


class PrescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prescription
        fields = ["id", "medication", "dosage", "frequency", "duration", "instructions"]


class RecordSerializer(serializers.ModelSerializer):
    diagnoses = serializers.SerializerMethodField()
    prescriptions = PrescriptionSerializer(many=True, read_only=True)
    diagnoses_in = DiagnosisIn(many=True, write_only=True, required=False)
    prescriptions_in = PrescriptionSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = MedicalRecord
        fields = ["id", "patient", "doctor", "appointment", "notes", "created_at",
                  "diagnoses", "prescriptions", "diagnoses_in", "prescriptions_in"]
        read_only_fields = ["doctor", "created_at"]

    def get_diagnoses(self, obj):
        return [{"icd10_code": d.icd10_code_id, "description": d.icd10_code.description, "is_primary": d.is_primary}
                for d in obj.diagnoses.select_related("icd10_code")]

    def validate(self, d):
        appt = d.get("appointment")
        if appt and appt.patient_id != d["patient"].id:
            raise serializers.ValidationError("Appointment belongs to a different patient.")
        dx = d.get("diagnoses_in", [])
        if len({x["icd10_code"].pk for x in dx}) != len(dx):
            raise serializers.ValidationError("Each diagnosis code may appear once.")
        if appt and (appt.start_time > timezone.now() or appt.status != Appointment.Status.SCHEDULED):
            raise serializers.ValidationError("Select a scheduled appointment that has already started.")
        if sum(1 for x in dx if x["is_primary"]) > 1:
            raise serializers.ValidationError("Only one primary diagnosis is allowed.")
        return d

    @transaction.atomic
    def create(self, data):
        dx, rx = data.pop("diagnoses_in", []), data.pop("prescriptions_in", [])
        rec = MedicalRecord.objects.create(doctor=current_doctor(self.context["request"]), **data)
        for x in dx:
            RecordDiagnosis.objects.create(record=rec, **x)
        for x in rx:
            Prescription.objects.create(record=rec, **x)
        if rec.appointment:
            Appointment.objects.filter(pk=rec.appointment_id).update(status=Appointment.Status.COMPLETED)
        return rec


class RecordViewSet(OwnedQuerysetMixin, viewsets.ModelViewSet):
    """Medical history (F4) with ICD-10 diagnoses and prescriptions (F5)."""
    serializer_class = RecordSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return self.scope(MedicalRecord.objects.prefetch_related("diagnoses", "prescriptions").order_by("-created_at"))

    @action(detail=True, methods=["post"])
    def invoice(self, request, pk=None):
        """Generate the invoice for this visit: body {"items_in":[{"service":1,"quantity":1}]}"""
        rec = self.get_object()
        s = InvoiceSerializer(data={"patient": rec.patient_id, "appointment": rec.appointment_id, "record": rec.id,
                                    "items_in": request.data.get("items_in", [])}, context={"request": request})
        s.is_valid(raise_exception=True)
        return Response(InvoiceSerializer(s.save()).data, status=201)


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = TreatmentPlan
        fields = ["id", "patient", "doctor", "record", "type", "description", "start_date", "end_date", "status"]
        read_only_fields = ["doctor"]

    def validate(self, d):
        start = d.get("start_date", getattr(self.instance, "start_date", None))
        end = d.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError("end_date cannot be before start_date.")
        return d


class PlanViewSet(OwnedQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = PlanSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return self.scope(TreatmentPlan.objects.order_by("-start_date"))

    def perform_create(self, serializer):
        serializer.save(doctor=current_doctor(self.request))


class OrderSerializer(serializers.ModelSerializer):
    results = serializers.SerializerMethodField()

    class Meta:
        model = ClinicalOrder
        fields = ["id", "patient", "doctor", "order_type", "description", "status", "ordered_at", "results"]
        read_only_fields = ["doctor", "status", "ordered_at"]

    def get_results(self, o):
        return [{"id": r.id, "result_text": r.result_text, "reported_at": r.reported_at} for r in o.results.all()]


class OrderViewSet(OwnedQuerysetMixin, viewsets.ModelViewSet):
    """Clinical orders (HL7 ORM) and their results (HL7 ORU)."""
    serializer_class = OrderSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return self.scope(ClinicalOrder.objects.prefetch_related("results").order_by("-ordered_at"))

    def perform_create(self, serializer):
        serializer.save(doctor=current_doctor(self.request))

    @action(detail=True, methods=["post"])
    def result(self, request, pk=None):
        order = self.get_object()
        text = (request.data.get("result_text") or "").strip()
        if not text:
            return Response({"result_text": ["This field is required."]}, status=400)
        OrderResult.objects.create(order=order, result_text=text)
        order.status = ClinicalOrder.Status.COMPLETED
        order.save(update_fields=["status"])
        return Response(OrderSerializer(order).data)
