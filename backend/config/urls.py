from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
# Team members will register their ViewSets here upon merging their apps:
# router.register("users", UserViewSet, basename="user")
# router.register("patients", PatientViewSet, basename="patient")
# router.register("doctors", DoctorViewSet, basename="doctor")
# router.register("appointments", AppointmentViewSet, basename="appointment")
# router.register("invoices", InvoiceViewSet, basename="invoice")
# router.register("icd10", ICD10ViewSet, basename="icd10")
# router.register("services", ServiceViewSet, basename="service")
# router.register("records", RecordViewSet, basename="record")
# router.register("treatment-plans", PlanViewSet, basename="plan")
# router.register("orders", OrderViewSet, basename="order")
# router.register("hl7/messages", Hl7MessageViewSet, basename="hl7message")
# router.register("audit", AuditLogViewSet, basename="audit")
# router.register("settings", SystemSettingViewSet, basename="setting")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
]
