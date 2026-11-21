from django.conf import settings
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsStaffRole
from .dispatch import transmit
from .models import Hl7Message


class Hl7Serializer(serializers.ModelSerializer):
    acks = serializers.SerializerMethodField()

    class Meta:
        model = Hl7Message
        fields = ["id", "control_id", "message_type", "trigger_event", "direction", "status", "raw_message", "patient",
                  "appointment", "order", "result", "created_at", "acks"]

    def get_acks(self, m):
        return [{"ack_code": a.ack_code, "error_text": a.error_text} for a in m.acks.all()]


class Hl7MessageViewSet(viewsets.ReadOnlyModelViewSet):
    """HL7 message log (F10). Resend a failed/queued message with POST .../resend/"""
    queryset = Hl7Message.objects.prefetch_related("acks").order_by("-id")
    serializer_class = Hl7Serializer
    permission_classes = [IsStaffRole]

    @action(detail=True, methods=["post"])
    def resend(self, request, pk=None):
        msg = self.get_object()
        if msg.status not in ("queued", "failed"):
            return Response({"detail": "Only queued or failed messages can be resent."}, status=409)
        return Response(Hl7Serializer(transmit(self.get_object())).data)
