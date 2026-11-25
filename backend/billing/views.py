from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsBillingReader, IsBillingStaff

from .models import ICD10Code, Invoice, InvoiceItem, Payment, Service


class ICD10Serializer(serializers.ModelSerializer):
    class Meta:
        model = ICD10Code
        fields = "__all__"


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = "__all__"

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value

    def validate_visit_reason(self, value):
        return (value or "").strip()

    def validate(self, attrs):
        # One active service per booking reason: the booking screen and the auto-invoice both pick the first
        # match, so a second one would be silently ignored.
        inst = self.instance
        reason = attrs.get("visit_reason", inst.visit_reason if inst else "")
        active = attrs.get("is_active", inst.is_active if inst else True)
        if reason and active:
            clash = Service.objects.filter(is_active=True, visit_reason__iexact=reason)
            if inst:
                clash = clash.exclude(pk=inst.pk)
            if clash.exists():
                raise serializers.ValidationError(
                    {"visit_reason": [f'"{reason}" is already used by the service "{clash.first().name}".']})
        return attrs


class ICD10ViewSet(viewsets.ModelViewSet):
    queryset = ICD10Code.objects.all()
    serializer_class = ICD10Serializer
    permission_classes = [IsBillingReader]


class ServiceViewSet(viewsets.ModelViewSet):
    """The price list. Staff read it; only billing staff (admins) change it. A service is switched off with is_active=false
    (never deleted: invoices keep pointing at it). The list shows active services; admins add ?all=1 to see
    the switched-off ones too, and can always open one by id to switch it back on."""
    serializer_class = ServiceSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsBillingReader()]
        if self.action == "visit_prices":
            return [IsAuthenticated()]
        return [IsBillingStaff()]

    def get_queryset(self):
        qs = Service.objects.all().order_by("id")
        u = self.request.user
        is_admin = u.is_authenticated and u.role in ("admin",)
        wants_all = self.request.query_params.get("all") in ("1", "true")
        if is_admin and (self.action != "list" or wants_all):
            return qs
        return qs.filter(is_active=True)

    @action(detail=False, methods=["get"], url_path="visit-prices")
    def visit_prices(self, request):
        """What each booking reason costs, for the booking screen (anyone signed in):
        [{"reason": "Chemotherapy session", "service": "Chemotherapy session", "price": "4200.00"}]"""
        out = {}
        for s in Service.objects.filter(is_active=True).exclude(visit_reason="").order_by("id"):
            out.setdefault(s.visit_reason.strip().lower(),
                           {"reason": s.visit_reason.strip(), "service": s.name, "price": str(s.price)})
        return Response(list(out.values()))


class ItemIn(serializers.Serializer):
    service = serializers.PrimaryKeyRelatedField(queryset=Service.objects.filter(is_active=True))
    quantity = serializers.IntegerField(min_value=1, default=1)
    icd10_code = serializers.PrimaryKeyRelatedField(queryset=ICD10Code.objects.all(), required=False, allow_null=True)


class ItemOut(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)

    class Meta:
        model = InvoiceItem
        fields = ["id", "service", "service_name", "icd10_code", "quantity", "unit_price", "line_total"]


class PaymentOut(serializers.ModelSerializer):
    recorded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = ["id", "amount", "method", "transaction_ref", "paid_at", "recorded_by_name"]

    def get_recorded_by_name(self, obj):
        u = obj.recorded_by
        return (u.get_full_name() or u.username) if u else ""


