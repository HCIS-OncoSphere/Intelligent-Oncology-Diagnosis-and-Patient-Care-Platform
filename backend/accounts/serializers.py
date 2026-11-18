from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    specialty = serializers.CharField(write_only=True, required=False)
    license_no = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "role", "phone", "is_active", "password", "specialty", "license_no"
        ]

    def create(self, data):
        pw = data.pop("password")
        spec = data.pop("specialty", None)
        lic = data.pop("license_no", None)
        user = User(**data)
        user.set_password(pw)
        user.save()

        # If appointments app is installed and a doctor license was given, link doctor profile
        if user.role == "clinical" and lic:
            try:
                from appointments.models import Doctor
                Doctor.objects.create(user=user, specialty=spec or "General", license_no=lic)
            except Exception:
                pass
        return user

    def update(self, instance, data):
        pw = data.pop("password", None)
        data.pop("specialty", None)
        data.pop("license_no", None)
        for k, v in data.items():
            setattr(instance, k, v)
        if pw:
            instance.set_password(pw)
        instance.save()
        return instance


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    date_of_birth = serializers.DateField(required=False)
    gender = serializers.CharField(required=False, default="O")
    phone = serializers.CharField(required=False, allow_blank=True)

    def validate_username(self, v):
        if User.objects.filter(username=v).exists():
            raise serializers.ValidationError("Username already taken.")
        return v

    def create(self, d):
        user = User.objects.create_user(
            username=d["username"],
            password=d["password"],
            email=d["email"],
            first_name=d["first_name"],
            last_name=d["last_name"],
            phone=d.get("phone", ""),
            role=User.Role.PATIENT,
        )
        try:
            from patients.models import Patient
            Patient.objects.create(
                user=user,
                date_of_birth=d.get("date_of_birth", "2000-01-01"),
                gender=d.get("gender", "O"),
                phone=d.get("phone", ""),
            )
        except Exception:
            pass
        return user
