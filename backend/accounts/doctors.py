"""Doctor registration (self-service, needs an admin's approval, or created directly by an admin) and
the creation of doctor accounts by an admin."""
import secrets
import string

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework import mixins, permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DoctorApplication, User
from .notify import email_user, notify, notify_admins
from .permissions import IsAdminRole
from .serializers import make_username

LICENSE_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}
LICENSE_MAX_BYTES = 5 * 1024 * 1024


def temporary_password():
    """12 characters with letters and digits, so it passes the password rules."""
    alphabet = string.ascii_letters + string.digits
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(12))
        if any(c.isdigit() for c in pw) and any(c.isalpha() for c in pw):
            return pw


def _clean_email(v):
    v = v.strip().lower()
    if not v.isascii():
        raise serializers.ValidationError("Use an email address written in English letters, like name@example.com.")
    return v


def _check_license_file(f):
    ext = f.name.rsplit(".", 1)[-1].lower() if "." in f.name else ""
    if ext not in LICENSE_EXTENSIONS:
        raise serializers.ValidationError("Upload a PDF, JPG or PNG file.")
    if f.size > LICENSE_MAX_BYTES:
        raise serializers.ValidationError("The file is larger than 5 MB.")
    return f


class DoctorFieldsMixin(serializers.Serializer):
    """The doctor's profile data, shared by self-registration and by the admin's form."""
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    specialty = serializers.CharField(max_length=100)
    license_no = serializers.CharField(max_length=50)
    years_experience = serializers.IntegerField(min_value=0, max_value=70, required=False, allow_null=True)
    education = serializers.CharField(max_length=200, required=False, allow_blank=True)
    languages = serializers.CharField(max_length=200, required=False, allow_blank=True)
    focus_areas = serializers.CharField(max_length=300, required=False, allow_blank=True)
    bio = serializers.CharField(max_length=2000, required=False, allow_blank=True)

    _reapplying_user = None

    def validate_license_no(self, v):
        return v.strip()

    def _check_license_free(self, license_no):
        from appointments.models import Doctor
        taken = Doctor.objects.filter(license_no__iexact=license_no)
        if self._reapplying_user is not None:
            taken = taken.exclude(user=self._reapplying_user)
        if taken.exists():
            raise serializers.ValidationError({"license_no": ["This licence number is already registered."]})

    def _doctor_values(self, d):
        return {k: d[k] for k in ("specialty", "license_no", "years_experience", "education", "languages",
                                  "focus_areas", "bio") if k in d}


class DoctorRegisterSerializer(DoctorFieldsMixin):
    password = serializers.CharField(write_only=True, min_length=8)
    license_document = serializers.FileField()

    def validate_email(self, v):
        v = _clean_email(v)
        existing = User.objects.filter(email__iexact=v).first()
        if existing is None:
            return v
        last = existing.doctor_applications.first()
        # only a doctor whose last application was rejected may apply again with the same email
        if last is not None and last.status == DoctorApplication.Status.REJECTED and not existing.is_active:
            self._reapplying_user = existing
            return v
        if last is not None and last.status == DoctorApplication.Status.PENDING:
            raise serializers.ValidationError("An application with this email is already waiting for review.")
        raise serializers.ValidationError("Email already registered.")

    def validate_license_document(self, f):
        return _check_license_file(f)

    def validate(self, attrs):
        self._check_license_free(attrs["license_no"])
        try:
            validate_password(attrs["password"], user=User(
                email=attrs.get("email"), first_name=attrs.get("first_name"), last_name=attrs.get("last_name")))
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        return attrs

    @transaction.atomic
    def create(self, d):
        from appointments.models import Doctor
        if self._reapplying_user is None:
            user = User.objects.create_user(
                username=make_username(d["email"]), password=d["password"], email=d["email"],
                first_name=d["first_name"], last_name=d["last_name"], phone=d.get("phone", ""),
                role=User.Role.CLINICAL, is_active=False)
            Doctor.objects.create(user=user, **self._doctor_values(d))
        else:
            user = self._reapplying_user
            user.first_name, user.last_name, user.phone = d["first_name"], d["last_name"], d.get("phone", "")
            user.set_password(d["password"])
            user.save()
            Doctor.objects.update_or_create(user=user, defaults=self._doctor_values(d))
        app = DoctorApplication.objects.create(user=user, license_document=d["license_document"])
        name = f"Dr. {user.first_name} {user.last_name}".strip()
        notify_admins("New doctor request", f"{name} ({d['specialty']}) is waiting for approval.", "/admin")
        return app


class DoctorRegisterView(APIView):
    """Public: a doctor asks for an account. It stays switched off until an admin approves it."""
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    throttle_scope = "register"

    def post(self, request):
        s = DoctorRegisterSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        app = s.save()
        return Response({"id": app.id, "status": app.status}, status=201)


# ---------------------------------------------------------------- admin: review requests ----------

class ApplicationSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    email = serializers.CharField(source="user.email", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    doctor = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()
    license_url = serializers.SerializerMethodField()

    class Meta:
        model = DoctorApplication
        fields = ["id", "status", "name", "email", "phone", "doctor", "rejection_reason", "submitted_at",
                  "reviewed_at", "reviewed_by_name", "license_url"]

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_doctor(self, obj):
        d = getattr(obj.user, "doctor", None)
        if d is None:
            return None
        return {"specialty": d.specialty, "license_no": d.license_no, "years_experience": d.years_experience,
                "education": d.education, "languages": d.languages, "focus_areas": d.focus_areas, "bio": d.bio}

    def get_reviewed_by_name(self, obj):
        u = obj.reviewed_by
        return (u.get_full_name() or u.username) if u else ""

    def get_license_url(self, obj):
        return f"/api/admin/doctor-requests/{obj.pk}/license/" if obj.license_document else None


class DoctorRequestViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Admin: the doctors' requests. ?status=pending|approved|rejected filters the list."""
    serializer_class = ApplicationSerializer
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        qs = DoctorApplication.objects.select_related("user__doctor", "reviewed_by")
        status = self.request.query_params.get("status")
        if status in DoctorApplication.Status.values:
            qs = qs.filter(status=status)
        return qs

    def _lock_pending(self):
        """The request, locked, if it is still waiting; otherwise a 400 reply."""
        app = DoctorApplication.objects.select_for_update().select_related("user").get(pk=self.get_object().pk)
        if app.status != DoctorApplication.Status.PENDING:
            return None, Response({"detail": f"This request was already {app.status}."}, status=400)
        return app, None

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def approve(self, request, pk=None):
        app, err = self._lock_pending()
        if err:
            return err
        app.status = DoctorApplication.Status.APPROVED
        app.reviewed_at, app.reviewed_by, app.rejection_reason = timezone.now(), request.user, ""
        app.save()
        app.user.is_active = True
        app.user.save(update_fields=["is_active"])
        notify(app.user, "Your account was approved", "You can sign in now.")
        email_user(app.user, "Your OncoSphere doctor account is approved",
                   "Your doctor registration was approved. You can sign in with your email and password.")
        return Response(ApplicationSerializer(app, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def reject(self, request, pk=None):
        reason = str(request.data.get("reason", "")).strip()
        if not reason:
            return Response({"reason": ["Write the reason for rejecting."]}, status=400)
        if len(reason) > 500:
            return Response({"reason": ["Keep the reason under 500 characters."]}, status=400)
        app, err = self._lock_pending()
        if err:
            return err
        app.status = DoctorApplication.Status.REJECTED
        app.rejection_reason, app.reviewed_at, app.reviewed_by = reason, timezone.now(), request.user
        app.save()
        email_user(app.user, "Your OncoSphere doctor registration",
                   f"Your registration was not approved.\nReason: {reason}\n"
                   "You can apply again with corrected details.")
        return Response(ApplicationSerializer(app, context={"request": request}).data)

    @action(detail=True, methods=["get"])
    def license(self, request, pk=None):
        app = self.get_object()
        if not app.license_document:
            raise Http404
        return FileResponse(app.license_document.open("rb"), as_attachment=False)


# ---------------------------------------------------------------- admin: create accounts ----------

class AdminDoctorSerializer(DoctorFieldsMixin):
    password = serializers.CharField(write_only=True, min_length=8, required=False)
    license_document = serializers.FileField(required=False)

    def validate_email(self, v):
        v = _clean_email(v)
        if User.objects.filter(email__iexact=v).exists():
            raise serializers.ValidationError("Email already registered.")
        return v

    def validate_license_document(self, f):
        return _check_license_file(f)

    def validate(self, attrs):
        self._check_license_free(attrs["license_no"])
        return attrs

    @transaction.atomic
    def create(self, d):
        from appointments.models import Doctor
        pw = d.get("password") or temporary_password()
        user = User.objects.create_user(
            username=make_username(d["email"]), password=pw, email=d["email"], first_name=d["first_name"],
            last_name=d["last_name"], phone=d.get("phone", ""), role=User.Role.CLINICAL, is_active=True,
            must_change_password=True)
        Doctor.objects.create(user=user, **self._doctor_values(d))
        if d.get("license_document"):
            DoctorApplication.objects.create(
                user=user, license_document=d["license_document"], status=DoctorApplication.Status.APPROVED,
                reviewed_at=timezone.now(), reviewed_by=self.context["request"].user)
        user._temporary = None if d.get("password") else pw
        return user


class _AdminCreateView(APIView):
    permission_classes = [IsAdminRole]
    serializer_class = None
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    welcome = "Your OncoSphere account"

    def post(self, request):
        s = self.serializer_class(data=request.data, context={"request": request})
        s.is_valid(raise_exception=True)
        user = s.save()
        pw = user._temporary
        body = (f"An account was created for you on OncoSphere.\nSign in with: {user.email}\n"
                + (f"Temporary password: {pw}\nYou will be asked to choose a new password at your first sign-in."
                   if pw else "Use the password the administrator gave you; you will be asked to change it."))
        emailed = email_user(user, self.welcome, body)
        out = {"id": user.id, "username": user.username, "email": user.email, "role": user.role, "emailed": emailed}
        if pw:
            out["temporary_password"] = pw  # shown once to the admin, never stored in clear text
        return Response(out, status=201)


class AdminDoctorCreateView(_AdminCreateView):
    serializer_class = AdminDoctorSerializer
    welcome = "Your OncoSphere doctor account"