class InvoiceSerializer(serializers.ModelSerializer):
    items = ItemOut(many=True, read_only=True)
    items_in = ItemIn(many=True, write_only=True)
    paid_amount = serializers.SerializerMethodField()
    # read-only extras for the receipt page
    payments = PaymentOut(many=True, read_only=True)
    patient_name = serializers.SerializerMethodField()
    patient_mrn = serializers.CharField(source="patient.mrn", read_only=True)
    visit = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = ["id", "invoice_number", "patient", "patient_name", "patient_mrn", "appointment", "visit", "record",
                  "total_amount", "paid_amount", "status", "issue_date", "due_date", "items", "items_in", "payments"]
        read_only_fields = ["invoice_number", "total_amount", "status", "issue_date"]
        extra_kwargs = {"due_date": {"required": False}}

    def get_paid_amount(self, obj):
        # summed from the prefetched payments, so a list of invoices costs no query per row
        return f"{sum((p.amount for p in obj.payments.all()), Decimal('0.00')):.2f}"

    def get_patient_name(self, obj):
        u = obj.patient.user
        return u.get_full_name() or u.username

    def get_visit(self, obj):
        a = obj.appointment
        if a is None:
            return None
        return {"start_time": a.start_time, "end_time": a.end_time, "doctor_name": str(a.doctor), "reason": a.reason,
                "status": a.status}

    @transaction.atomic
    def create(self, data):
        items = data.pop("items_in")
        data.setdefault("due_date", timezone.now().date() + timedelta(days=14))
        inv = Invoice.objects.create(**data)
        total = Decimal("0.00")
        for it in items:
            svc = it["service"]
            line = svc.price * it["quantity"]
            # ICD-10 fallback chain: explicit code -> service code -> primary diagnosis of the record
            code = it.get("icd10_code") or svc.icd10_code
            if code is None and inv.record_id:
                dx = inv.record.diagnoses.order_by("-is_primary").first()
                code = dx.icd10_code if dx else None
            InvoiceItem.objects.create(invoice=inv, service=svc, icd10_code=code,
                                       quantity=it["quantity"], unit_price=svc.price, line_total=line)
            total += line
        inv.total_amount = total
        inv.save(update_fields=["total_amount"])
        return inv


class PaymentIn(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.01"))
    method = serializers.ChoiceField(choices=Payment.Method.choices)
    transaction_ref = serializers.CharField(required=False, allow_null=True)


class InvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_permissions(self):
        if self.action == "create":
            return [IsBillingStaff()]  # raised by admins; doctors only read them
        return super().get_permissions()

    def get_queryset(self):
        qs = (Invoice.objects.select_related("patient__user", "appointment__doctor__user")
              .prefetch_related("items__service", "payments__recorded_by").order_by("-id"))
        u = self.request.user
        appt = self.request.query_params.get("appointment")  # ?appointment=<id>: the bill of one visit
        if appt:
            if not appt.isdigit():
                raise serializers.ValidationError({"appointment": ["Must be a whole number."]})
            qs = qs.filter(appointment_id=int(appt))
        return qs if u.role in ("admin", "clinical") else qs.filter(patient__user=u)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def pay(self, request, pk=None):
        if request.user.role == "clinical":
            return Response({"detail": "Doctors do not handle payments."}, status=403)
        inv = self.get_object()  # scoped: patients only reach their own invoices
        # lock the row so two simultaneous payments cannot both pass the overpayment check
        inv = Invoice.objects.select_for_update().get(pk=inv.pk)
        if inv.status != Invoice.Status.PENDING:
            return Response({"detail": f"Invoice is {inv.status}."}, status=400)
        s = PaymentIn(data=request.data)
        s.is_valid(raise_exception=True)
        # cash and insurance are handed over at the desk, so only staff record them; patients pay by card
        if request.user.role == "patient" and s.validated_data["method"] != Payment.Method.CARD:
            return Response({"detail": "Cash and insurance payments are recorded at the reception desk."}, status=403)
        if inv.paid_amount + s.validated_data["amount"] > inv.total_amount:
            return Response({"detail": "Payment exceeds the amount due."}, status=400)
        Payment.objects.create(invoice=inv, recorded_by=request.user, **s.validated_data)
        if inv.paid_amount >= inv.total_amount:
            inv.status = Invoice.Status.PAID
            inv.save(update_fields=["status"])
        return Response(InvoiceSerializer(inv).data)
