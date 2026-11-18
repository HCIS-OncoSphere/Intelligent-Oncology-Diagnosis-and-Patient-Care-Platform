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
    """Returns currently authenticated user profile."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class UserViewSet(viewsets.ModelViewSet):
    """Admin user management (F8)."""
    queryset = User.objects.all().order_by("id")
    serializer_class = UserSerializer
    permission_classes = [IsAdminRole]
