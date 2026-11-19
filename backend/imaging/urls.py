from rest_framework.routers import SimpleRouter

from .views import StudyViewSet

router = SimpleRouter()
router.register("imaging/studies", StudyViewSet, basename="imaging-study")
urlpatterns = router.urls
