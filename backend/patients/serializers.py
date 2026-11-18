from rest_framework import serializers
from .models import Patient


class PatientSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="user.get_full_name", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = Patient
        fields = [
            "id", "mrn", "name", "email", "date_of_birth", "gender",
            "phone", "address", "blood_type", "cancer_type",
            "cancer_stage", "emergency_contact", "emr_patient_id", "created_at"
        ]
        read_only_fields = ["mrn", "emr_patient_id", "created_at"]
