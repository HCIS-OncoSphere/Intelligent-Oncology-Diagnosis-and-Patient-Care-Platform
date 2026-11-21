"""Profile pages for patients and doctors, plus profile-photo and cover uploads.

GET    /api/profile/             your own profile
GET    /api/profile/<user_id>/   someone else's profile (rules in _can_view)
PATCH  /api/profile/             edit your own contact and "about" details
POST   /api/profile/photo/       multipart: kind=avatar|cover, file=<image>
DELETE /api/profile/photo/?kind=avatar|cover
"""
from datetime import date, timedelta
from io import BytesIO

from django.core.files.base import ContentFile
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework import permissions, serializers, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
# avatar: square crop; cover: wide crop (about 4:1)
SIZES = {"avatar": (512, 512), "cover": (1600, 400)}


def _url(request, image):
    # relative (/media/...), so it loads through the same host and proxy as the page
    return image.url if image else None


def _age(born):
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def _can_view(viewer, target):
    """You can always see yourself. Anyone signed in can see a doctor's public profile.
    Only staff (clinical/admin) can see a patient's profile. Admin profiles are private."""
    if viewer == target or viewer.role == "admin":
        return True
    if target.role == "clinical":
        return True
    if target.role == "patient":
        return viewer.role == "clinical"
    return False


def _patient_block(request, patient):
    from appointments.models import Appointment

    now = timezone.now()
    upcoming = (patient.appointments.select_related("doctor__user")
                .filter(start_time__gte=now, status=Appointment.Status.SCHEDULED)
                .order_by("start_time")[:3])
    block = {
        "mrn": patient.mrn,
        "date_of_birth": patient.date_of_birth,
        "age": _age(patient.date_of_birth),
        "gender": patient.gender,
        "phone": patient.phone,
        "address": patient.address,
        "blood_type": patient.blood_type,
        "cancer_type": patient.cancer_type,
        "cancer_stage": patient.cancer_stage,
        "emergency_contact": patient.emergency_contact,
        "upcoming": [{
            "id": a.id, "start_time": a.start_time, "reason": a.reason,
            "doctor": a.doctor.user.get_full_name() or a.doctor.user.username,
        } for a in upcoming],
        "active_plan": None, "latest_result": None, "prescriptions": 0, "care_team": [],
    }

    doctors = {a.doctor for a in patient.appointments.select_related("doctor__user")}
    try:  # the records app is a separate slice; the profile still works without it
        from records.models import OrderResult, Prescription, TreatmentPlan

        plan = (patient.plans.filter(status=TreatmentPlan.Status.ACTIVE)
                .select_related("doctor__user").order_by("-start_date").first())
        if plan:
            block["active_plan"] = {"type": plan.get_type_display(), "description": plan.description,
                                    "start_date": plan.start_date}
        result = (OrderResult.objects.filter(order__patient=patient)
                  .select_related("order").order_by("-reported_at").first())
        if result:
            block["latest_result"] = {"order_type": result.order.get_order_type_display(),
                                      "description": result.order.description,
                                      "reported_at": result.reported_at}
        block["prescriptions"] = Prescription.objects.filter(record__patient=patient).count()
        doctors |= {p.doctor for p in patient.plans.select_related("doctor__user")}
    except (ImportError, LookupError):
        pass

    block["care_team"] = [{
        "user_id": d.user_id, "name": d.user.get_full_name() or d.user.username,
        "specialty": d.specialty, "avatar": _url(request, d.user.avatar),
    } for d in sorted(doctors, key=lambda d: d.user.get_full_name())]
    return block


def _doctor_block(request, doctor, private):
    block = {
        "specialty": doctor.specialty,
        "license_no": doctor.license_no,
        "bio": doctor.bio,
        "years_experience": doctor.years_experience,
        "education": doctor.education,
        "languages": doctor.languages,
        "focus_areas": doctor.focus_areas,
        "availability": [{"day_of_week": a.day_of_week, "start_time": a.start_time, "end_time": a.end_time}
                         for a in doctor.availability.all()],
    }
    today = timezone.localdate()
    block["available_today"] = any(a["day_of_week"] == today.weekday() for a in block["availability"])
    if not private:
        return block

    # Only the doctor and admins see the schedule and numbers (they name patients).
    from appointments.models import Appointment

    appts = doctor.appointments.exclude(status=Appointment.Status.CANCELLED)
    week_start = today - timedelta(days=today.weekday())
    todays = appts.filter(start_time__date=today).select_related("patient__user").order_by("start_time")
    block["stats"] = {
        "today": todays.count(),
        "week": appts.filter(start_time__date__gte=week_start,
                             start_time__date__lt=week_start + timedelta(days=7)).count(),
        "patients": appts.values("patient").distinct().count(),
    }
    block["today"] = [{
        "id": a.id, "start_time": a.start_time, "reason": a.reason, "status": a.status,
        "patient": a.patient.user.get_full_name() or a.patient.user.username,
        "patient_user_id": a.patient.user_id,
    } for a in todays]
    return block


