from rest_framework import serializers, viewsets
from accounts.permissions import IsAdminRole
from .models import AuditLog, SystemSetting


class AuditSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = AuditLog
        fields = "__all__"


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.order_by("-id")
    serializer_class = AuditSerializer
    permission_classes = [IsAdminRole]


class SettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSetting
        fields = ["id", "key", "value", "description", "updated_at"]


class SystemSettingViewSet(viewsets.ModelViewSet):
    queryset = SystemSetting.objects.order_by("key")
    serializer_class = SettingSerializer
    permission_classes = [IsAdminRole]

    def perform_create(self, s):
        s.save(updated_by=self.request.user)

    def perform_update(self, s):
        s.save(updated_by=self.request.user)
