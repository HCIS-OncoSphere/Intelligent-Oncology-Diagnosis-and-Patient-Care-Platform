from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from .models import Patient
from .serializers import PatientNameSerializer, PatientSerializer

# Fields that only clinical staff or admins may update
_CLINICAL_FIELDS = {"cancer_type", "cancer_stage"}


class PatientViewSet(viewsets.ModelViewSet):
    """
    Staff (clinical/admin) see all patients.
    A patient sees and edits only their own profile.
    Patients are restricted to PATCH only (no full PUT replacement).
    Clinical/admin fields (cancer_type, cancer_stage) are read-only for patients.
    """
    serializer_class = PatientSerializer
    permission_classes = [permissions.IsAuthenticated]
    # Patients may only PATCH; staff may still PUT if needed.
    # DELETE is not exposed on any role.
    http_method_names = ["get", "patch", "put", "head", "options"]

    def get_queryset(self):
        qs = Patient.objects.select_related("user").order_by("id")
        u = self.request.user
        if u.role in ("admin", "clinical", "finance"):
            return qs
        return qs.filter(user=u)

    def get_serializer_class(self):
        # Finance staff pick a patient when raising an invoice: they get the name and MRN, nothing medical.
        if getattr(self.request.user, "role", None) == "finance":
            return PatientNameSerializer
        return super().get_serializer_class()

    def perform_update(self, serializer):
        user = self.request.user
        if user.role == "finance":
            raise PermissionDenied("Finance staff cannot edit patient records.")
        # Patients cannot use PUT (full update)
        if user.role == "patient" and self.request.method == "PUT":
            raise PermissionDenied("Patients may only use PATCH for partial updates.")
        # Patients cannot modify clinical fields
        if user.role == "patient":
            attempted = set(self.request.data.keys()) & _CLINICAL_FIELDS
            if attempted:
                raise PermissionDenied(
                    f"Patients may not update clinical fields: {sorted(attempted)}"
                )
        serializer.save()
