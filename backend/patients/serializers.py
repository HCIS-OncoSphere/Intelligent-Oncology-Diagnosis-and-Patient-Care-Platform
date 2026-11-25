from rest_framework import serializers
from .models import Patient

_KNOWN_BLOOD_TYPES = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", ""}


class PatientNameSerializer(serializers.ModelSerializer):
    """What finance staff may see of a patient: who they are (for an invoice), nothing clinical."""
    name = serializers.CharField(source="user.get_full_name", read_only=True)

    class Meta:
        model = Patient
        fields = ["id", "mrn", "name"]
        read_only_fields = fields


class PatientSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="user.get_full_name", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = Patient
        fields = [
            "id", "mrn", "name", "email", "date_of_birth", "gender",
            "phone", "address", "blood_type", "cancer_type",
            "cancer_stage", "emergency_contact", "emergency_contact_phone", "national_id", "emr_patient_id", "created_at"
        ]
        read_only_fields = ["mrn", "emr_patient_id", "created_at"]

    def validate_gender(self, value):
        allowed = Patient.Gender.values
        if value not in allowed:
            raise serializers.ValidationError(
                f"Invalid gender. Allowed values: {allowed}"
            )
        return value

    def validate_blood_type(self, value):
        if value not in _KNOWN_BLOOD_TYPES:
            raise serializers.ValidationError(
                f"Invalid blood type. Allowed values: {sorted(_KNOWN_BLOOD_TYPES - {''})}"
            )
        return value

    def validate_cancer_stage(self, value):
        if value:
            return value.strip().upper()
        return value

    def validate_national_id(self, value):
        value = (value or "").strip()
        if value and not (value.isascii() and value.isdigit() and len(value) == 14):
            raise serializers.ValidationError("National ID must be exactly 14 digits.")
        return value
