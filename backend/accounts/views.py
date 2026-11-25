import logging

import re
import requests
from django.conf import settings
from django.db import transaction

from rest_framework import generics, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from .models import Notification, User
from .permissions import IsAdminRole
from .serializers import RegisterSerializer, UserSerializer, make_username


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


def _jwt_tokens_for(user):
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def make_google_username(given_name, family_name, email):
    """Build a readable username from the Google account name, e.g. "alaa.khaled".
    Falls back to the email prefix (make_username) when names are missing, and
    adds a number if the username is already taken."""
    base = " ".join((given_name or "").strip(), (family_name or "").strip()).strip()
    base = re.sub(r"[^A-Za-z0-9._\-]", ".", base).strip("._-").lower() or None
    if not base:
        return make_username(email)
    base = base[:30]
    name, n = base, 1
    while User.objects.filter(username__iexact=name).exists():
        n += 1
        name = f"{base}{n}"
    return name


class GoogleAuthView(generics.GenericAPIView):
    """Sign up or sign in a patient using a Google ID token.

    The frontend (Google Identity Services) posts {"credential": "<id_token>"}.
    We verify the token with Google, then create a patient account on first use
    or sign in an existing one. JWT access/refresh tokens are returned, the same
    as /auth/login/, so the client stores them and calls /auth/me/ afterwards.
    """
    permission_classes = [permissions.AllowAny]
    throttle_scope = "register"

    GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"

    def post(self, request):
        credential = request.data.get("credential")
        if not credential:
            return Response({"credential": ["Google ID token is required."]}, status=400)

        # Verify the ID token with Google (server-to-server, so it can't be forged).
        try:
            resp = requests.get(
                self.GOOGLE_TOKENINFO_URL,
                params={"id_token": credential},
                timeout=10,
            )
        except requests.RequestException:
            return Response(
                {"detail": "Could not reach Google to verify the sign-in. Try again."},
                status=502,
            )
        if resp.status_code != 200:
            # Google says why (expired token, wrong client, clock problem...); show it in the server log
            why = ""
            try:
                why = resp.json().get("error_description") or resp.json().get("error") or ""
            except ValueError:
                pass
            logging.getLogger(__name__).warning("Google rejected the sign-in token: %s %s", resp.status_code, why)
            return Response({"detail": "Invalid Google sign-in token." + (f" ({why})" if why else "")}, status=400)

        profile = resp.json()

        # Extra assurance: the token must have been issued to this app.
        client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
        if client_id and profile.get("aud") != client_id:
            return Response({"detail": "Google token was not issued to this app."}, status=400)

        if not profile.get("email_verified"):
            return Response({"detail": "Google account email is not verified."}, status=400)

        email = (profile.get("email") or "").strip().lower()
        if not email:
            return Response({"detail": "Google account has no email address."}, status=400)

        given_name = profile.get("given_name") or ""
        family_name = profile.get("family_name") or ""

        user = User.objects.filter(email__iexact=email).first()
        created = False
        if user is None:
            # First time: create a patient account. Password is unusable — the
            # person signs in with Google, not a password.
            created = True
            with transaction.atomic():
                user = User.objects.create_user(
                    username=make_google_username(given_name, family_name, email),
                    email=email,
                    first_name=given_name,
                    last_name=family_name,
                    role=User.Role.PATIENT,
                )
                user.set_unusable_password()
                user.save()
                try:
                    from patients.models import Patient
                    Patient.objects.create(user=user)  # date_of_birth left blank; collected later
                except (ImportError, LookupError):
                    pass
        elif user.role != User.Role.PATIENT:
            # A Google account can't be used to sign in as staff/admin/finance.
            return Response(
                {"detail": "This email is registered as a staff account. Sign in with your password instead."},
                status=403,
            )

        status_code = 201 if created else 200
        return Response({
            **_jwt_tokens_for(user),
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "created": created,
        }, status=status_code)


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
