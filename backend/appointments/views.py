"""Appointments. Feature F3: scheduling and management.

Endpoints (all under /api/):
  doctors/                       GET list, GET {id}/          logged in
  doctors/{id}/slots/?date=      GET free slots for one day (&days=7 for a week)   logged in
  doctors/next-free/             GET each doctor's first free slot   logged in
  availability/                  GET (all) / POST, PATCH, DELETE (admins: any doctor, doctors: their own)
  appointments/                  GET (scoped), POST (patients for themselves, admins for a patient)
  appointments/{id}/             GET, PATCH, PUT (scoped), DELETE (staff)
  appointments/{id}/cancel/      POST (scoped)
  appointments/{id}/reschedule/  POST (scoped)
  appointments/reminders/        GET tomorrow's scheduled list (staff)
"""
from datetime import datetime, time, timedelta

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from accounts.permissions import IsStaffRole
from patients.models import Patient
from .models import Appointment, Doctor, DoctorAvailability

STAFF_ROLES = ("admin", "clinical")


def is_staff(user):
    return getattr(user, "role", None) in STAFF_ROLES


def int_param(params, name):
    """Optional whole-number query parameter. Bad input is a 400, not a server error."""
    v = params.get(name)
    if v in (None, ""):
        return None
    if not v.isdigit():
        raise serializers.ValidationError({name: ["Must be a whole number."]})
    return int(v)


def date_param(params, name):
    """Optional YYYY-MM-DD query parameter."""
    v = params.get(name)
    if v in (None, ""):
        return None
    try:
        d = parse_date(v)
    except ValueError:  # well formed but impossible, e.g. 2026-02-30
        d = None
    if d is None:
        raise serializers.ValidationError({name: ["Use the format YYYY-MM-DD."]})
    return d


def lock_rows(*objs):
    """Lock the doctor / patient rows until the transaction ends, so two requests for the same
    slot cannot both pass the overlap check (check-then-insert race)."""
    if not transaction.get_connection().in_atomic_block:
        return
    for o in objs:
        if o is not None:
            type(o).objects.select_for_update().filter(pk=o.pk).exists()


# allowed status changes; completed / no-show only once the visit has started
TRANSITIONS = {
    Appointment.Status.SCHEDULED: {Appointment.Status.COMPLETED, Appointment.Status.NO_SHOW,
                                   Appointment.Status.CANCELLED},
}
AFTER_START = {Appointment.Status.COMPLETED, Appointment.Status.NO_SHOW}


class CanBook(BasePermission):
    """Only patients (for themselves) and admins (for a patient) create appointments. Doctors do not."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, "role", None) in ("patient", "admin")


# --------------------------------------------------------------------------- doctors and availability

class AvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorAvailability
        fields = ["id", "doctor", "day_of_week", "start_time", "end_time"]

    def validate_day_of_week(self, v):
        if not 0 <= v <= 6:
            raise serializers.ValidationError("day_of_week must be 0 (Monday) to 6 (Sunday).")
        return v

    def validate(self, d):
        doctor = d.get("doctor", getattr(self.instance, "doctor", None))
        day = d.get("day_of_week", getattr(self.instance, "day_of_week", None))
        start = d.get("start_time", getattr(self.instance, "start_time", None))
        end = d.get("end_time", getattr(self.instance, "end_time", None))
        if start >= end:
            raise serializers.ValidationError("end_time must be after start_time.")
        overlap = DoctorAvailability.objects.filter(doctor=doctor, day_of_week=day,
                                                    start_time__lt=end, end_time__gt=start)
        if self.instance:
            overlap = overlap.exclude(pk=self.instance.pk)
        if overlap.exists():
            raise serializers.ValidationError("This window overlaps another availability window of the doctor.")
        return d


class DoctorSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    is_me = serializers.SerializerMethodField()
    availability = AvailabilitySerializer(many=True, read_only=True)

    class Meta:
        model = Doctor
        fields = ["id", "name", "specialty", "license_no", "is_me", "availability"]

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_is_me(self, obj):
        """True for the signed-in doctor's own profile, so the UI can pick it without exposing user ids."""
        req = self.context.get("request")
        return bool(req and obj.user_id == req.user.id)


NEXT_FREE_DAYS = 60  # how far ahead "first free time" looks


