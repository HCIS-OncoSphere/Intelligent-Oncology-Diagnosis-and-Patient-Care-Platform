from rest_framework import generics, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .permissions import IsAdminRole
from .serializers import RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    """Public patient self-registration (F2). Staff/admin accounts are created by an admin."""
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({"id": user.id, "username": user.username, "role": user.role}, status=201)


class MeView(APIView):
    """Returns currently authenticated user profile; supports partial self-update via PATCH."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user, context={"request": request}).data)

    def patch(self, request):
        """Allow users to update their own profile, but block changes to role and is_active."""
        data = request.data.copy()
        # Patients/clinical users must not be able to elevate their own role or
        # deactivate / reactivate their own account.
        data.pop("role", None)
        data.pop("is_active", None)
        serializer = UserSerializer(
            request.user,
            data=data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user, context={"request": request}).data)


class UserViewSet(viewsets.ModelViewSet):
    """Admin user management (F8)."""
    queryset = User.objects.all().order_by("id")
    serializer_class = UserSerializer
    permission_classes = [IsAdminRole]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def perform_update(self, serializer):
        """Prevent an admin from accidentally deactivating their own account."""
        instance = self.get_object()
        request_user = self.request.user
        if instance == request_user and "is_active" in self.request.data:
            is_active_val = self.request.data["is_active"]
            if not is_active_val:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("Admins cannot deactivate their own account.")
        serializer.save()
