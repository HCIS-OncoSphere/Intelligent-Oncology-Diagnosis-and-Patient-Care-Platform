from django.contrib import admin

from .models import Appointment, Doctor, DoctorAvailability


class AvailabilityInline(admin.TabularInline):
    model = DoctorAvailability
    extra = 0


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ("__str__", "specialty", "license_no")
    inlines = [AvailabilityInline]


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("id", "patient", "doctor", "start_time", "end_time", "status")
    list_filter = ("status", "doctor")
    date_hierarchy = "start_time"
