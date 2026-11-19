from rest_framework.routers import SimpleRouter

from .views import AppointmentViewSet, AvailabilityViewSet, DoctorViewSet

router = SimpleRouter()
router.register("doctors", DoctorViewSet, basename="doctor")
router.register("availability", AvailabilityViewSet, basename="availability")
router.register("appointments", AppointmentViewSet, basename="appointment")
urlpatterns = router.urls
