from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .profile import ProfilePhotoView, ProfileView
from .serializers import LoginSerializer
from .doctors import AdminDoctorCreateView, DoctorRegisterView, DoctorRequestViewSet
from .views import (
    ChangePasswordView, GoogleAuthView, MeView, NotificationView, RegisterView, UserViewSet,
)

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("admin/doctor-requests", DoctorRequestViewSet, basename="doctor-request")

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/google/", GoogleAuthView.as_view(), name="google-auth"),
    path("auth/register/doctor/", DoctorRegisterView.as_view(), name="register-doctor"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("notifications/", NotificationView.as_view(), name="notifications"),
    path("admin/doctors/", AdminDoctorCreateView.as_view(), name="admin-doctor-create"),
    path("auth/login/", TokenObtainPairView.as_view(serializer_class=LoginSerializer), name="token_obtain_pair"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/photo/", ProfilePhotoView.as_view(), name="profile-photo"),
    path("profile/<int:user_id>/", ProfileView.as_view(), name="profile-detail"),
    path("", include(router.urls)),
]
