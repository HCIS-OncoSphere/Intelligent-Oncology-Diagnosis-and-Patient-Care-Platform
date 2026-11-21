from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .profile import ProfilePhotoView, ProfileView
from .serializers import LoginSerializer
from .views import MeView, RegisterView, UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", TokenObtainPairView.as_view(serializer_class=LoginSerializer), name="token_obtain_pair"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/photo/", ProfilePhotoView.as_view(), name="profile-photo"),
    path("profile/<int:user_id>/", ProfileView.as_view(), name="profile-detail"),
    path("", include(router.urls)),
]
