from rest_framework.routers import SimpleRouter
from .views import AuditLogViewSet, SystemSettingViewSet

router = SimpleRouter()
router.register("audit", AuditLogViewSet, basename="audit")
router.register("settings", SystemSettingViewSet, basename="setting")
urlpatterns = router.urls
