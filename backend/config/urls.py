from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("accounts.urls")),
    path("api/", include("patients.urls")),
    path("api/", include("appointments.urls")),
    path("api/", include("billing.urls")),
    path("api/", include("records.urls")),
    path("api/reports/", include("reports.urls")),
    path("api/", include("administration.urls")),
    path("api/", include(router.urls)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
]

# profile photos during development (static() adds nothing when DEBUG is off)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