def build_profile(request, user):
    data = {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.get_full_name() or user.username,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "avatar": _url(request, user.avatar),
        "cover": _url(request, user.cover),
        "is_me": user == request.user,
        "patient": None,
        "doctor": None,
    }
    if user.role == "patient" and hasattr(user, "patient"):
        data["patient"] = _patient_block(request, user.patient)
    if user.role == "clinical" and hasattr(user, "doctor"):
        private = user == request.user or request.user.role == "admin"
        data["doctor"] = _doctor_block(request, user.doctor, private)
    return data


class ProfileUpdateSerializer(serializers.Serializer):
    """What you may change on your own profile. Medical fields (cancer type, stage, blood type)
    and the doctor's license and specialty stay with staff and admins."""
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    # patients
    address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    emergency_contact = serializers.CharField(max_length=100, required=False, allow_blank=True)
    # doctors
    bio = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    years_experience = serializers.IntegerField(min_value=0, max_value=80, required=False, allow_null=True)
    education = serializers.CharField(max_length=200, required=False, allow_blank=True)
    languages = serializers.CharField(max_length=200, required=False, allow_blank=True)
    focus_areas = serializers.CharField(max_length=300, required=False, allow_blank=True)

    PATIENT_ONLY = {"address", "emergency_contact"}
    DOCTOR_ONLY = {"bio", "years_experience", "education", "languages", "focus_areas"}

    def validate_email(self, v):
        v = v.strip().lower()
        if User.objects.filter(email__iexact=v).exclude(pk=self.context["user"].pk).exists():
            raise serializers.ValidationError("Email already registered.")
        return v

    def validate(self, attrs):
        user = self.context["user"]
        not_yours = set()
        if user.role != "patient":
            not_yours |= self.PATIENT_ONLY & set(attrs)
        if user.role != "clinical":
            not_yours |= self.DOCTOR_ONLY & set(attrs)
        if not_yours:
            raise serializers.ValidationError({k: "Not part of your profile." for k in sorted(not_yours)})
        return attrs


class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, user_id=None):
        target = request.user if user_id is None else get_object_or_404(User, pk=user_id)
        if not _can_view(request.user, target):
            raise Http404  # don't reveal that the account exists
        return Response(build_profile(request, target))

    @transaction.atomic
    def patch(self, request, user_id=None):
        if user_id is not None and user_id != request.user.id:
            return Response({"detail": "You can only edit your own profile."}, status=status.HTTP_403_FORBIDDEN)
        user = request.user
        s = ProfileUpdateSerializer(data=request.data, context={"user": user})
        s.is_valid(raise_exception=True)
        d = s.validated_data

        for f in ("first_name", "last_name", "email", "phone"):
            if f in d:
                setattr(user, f, d[f])
        user.save()

        if user.role == "patient" and hasattr(user, "patient"):
            p = user.patient
            for f in ("phone", "address", "emergency_contact"):
                if f in d:
                    setattr(p, f, d[f])
            p.save()
        if user.role == "clinical" and hasattr(user, "doctor"):
            doc = user.doctor
            for f in ProfileUpdateSerializer.DOCTOR_ONLY:
                if f in d:
                    setattr(doc, f, d[f])
            doc.save()
        return Response(build_profile(request, user))


def _process_image(upload, kind):
    """Check the upload is a real image, fix phone-camera rotation, crop to shape, re-encode as JPEG.
    Re-encoding also drops EXIF data such as GPS location."""
    if upload.size > MAX_UPLOAD_BYTES:
        raise serializers.ValidationError({"file": "The photo is larger than 5 MB."})
    try:
        img = Image.open(upload)
        fmt = img.format
        img.verify()  # cheap integrity check; the image must be reopened afterwards
        upload.seek(0)
        img = Image.open(upload)
        img.load()
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise serializers.ValidationError({"file": "That file isn't a picture we can read."})
    if fmt not in ALLOWED_FORMATS:
        raise serializers.ValidationError({"file": "Use a JPG, PNG or WebP picture."})

    img = ImageOps.exif_transpose(img).convert("RGB")
    img = ImageOps.fit(img, SIZES[kind], method=Image.Resampling.LANCZOS)
    out = BytesIO()
    img.save(out, "JPEG", quality=86, optimize=True)
    return ContentFile(out.getvalue(), name=f"{kind}.jpg")


class ProfilePhotoView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def _kind(self, request, source):
        kind = source.get("kind", "avatar")
        if kind not in SIZES:
            raise serializers.ValidationError({"kind": "Use avatar or cover."})
        return kind

    def post(self, request):
        kind = self._kind(request, request.data)
        upload = request.FILES.get("file")
        if not upload:
            raise serializers.ValidationError({"file": "Choose a picture to upload."})
        content = _process_image(upload, kind)
        user = request.user
        field = getattr(user, kind)
        old_name = field.name  # remember it: save() below changes the same field object
        field.save(content.name, content, save=True)
        if old_name and old_name != field.name:
            field.storage.delete(old_name)
        return Response(build_profile(request, user), status=status.HTTP_201_CREATED)

    def delete(self, request):
        kind = self._kind(request, request.query_params)
        user = request.user
        field = getattr(user, kind)
        if field:
            field.delete(save=True)
        return Response(build_profile(request, user))
