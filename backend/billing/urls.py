from rest_framework.routers import SimpleRouter

from .views import ICD10ViewSet, InvoiceViewSet, ServiceViewSet

router = SimpleRouter()
router.register("invoices", InvoiceViewSet, basename="invoice")
router.register("icd10", ICD10ViewSet, basename="icd10")
router.register("services", ServiceViewSet, basename="service")
urlpatterns = router.urls
