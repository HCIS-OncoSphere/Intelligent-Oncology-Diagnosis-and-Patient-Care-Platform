"""Profile pages for every role (patient, doctor, admin), plus profile-photo and cover uploads.

GET    /api/profile/             your own profile
GET    /api/profile/<user_id>/   someone else's profile (rules in _can_view)
PATCH  /api/profile/             edit your own contact and "about" details
POST   /api/profile/photo/       multipart: kind=avatar|cover, file=<image>
DELETE /api/profile/photo/?kind=avatar|cover
"""
from datetime import date, timedelta
from decimal import Decimal
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
    if not born:
        return None  # patient signed up with Google and hasn't given a DOB yet
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def _national_id(viewer, patient):
    """The owner and admins see the whole number; a doctor sees only the last four digits."""
    nid = patient.national_id
    if not nid or viewer == patient.user or viewer.role == "admin":
        return nid
    return "*" * (len(nid) - 4) + nid[-4:]


def _visit_counts(patient):
    from appointments.models import Appointment

    done = patient.appointments.filter(status=Appointment.Status.COMPLETED)
    last = done.order_by("-start_time").first()
    return {"completed": done.count(), "total": patient.appointments.count(),
            "last_visit": last.start_time if last else None}


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
        "emergency_contact_phone": patient.emergency_contact_phone,
        "national_id": _national_id(request.user, patient),
        "emr_patient_id": patient.emr_patient_id,
        "registered_on": patient.created_at,
        "upcoming": [{
            "id": a.id, "start_time": a.start_time, "reason": a.reason,
            "doctor": a.doctor.user.get_full_name() or a.doctor.user.username,
        } for a in upcoming],
        "active_plan": None, "latest_result": None, "prescriptions": 0, "care_team": [],
        "diagnoses": [], "plans": [], "medications": [], "orders": [], "imaging": None, "billing": None,
        "visits": _visit_counts(patient),
    }

    doctors = {a.doctor for a in patient.appointments.select_related("doctor__user")}
    try:  # the records app is a separate slice; the profile still works without it
        from records.models import OrderResult, Prescription, RecordDiagnosis, TreatmentPlan

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
        block["plans"] = [{
            "type": p.get_type_display(), "status": p.status, "description": p.description,
            "start_date": p.start_date, "end_date": p.end_date,
            "doctor": p.doctor.user.get_full_name() or p.doctor.user.username,
        } for p in patient.plans.select_related("doctor__user").order_by("-start_date")[:5]]
        block["medications"] = [{
            "medication": m.medication, "dosage": m.dosage, "frequency": m.frequency, "duration": m.duration,
            "instructions": m.instructions, "prescribed_on": m.record.created_at,
        } for m in Prescription.objects.filter(record__patient=patient).select_related("record")
            .order_by("-record__created_at", "-id")[:5]]
        block["orders"] = [{
            "type": o.get_order_type_display(), "description": o.description, "status": o.status,
            "ordered_at": o.ordered_at,
            "result": (o.results.order_by("-reported_at").first().result_text[:200]
                       if o.results.exists() else ""),
        } for o in patient.orders.prefetch_related("results").order_by("-ordered_at")[:5]]
        seen, diagnoses = set(), []
        for d in (RecordDiagnosis.objects.filter(record__patient=patient).select_related("icd10_code")
                  .order_by("-is_primary", "-record__created_at")):
            if d.icd10_code_id not in seen:
                seen.add(d.icd10_code_id)
                diagnoses.append({"code": d.icd10_code_id, "description": d.icd10_code.description,
                                  "is_primary": d.is_primary})
        block["diagnoses"] = diagnoses[:6]
    except (ImportError, LookupError):
        pass

    try:  # imaging and billing are separate slices too
        studies = patient.studies.order_by("-study_date", "-id")
        last = studies.first()
        if last:
            block["imaging"] = {"count": studies.count(), "modality": last.get_modality_display(),
                                "body_part": last.body_part, "description": last.description,
                                "study_date": last.study_date}
        invoices = patient.invoices.exclude(status="cancelled")
        due = [i for i in invoices.filter(status="pending").prefetch_related("payments")]
        block["billing"] = {
            "unpaid_count": len(due),
            "amount_due": f"{sum((i.total_amount - i.paid_amount for i in due), Decimal('0.00')):.2f}",
            "paid_count": invoices.filter(status="paid").count(),
        }
    except (ImportError, LookupError, AttributeError):
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
        "registered_on": doctor.user.date_joined,
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
        "completed": appts.filter(status=Appointment.Status.COMPLETED).count(),
    }
    nxt = (appts.filter(start_time__gte=timezone.now(), status=Appointment.Status.SCHEDULED)
           .select_related("patient__user").order_by("start_time")[:5])
    block["upcoming"] = [{
        "id": a.id, "start_time": a.start_time, "reason": a.reason,
        "patient": a.patient.user.get_full_name() or a.patient.user.username,
        "patient_user_id": a.patient.user_id,
    } for a in nxt]
    block["today"] = [{
        "id": a.id, "start_time": a.start_time, "reason": a.reason, "status": a.status,
        "patient": a.patient.user.get_full_name() or a.patient.user.username,
        "patient_user_id": a.patient.user_id,
    } for a in todays]
    return block


