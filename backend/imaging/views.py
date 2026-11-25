"""Imaging module (owner: Aliaa). Phase 2 = study registry + viewer config.
Phase 3 = DICOMweb proxy, annotations, comparison."""
from django.conf import settings
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsStaffRole

from .models import ImagingSeries, ImagingStudy


class SeriesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImagingSeries
        fields = ["id", "orthanc_series_uid", "modality", "num_instances"]


class StudySerializer(serializers.ModelSerializer):
    series = SeriesSerializer(many=True, read_only=True)
    series_in = SeriesSerializer(many=True, write_only=True, required=False)
    # read-only, so staff can see whose study it is without a second lookup
    patient_name = serializers.SerializerMethodField()
    patient_mrn = serializers.CharField(source="patient.mrn", read_only=True)

    class Meta:
        model = ImagingStudy
        fields = ["id", "patient", "patient_name", "patient_mrn", "appointment", "orthanc_study_uid", "modality",
                  "body_part", "description", "study_date", "series", "series_in"]

    def get_patient_name(self, obj):
        u = obj.patient.user
        return u.get_full_name() or u.username

    def create(self, data):
        series = data.pop("series_in", [])
        study = ImagingStudy.objects.create(uploaded_by=self.context["request"].user, **data)
        for s in series:
            ImagingSeries.objects.create(study=study, **s)
        return study

    def update(self, instance, data):
        # DRF refuses nested writes in the default update(); series are only registered at creation
        data.pop("series_in", None)
        return super().update(instance, data)


class StudyViewSet(viewsets.ModelViewSet):
    """Staff register and edit studies; patients can read their own."""
    serializer_class = StudySerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permissions(self):
        return super().get_permissions() if self.action in ("list", "retrieve", "viewer_config") else [IsStaffRole()]

    def get_queryset(self):
        qs = ImagingStudy.objects.select_related("patient__user").prefetch_related("series").order_by("-study_date", "-id")
        u = self.request.user
        if u.role not in ("admin", "clinical"):
            return qs.filter(patient__user=u)
        pid = self.request.query_params.get("patient")
        return qs.filter(patient_id=pid) if pid else qs

    @action(detail=True, methods=["get"], url_path="viewer-config")
    def viewer_config(self, request, pk=None):
        """What the React viewer needs to open this study.
        TODO (Aliaa, Phase 3): point dicomweb_root at the authorised Django proxy instead of Orthanc directly."""
        st = self.get_object()
        return Response({
            "study_uid": st.orthanc_study_uid,
            "series_uids": [s.orthanc_series_uid for s in st.series.all()],
            "dicomweb_root": settings.ORTHANC_URL.rstrip("/") + "/dicom-web",
            "read_only": request.user.role == "patient",
        })
