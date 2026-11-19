"""Appointments. Feature F3: scheduling and management.

Endpoints (all under /api/):
  doctors/                       GET list, GET {id}/          logged in
  doctors/{id}/slots/?date=      GET free slots for one day   logged in
  availability/                  GET (all) / POST, PATCH, DELETE (staff)
  appointments/                  GET (scoped), POST
  appointments/{id}/             GET, PATCH, PUT (scoped), DELETE (staff)
  appointments/{id}/cancel/      POST (scoped)
  appointments/{id}/reschedule/  POST (scoped)
  appointments/reminders/        GET tomorrow's scheduled list (staff)
"""
from datetime import datetime, time, timedelta

from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from accounts.permissions import IsStaffRole
from patients.models import Patient
from .models import Appointment, Doctor, DoctorAvailability

STAFF_ROLES = ("admin", "clinical")


def is_staff(user):
    return getattr(user, "role", None) in STAFF_ROLES


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
    availability = AvailabilitySerializer(many=True, read_only=True)

    class Meta:
        model = Doctor
        fields = ["id", "name", "specialty", "license_no", "availability"]

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


class DoctorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Doctor.objects.select_related("user").prefetch_related("availability").order_by("id")
    serializer_class = DoctorSerializer

    @action(detail=True, methods=["get"])
    def slots(self, request, pk=None):
        """Free booking slots of this doctor on one day: ?date=YYYY-MM-DD&minutes=30"""
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

        windows = doctor.availability.filter(day_of_week=day.weekday())
        if not doctor.availability.exists():
            # no availability rows means any time is allowed: offer the default clinic day
            windows = [DoctorAvailability(doctor=doctor, day_of_week=day.weekday(), start_time=time(9), end_time=time(17))]
        tz = timezone.get_current_timezone()
        day_start = timezone.make_aware(datetime.combine(day, time.min), tz)
        booked = list(Appointment.objects.filter(doctor=doctor, start_time__lt=day_start + timedelta(days=1),
                                                 end_time__gt=day_start)
                      .exclude(status=Appointment.Status.CANCELLED).values_list("start_time", "end_time"))
        now, step, free = timezone.now(), timedelta(minutes=minutes), []
        for w in windows:
            s = timezone.make_aware(datetime.combine(day, w.start_time), tz)
            end = timezone.make_aware(datetime.combine(day, w.end_time), tz)
            while s + step <= end:
                e = s + step
                if s >= now and not any(bs < e and be > s for bs, be in booked):
                    free.append({"start_time": s.isoformat(), "end_time": e.isoformat()})
                s = e
        return Response({"doctor": doctor.id, "date": day.isoformat(), "minutes": minutes, "slots": free})


class AvailabilityViewSet(viewsets.ModelViewSet):
    """Weekly working hours. Everyone signed in can read them; only staff change them."""
    serializer_class = AvailabilitySerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return super().get_permissions()
        return [IsStaffRole()]

    def get_queryset(self):
        qs = DoctorAvailability.objects.all()
        doctor = self.request.query_params.get("doctor")
        return qs.filter(doctor_id=doctor) if doctor else qs


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

        start = d.get("start_time", getattr(self.instance, "start_time", None))
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

        # no double booking: A.start < B.end and A.end > B.start; cancelled bookings free the slot
        clash = Appointment.objects.filter(doctor=doctor, start_time__lt=end, end_time__gt=start).exclude(
            status=Appointment.Status.CANCELLED)
        if self.instance:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError("This time slot is already booked.")
        return d


class AppointmentViewSet(viewsets.ModelViewSet):
    """Patients see and manage only their own bookings; staff see everything.

    Filters: ?status=scheduled  ?doctor=<id>  ?patient=<id> (staff)  ?date=YYYY-MM-DD  ?upcoming=1
    """
    serializer_class = AppointmentSerializer

    def get_permissions(self):
        if self.action in ("destroy", "reminders"):
            return [IsStaffRole()]
        return super().get_permissions()

    def get_queryset(self):
        qs = Appointment.objects.select_related("patient__user", "doctor__user").order_by("start_time")
        u, p = self.request.user, self.request.query_params
        if not is_staff(u):
            qs = qs.filter(patient__user=u)
        elif p.get("patient"):
            qs = qs.filter(patient_id=p["patient"])
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("doctor"):
            qs = qs.filter(doctor_id=p["doctor"])
        day = parse_date(p.get("date", "") or "")
        if day:
            tz = timezone.get_current_timezone()
            s = timezone.make_aware(datetime.combine(day, time.min), tz)
            qs = qs.filter(start_time__gte=s, start_time__lt=s + timedelta(days=1))
        if p.get("upcoming") in ("1", "true"):
            qs = qs.filter(start_time__gte=timezone.now(), status=Appointment.Status.SCHEDULED)
        return qs

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
