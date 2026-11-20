from rest_framework.routers import SimpleRouter
from .views import OrderViewSet, PlanViewSet, RecordViewSet

router = SimpleRouter()
router.register("records", RecordViewSet, basename="record")
router.register("treatment-plans", PlanViewSet, basename="plan")
router.register("orders", OrderViewSet, basename="order")
urlpatterns = router.urls
