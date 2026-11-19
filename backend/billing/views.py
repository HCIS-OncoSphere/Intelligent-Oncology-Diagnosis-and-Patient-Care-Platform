from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsStaffRole

from .models import ICD10Code, Invoice, InvoiceItem, Payment, Service


class ICD10Serializer(serializers.ModelSerializer):
    class Meta:
        model = ICD10Code
        fields = "__all__"


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = "__all__"


class ICD10ViewSet(viewsets.ModelViewSet):
    queryset = ICD10Code.objects.all()
    serializer_class = ICD10Serializer
    permission_classes = [IsStaffRole]


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.filter(is_active=True)
    serializer_class = ServiceSerializer
    permission_classes = [IsStaffRole]


class ItemIn(serializers.Serializer):
    service = serializers.PrimaryKeyRelatedField(queryset=Service.objects.filter(is_active=True))
    quantity = serializers.IntegerField(min_value=1, default=1)
    icd10_code = serializers.PrimaryKeyRelatedField(queryset=ICD10Code.objects.all(), required=False, allow_null=True)


class ItemOut(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = ["id", "service", "icd10_code", "quantity", "unit_price", "line_total"]


class InvoiceSerializer(serializers.ModelSerializer):
    items = ItemOut(many=True, read_only=True)
    items_in = ItemIn(many=True, write_only=True)
    paid_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = ["id", "invoice_number", "patient", "appointment", "record", "total_amount", "paid_amount",
                  "status", "issue_date", "due_date", "items", "items_in"]
        read_only_fields = ["invoice_number", "total_amount", "status", "issue_date"]
        extra_kwargs = {"due_date": {"required": False}}

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
            return [IsStaffRole()]
        return super().get_permissions()

    def get_queryset(self):
        qs = Invoice.objects.prefetch_related("items", "payments").order_by("-id")
        u = self.request.user
        return qs if u.role in ("admin", "clinical") else qs.filter(patient__user=u)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def pay(self, request, pk=None):
        inv = self.get_object()  # scoped: patients only reach their own invoices
        # lock the row so two simultaneous payments cannot both pass the overpayment check
        inv = Invoice.objects.select_for_update().get(pk=inv.pk)
        if inv.status != Invoice.Status.PENDING:
            return Response({"detail": f"Invoice is {inv.status}."}, status=400)
        s = PaymentIn(data=request.data)
        s.is_valid(raise_exception=True)
        if inv.paid_amount + s.validated_data["amount"] > inv.total_amount:
            return Response({"detail": "Payment exceeds the amount due."}, status=400)
        Payment.objects.create(invoice=inv, recorded_by=request.user, **s.validated_data)
        if inv.paid_amount >= inv.total_amount:
            inv.status = Invoice.Status.PAID
            inv.save(update_fields=["status"])
        return Response(InvoiceSerializer(inv).data)