def _admin_block():
    """System overview for administrators."""
    from django.db.models import Count

    block = {"users": dict(User.objects.values_list("role").annotate(n=Count("id"))),
             "active_users": User.objects.filter(is_active=True).count(),
             "pending_requests": 0, "today_visits": 0, "unpaid_invoices": 0, "recent_activity": []}
    try:
        from appointments.models import Appointment
        from accounts.models import DoctorApplication

        block["pending_requests"] = DoctorApplication.objects.filter(status="pending").count()
        block["today_visits"] = Appointment.objects.filter(
            start_time__date=timezone.localdate(), status=Appointment.Status.SCHEDULED).count()
        from billing.models import Invoice

        block["unpaid_invoices"] = Invoice.objects.filter(status="pending").count()
    except (ImportError, LookupError):
        pass
    try:
        from administration.models import AuditLog

        block["recent_activity"] = [{
            "action": a.action, "path": a.path, "status_code": a.status_code,
            "user": a.user.username if a.user else "", "created_at": a.created_at,
        } for a in AuditLog.objects.select_related("user").order_by("-id")[:6]]
    except (ImportError, LookupError):
        pass
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
        "member_since": user.date_joined,
        # sign-in time is private to the owner and admins
        "last_login": user.last_login if (user == request.user or request.user.role == "admin") else None,
        "patient": None,
        "doctor": None,
        "admin": None,
    }
    if user.role == "patient" and hasattr(user, "patient"):
        data["patient"] = _patient_block(request, user.patient)
    if user.role == "clinical" and hasattr(user, "doctor"):
        private = user == request.user or request.user.role == "admin"
        data["doctor"] = _doctor_block(request, user.doctor, private)
    if user.role == "admin":
        data["admin"] = _admin_block()
    return data


class ProfileUpdateSerializer(serializers.Serializer):
    """What you may change on your own profile. Medical fields (cancer type, stage, blood type)
    and the doctor's license and specialty stay with staff and admins."""
    username = serializers.CharField(max_length=150, required=False)
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    # patients
    address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    emergency_contact = serializers.CharField(max_length=100, required=False, allow_blank=True)
    emergency_contact_phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    national_id = serializers.CharField(max_length=14, required=False, allow_blank=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    # doctors
    bio = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    years_experience = serializers.IntegerField(min_value=0, max_value=80, required=False, allow_null=True)
    education = serializers.CharField(max_length=200, required=False, allow_blank=True)
    languages = serializers.CharField(max_length=200, required=False, allow_blank=True)
    focus_areas = serializers.CharField(max_length=300, required=False, allow_blank=True)

    PATIENT_ONLY = {"address", "emergency_contact", "emergency_contact_phone", "national_id", "date_of_birth"}
    DOCTOR_ONLY = {"bio", "years_experience", "education", "languages", "focus_areas"}

    def validate_national_id(self, v):
        v = v.strip()
        if v and not (v.isascii() and v.isdigit() and len(v) == 14):
            raise serializers.ValidationError("National ID must be exactly 14 digits.")
        return v

    def validate_username(self, v):
        v = v.strip()
        if not v:
            raise serializers.ValidationError("Choose a username.")
        if len(v) < 3:
            raise serializers.ValidationError("Username is too short (at least 3 characters).")
        if User.objects.filter(username__iexact=v).exclude(pk=self.context["user"].pk).exists():
            raise serializers.ValidationError("This username is already taken.")
        return v

    def validate_email(self, v):
        v = v.strip().lower()
        if not v.isascii():
            raise serializers.ValidationError("Use an email address written in English letters, like name@example.com.")
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

        for f in ("username", "first_name", "last_name", "email", "phone"):
            if f in d:
                setattr(user, f, d[f])
        user.save()

        if user.role == "patient" and hasattr(user, "patient"):
            p = user.patient
            for f in ("phone", "address", "emergency_contact", "emergency_contact_phone", "national_id",
                      "date_of_birth"):
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
