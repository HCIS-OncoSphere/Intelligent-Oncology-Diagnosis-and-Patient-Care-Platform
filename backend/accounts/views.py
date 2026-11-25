from rest_framework import generics, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from .models import Notification, User
from .permissions import IsAdminRole
from .serializers import RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    """Public patient self-registration (F2). Staff/admin accounts are created by an admin."""
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer
    throttle_scope = "register"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({"id": user.id, "username": user.username, "role": user.role}, status=201)


class MeView(APIView):
    """Returns currently authenticated user profile; supports partial self-update via PATCH."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        data = UserSerializer(request.user, context={"request": request}).data
        data["avatar"] = request.user.avatar.url if request.user.avatar else None  # relative, like /api/profile/
        return Response(data)

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


class ChangePasswordView(APIView):
    """Signed-in user changes their own password (also clears the "must change" flag of a temporary one)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        current = request.data.get("current_password") or ""
        new = request.data.get("new_password") or ""
        user = request.user
        if not user.check_password(current):
            return Response({"current_password": ["Current password is wrong."]}, status=400)
        if new == current:
            return Response({"new_password": ["Choose a password different from the current one."]}, status=400)
        try:
            validate_password(new, user=user)
        except DjangoValidationError as e:
            return Response({"new_password": list(e.messages)}, status=400)
        user.set_password(new)
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password"])
        return Response({"detail": "Password changed."})


class NotificationView(APIView):
    """GET: your latest notifications and the unread count. POST {"ids": [..]} (or no ids): mark as read."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = Notification.objects.filter(user=request.user)
        items = [{"id": n.id, "title": n.title, "message": n.message, "link": n.link, "is_read": n.is_read,
                  "created_at": n.created_at} for n in qs[:30]]
        return Response({"unread": qs.filter(is_read=False).count(), "results": items})

    def post(self, request):
        qs = Notification.objects.filter(user=request.user, is_read=False)
        ids = request.data.get("ids")
        if isinstance(ids, list):
            qs = qs.filter(id__in=[i for i in ids if isinstance(i, int)])
        qs.update(is_read=True)
        return Response({"detail": "ok"})
