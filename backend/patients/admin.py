from django.contrib import admin
from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("mrn", "user", "date_of_birth", "gender", "cancer_type", "cancer_stage", "created_at")
    search_fields = ("mrn", "user__username", "user__first_name", "user__last_name", "user__email")
    list_filter = ("gender", "blood_type", "cancer_type")
    readonly_fields = ("mrn", "created_at")
