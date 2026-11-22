import re
from datetime import date

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


class LoginSerializer(TokenObtainPairSerializer):
    """JWT login that accepts either the username or the email address in the
    "username" field. The response is unchanged: {"access", "refresh"}."""

    def validate(self, attrs):
        ident = (attrs.get(self.username_field) or "").strip()
        if "@" in ident:
            match = User.objects.filter(email__iexact=ident).only("username").first()
            if match:
                ident = match.username
        attrs[self.username_field] = ident
        return super().validate(attrs)


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, required=False)
    specialty = serializers.CharField(write_only=True, required=False)
    license_no = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "role", "phone", "is_active", "password", "specialty", "license_no", "avatar"
        ]
        # the photo is changed through /api/profile/photo/, never here
        read_only_fields = ["avatar"]
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


def make_username(email):
    """Username for a self-registered patient: the part of the email before @, kept to
    letters, digits and . _ + -, with a number added if it's taken (mona.adel, mona.adel2, ...)."""
    base = re.sub(r"[^A-Za-z0-9._+-]", "", email.split("@")[0]).lower()[:30] or "patient"
    name, n = base, 1
    while User.objects.filter(username__iexact=name).exists():
        n += 1
        name = f"{base}{n}"
    return name


class RegisterSerializer(serializers.Serializer):
    GENDERS = [("M", "Male"), ("F", "Female"), ("O", "Other")]

    # No username field: the system makes one from the email (see make_username) and
    # patients sign in with their email. A "username" sent by an old client is ignored.
    password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField()
    # names may be in any language (Arabic included)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    # DOB is required — a missing date of birth must be an explicit error in a
    # medical record system; never silently default.
    date_of_birth = serializers.DateField(required=True)
    gender = serializers.ChoiceField(choices=GENDERS, required=False, default="O")
    phone = serializers.CharField(required=False, allow_blank=True, max_length=30)

    def validate_email(self, v):
        v = v.strip().lower()
        if not v.isascii():
            raise serializers.ValidationError("Use an email address written in English letters, like name@example.com.")
        if User.objects.filter(email__iexact=v).exists():
            raise serializers.ValidationError("Email already registered.")
        return v

    def validate_date_of_birth(self, v):
        if v > date.today():
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        if v.year < 1900:
            raise serializers.ValidationError("Enter a valid date of birth.")
        return v

    def validate(self, attrs):
        # Run the AUTH_PASSWORD_VALIDATORS from settings (at least 8 characters,
        # not only numbers), same as Django's own forms.
        candidate = User(
            email=attrs.get("email"),
            first_name=attrs.get("first_name"), last_name=attrs.get("last_name"),
        )
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        return attrs

    @transaction.atomic
    def create(self, d):
        # Atomic: if the patient profile cannot be created, the login account
        # is rolled back too, so the username/email stay free to retry.
        user = User.objects.create_user(
            username=make_username(d["email"]),
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