def free_slots(doctor, first_day, days=1, minutes=30, booked=None, limit=None):
    """Free slots of one doctor from first_day for `days` days, in time order.

    `doctor.availability` should be prefetched. `booked` is a list of (start, end) of the doctor's
    non-cancelled appointments covering the period; it is read from the database when not given.
    `limit` stops early (1 = only the first free slot)."""
    windows = sorted(doctor.availability.all(), key=lambda w: w.start_time)
    tz = timezone.get_current_timezone()
    period_start = timezone.make_aware(datetime.combine(first_day, time.min), tz)
    period_end = period_start + timedelta(days=days)
    if booked is None:
        booked = list(Appointment.objects.filter(doctor=doctor, start_time__lt=period_end, end_time__gt=period_start)
                      .exclude(status=Appointment.Status.CANCELLED).values_list("start_time", "end_time"))
    now, step, free = timezone.now(), timedelta(minutes=minutes), []
    for offset in range(days):
        day = first_day + timedelta(days=offset)
        # no availability rows means any time is allowed: offer the default clinic day
        todays = [w for w in windows if w.day_of_week == day.weekday()] if windows else \
            [DoctorAvailability(day_of_week=day.weekday(), start_time=time(9), end_time=time(17))]
        for w in todays:
            s = timezone.make_aware(datetime.combine(day, w.start_time), tz)
            end = timezone.make_aware(datetime.combine(day, w.end_time), tz)
            while s + step <= end:
                e = s + step
                if s >= now and not any(bs < e and be > s for bs, be in booked):
                    free.append({"start_time": s.isoformat(), "end_time": e.isoformat()})
                    if limit and len(free) >= limit:
                        return free
                s = e
    return free


class DoctorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Doctor.objects.select_related("user").prefetch_related("availability").order_by("id")
    serializer_class = DoctorSerializer

    @action(detail=True, methods=["get"])
    def slots(self, request, pk=None):
        """Free booking slots of this doctor: ?date=YYYY-MM-DD&minutes=30, and &days=7 for a whole week."""
        doctor = self.get_object()
        day = parse_date(request.query_params.get("date", "") or "")
        if day is None:
            return Response({"date": ["Use the format YYYY-MM-DD."]}, status=400)
        try:
            minutes = int(request.query_params.get("minutes", 30))
        except ValueError:
            minutes = 0
        if not 5 <= minutes <= 240:
            return Response({"minutes": ["Must be a number between 5 and 240."]}, status=400)
        days = request.query_params.get("days", "1")
        if not days.isdigit() or not 1 <= int(days) <= 31:
            return Response({"days": ["Must be a number between 1 and 31."]}, status=400)
        return Response({"doctor": doctor.id, "date": day.isoformat(), "minutes": minutes,
                         "slots": free_slots(doctor, day, int(days), minutes)})

    @action(detail=False, methods=["get"], url_path="next-free")
    def next_free(self, request):
        """Each doctor's first free 30-minute slot in the next 60 days (null when fully booked):
        [{"doctor": id, "start_time": ..., "end_time": ...}]. Two queries, whatever the number of doctors."""
        doctors = list(self.get_queryset())
        today = timezone.localdate()
        tz = timezone.get_current_timezone()
        start = timezone.make_aware(datetime.combine(today, time.min), tz)
        booked = {}
        for d, s, e in (Appointment.objects.filter(doctor__in=doctors, start_time__lt=start + timedelta(days=NEXT_FREE_DAYS),
                                                   end_time__gt=start)
                        .exclude(status=Appointment.Status.CANCELLED).values_list("doctor_id", "start_time", "end_time")):
            booked.setdefault(d, []).append((s, e))
        out = []
        for doctor in doctors:
            first = free_slots(doctor, today, NEXT_FREE_DAYS, booked=booked.get(doctor.id, []), limit=1)
            out.append({"doctor": doctor.id, **(first[0] if first else {"start_time": None, "end_time": None})})
        return Response(out)


class AvailabilityViewSet(viewsets.ModelViewSet):
    """Weekly working hours. Everyone signed in can read them.
    Admins change any doctor's hours; a doctor changes only their own."""
    serializer_class = AvailabilitySerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return super().get_permissions()
        return [IsStaffRole()]

    def get_queryset(self):
        qs = DoctorAvailability.objects.all()
        u = self.request.user
        if self.action not in ("list", "retrieve") and u.role != "admin":
            return qs.filter(doctor__user=u)  # another doctor's window is a 404 for edit / delete
        doctor = int_param(self.request.query_params, "doctor")
        return qs.filter(doctor_id=doctor) if doctor is not None else qs

    def _check_owner(self, serializer):
        u = self.request.user
        doctor = serializer.validated_data.get("doctor") or getattr(serializer.instance, "doctor", None)
        if u.role != "admin" and (doctor is None or doctor.user_id != u.id):
            raise PermissionDenied("Doctors can set only their own working hours.")

    def perform_create(self, serializer):
        self._check_owner(serializer)
        serializer.save()

    def perform_update(self, serializer):
        self._check_owner(serializer)
        serializer.save()


