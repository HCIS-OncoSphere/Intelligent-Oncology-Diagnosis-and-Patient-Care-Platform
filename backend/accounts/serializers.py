from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, required=False)
    specialty = serializers.CharField(write_only=True, required=False)
    license_no = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "role", "phone", "is_active", "password", "specialty", "license_no"
        ]
        # is_active and role may only be changed by admins (enforced in views).
        # Marking them here as extra_kwargs to signal intent; object-level
        # enforcement is done in UserViewSet / MeView.patch().
        extra_kwargs = {
            "is_active": {"required": False},
        }

    def create(self, data):
        pw = data.pop("password")
        spec = data.pop("specialty", None)
        lic = data.pop("license_no", None)

        # Use create_user so that password hashing and is_active defaults are
        # handled by Django's user manager instead of raw model instantiation.
        user = User.objects.create_user(**data)
        user.set_password(pw)
        user.save()

        # If the appointments app is installed and a doctor license was given,
        # create the linked Doctor profile.  Only catch ImportError / LookupError
        # (app not installed); let DB integrity errors bubble up.
        if user.role == "clinical" and lic:
            try:
                from appointments.models import Doctor
                Doctor.objects.create(user=user, specialty=spec or "General", license_no=lic)
            except (ImportError, LookupError):
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
    # DOB is required — a missing date of birth must be an explicit error in a
    # medical record system; never silently default.
    date_of_birth = serializers.DateField(required=True)
    gender = serializers.CharField(required=False, default="O")
    phone = serializers.CharField(required=False, allow_blank=True)

    def validate_username(self, v):
        if User.objects.filter(username=v).exists():
            raise serializers.ValidationError("Username already taken.")
        return v

    def validate_email(self, v):
        if User.objects.filter(email=v).exists():
            raise serializers.ValidationError("Email already registered.")
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
        # Only swallow ImportError / LookupError (patients app not installed).
        # Any database or integrity error should propagate so the caller knows
        # the user was created but the patient profile was not.
        try:
            from patients.models import Patient
            Patient.objects.create(
                user=user,
                date_of_birth=d["date_of_birth"],
                gender=d.get("gender", "O"),
                phone=d.get("phone", ""),
            )
        except (ImportError, LookupError):
            pass
        return user
