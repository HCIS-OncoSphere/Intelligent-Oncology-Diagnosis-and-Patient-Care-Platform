from rest_framework.routers import SimpleRouter
from .views import Hl7MessageViewSet

router = SimpleRouter()
router.register("hl7/messages", Hl7MessageViewSet, basename="hl7message")
urlpatterns = router.urls