# --------------------------------------------------------------------------- appointments

class AppointmentSerializer(serializers.ModelSerializer):
    patient = serializers.PrimaryKeyRelatedField(queryset=Patient.objects.all(), required=False)
    patient_name = serializers.SerializerMethodField()
    patient_mrn = serializers.CharField(source="patient.mrn", read_only=True)
    doctor_name = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = ["id", "patient", "patient_name", "patient_mrn", "doctor", "doctor_name", "start_time",
                  "end_time", "status", "reason", "created_at"]
        read_only_fields = ["created_at"]

    def get_patient_name(self, obj):
        u = obj.patient.user
        return u.get_full_name() or u.username

    def get_doctor_name(self, obj):
        return str(obj.doctor)

    def _user(self):
        req = self.context.get("request")
        return getattr(req, "user", None)

    def validate(self, d):
        user = self._user()
        creating = self.instance is None

        # patients can neither pick a status nor move a booking to another patient
        if user is not None and not is_staff(user):
            if "status" in d and (creating or d["status"] != self.instance.status):
                raise serializers.ValidationError({"status": "Patients cannot change the status. Use cancel."})
            d.pop("patient", None)
        if creating:
            d["status"] = Appointment.Status.SCHEDULED
        elif "status" in d and d["status"] != self.instance.status:
            old, new = self.instance.status, d["status"]
            if new not in TRANSITIONS.get(old, set()):
                raise serializers.ValidationError(
                    {"status": f"A {old} appointment cannot be changed to {new}."})
            if new in AFTER_START and self.instance.start_time > timezone.now():
                raise serializers.ValidationError(
                    {"status": f"An appointment can be marked {new} only after it has started."})

        start =d.get("start_time", getattr(self.instance, "start_time", None))
        end = d.get("end_time", getattr(self.instance, "end_time", None))
        doctor = d.get("doctor", getattr(self.instance, "doctor", None))
        if start is None or end is None or doctor is None:
            raise serializers.ValidationError("doctor, start_time and end_time are required.")
        if start >= end:
            raise serializers.ValidationError("end_time must be after start_time.")

        time_changed = creating or any(
            k in d and d[k] != getattr(self.instance, k) for k in ("start_time", "end_time", "doctor"))
        if not time_changed:
            return d  # only status/reason changed: the slot was already validated
        if not creating and self.instance.status != Appointment.Status.SCHEDULED:
            raise serializers.ValidationError("Only scheduled appointments can be moved.")
        if start < timezone.now():
            raise serializers.ValidationError("Cannot book in the past.")

        # doctor availability (only enforced if the doctor defined any), compared in local time
        slots = DoctorAvailability.objects.filter(doctor=doctor)
        if slots.exists():
            ls, le = timezone.localtime(start), timezone.localtime(end)
            ok = ls.date() == le.date() and slots.filter(
                day_of_week=ls.weekday(), start_time__lte=ls.time(), end_time__gte=le.time()).exists()
            if not ok:
                raise serializers.ValidationError("Doctor is not available at this time.")

        patient = d.get("patient", getattr(self.instance, "patient", None))
        if patient is None and getattr(user, "role", None) == "patient":
            patient = getattr(user, "patient", None)
        lock_rows(doctor, patient)

        # no double booking: A.start < B.end and A.end > B.start; cancelled bookings free the slot
        overlapping = Appointment.objects.filter(start_time__lt=end, end_time__gt=start).exclude(
            status=Appointment.Status.CANCELLED)
        if self.instance:
            overlapping = overlapping.exclude(pk=self.instance.pk)
        if overlapping.filter(doctor=doctor).exists():
            raise serializers.ValidationError("This time slot is already booked.")
        if patient is not None and overlapping.filter(patient=patient).exists():
            raise serializers.ValidationError("The patient already has another appointment at this time.")
        return d


