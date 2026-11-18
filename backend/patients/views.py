from rest_framework import permissions, viewsets
from .models import Patient
from .serializers import PatientSerializer


class PatientViewSet(viewsets.ModelViewSet):
    """
    Staff (clinical/admin) see all patients.
    A patient sees and edits only their own profile.
    """
    serializer_class = PatientSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "patch", "put", "head", "options"]

    def get_queryset(self):
        qs = Patient.objects.select_related("user").order_by("id")
        u = self.request.user
        if u.role in ("admin", "clinical"):
            return qs
        return qs.filter(user=u)
