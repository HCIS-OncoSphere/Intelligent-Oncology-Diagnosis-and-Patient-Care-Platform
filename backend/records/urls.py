from django.urls import path
from rest_framework.routers import SimpleRouter
from .views import FollowUpBookingView, OrderViewSet, PlanViewSet, RecordViewSet

router = SimpleRouter()
router.register("records", RecordViewSet, basename="record")
router.register("treatment-plans", PlanViewSet, basename="plan")
router.register("orders", OrderViewSet, basename="order")
urlpatterns = [
    path("records/<int:pk>/book-follow-up/", FollowUpBookingView.as_view({"post": "create"}),
         name="record-book-follow-up"),
] + router.urls