class AppointmentViewSet(viewsets.ModelViewSet):
    """Patients see and manage only their own bookings; staff see everything.

    Filters: ?status=scheduled  ?doctor=<id>  ?patient=<id> (staff)  ?date=YYYY-MM-DD  ?upcoming=1
             ?from=YYYY-MM-DD&to=YYYY-MM-DD (a period, both days included)
    """
    serializer_class = AppointmentSerializer

    def get_permissions(self):
        if self.action in ("destroy", "reminders"):
            return [IsStaffRole()]
        if self.action == "create":
            return [CanBook()]
        return super().get_permissions()

    def get_queryset(self):
        qs = Appointment.objects.select_related("patient__user", "doctor__user").order_by("start_time")
        u, p = self.request.user, self.request.query_params
        if self.action != "list":
            return qs if is_staff(u) else qs.filter(patient__user=u)
        patient, doctor, day = int_param(p, "patient"), int_param(p, "doctor"), date_param(p, "date")
        status = p.get("status")
        if status and status not in Appointment.Status.values:
            raise serializers.ValidationError({"status": [f"Use one of: {', '.join(Appointment.Status.values)}."]})
        if not is_staff(u):
            qs = qs.filter(patient__user=u)
        elif patient is not None:
            qs = qs.filter(patient_id=patient)
        if status:
            qs = qs.filter(status=status)
        if doctor is not None:
            qs = qs.filter(doctor_id=doctor)
        tz = timezone.get_current_timezone()
        if day:
            s = timezone.make_aware(datetime.combine(day, time.min), tz)
            qs = qs.filter(start_time__gte=s, start_time__lt=s + timedelta(days=1))
        # a period, both days included (the week calendar): ?from=YYYY-MM-DD&to=YYYY-MM-DD
        first, last = date_param(p, "from"), date_param(p, "to")
        if first:
            qs = qs.filter(start_time__gte=timezone.make_aware(datetime.combine(first, time.min), tz))
        if last:
            qs = qs.filter(start_time__lt=timezone.make_aware(datetime.combine(last + timedelta(days=1), time.min), tz))
        if p.get("upcoming") in ("1", "true"):
            qs = qs.filter(start_time__gte=timezone.now(), status=Appointment.Status.SCHEDULED)
        return qs

    # validation and save run in one transaction, so the row locks taken in validate() hold until the insert
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @transaction.atomic
    def update(self, request, *args, **kwargs):  # PUT and PATCH
        return super().update(request, *args, **kwargs)

    def perform_create(self, serializer):
        u = self.request.user
        if u.role == "patient":
            patient = getattr(u, "patient", None)
            if patient is None:
                raise serializers.ValidationError("Your account has no patient profile.")
            serializer.save(patient=patient, booked_by=u)
        else:
            if "patient" not in serializer.validated_data:
                raise serializers.ValidationError({"patient": "Required for staff bookings."})
            serializer.save(booked_by=u)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        appt = self.get_object()
        if appt.status != Appointment.Status.SCHEDULED:
            return Response({"detail": f"Only scheduled appointments can be cancelled (this one is {appt.status})."},
                            status=400)
        appt.status = Appointment.Status.CANCELLED
        appt.save(update_fields=["status"])  # the HL7 signal sends SIU^S15
        return Response(self.get_serializer(appt).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def reschedule(self, request, pk=None):
        """Move a booking: body {"start_time": ..., "end_time": ...}. Same rules as booking."""
        appt = self.get_object()
        ser = self.get_serializer(appt, data={k: request.data.get(k) for k in ("start_time", "end_time")}, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

    @action(detail=False, methods=["get"])
    def reminders(self, request):
        """Tomorrow's scheduled appointments with the patient phone, for a reminder call list."""
        tz = timezone.get_current_timezone()
        tomorrow = timezone.localdate() + timedelta(days=1)
        s = timezone.make_aware(datetime.combine(tomorrow, time.min), tz)
        qs = (Appointment.objects.select_related("patient__user", "doctor__user")
              .filter(start_time__gte=s, start_time__lt=s + timedelta(days=1), status=Appointment.Status.SCHEDULED)
              .order_by("start_time"))
        return Response([{**self.get_serializer(a).data, "patient_phone": a.patient.phone or a.patient.user.phone}
                         for a in qs])

    def perform_destroy(self, instance):
        if not is_staff(self.request.user):
            raise PermissionDenied("Patients cancel appointments instead of deleting them.")
        instance.delete()
