"""Forgot / reset password flow (works for every role: patient, clinical, admin, doctor).

POST /api/auth/forgot-password/   { "email": "..." }
  → always 200 (never reveals whether the e-mail exists).
  → if found: creates a one-use PasswordResetToken and e-mails a link.

POST /api/auth/reset-password/    { "token": "...", "new_password": "..." }
  → 200 on success, 400 on bad / expired token or weak password.
"""
import secrets

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PasswordResetToken, User
from .notify import email_user

EXPIRY_HOURS = 2


def _frontend_url():
    return getattr(settings, "FRONTEND_URL", "http://localhost:5173")


def _send_reset_email(user, token_str):
    link = f"{_frontend_url()}/reset-password?token={token_str}"
    # Print directly in server log for easy clicking in development without Quoted-Printable encoding
    print(f"\n=======================================================\n[PASSWORD RESET LINK]: {link}\n=======================================================\n", flush=True)
    subject = "Reset your OncoSphere password"
    body = (
        f"Hi {user.first_name or user.username},\n\n"
        f"We received a request to reset the password for your OncoSphere account.\n\n"
        f"Click the link below to choose a new password (valid for {EXPIRY_HOURS} hours):\n\n"
        f"  {link}\n\n"
        f"If you did not request a password reset, you can safely ignore this e-mail.\n\n"
        f"-- The OncoSphere team"
    )
    email_user(user, subject, body)


class ForgotPasswordView(APIView):
    """Step 1: user submits their e-mail; we send a reset link if the account exists."""
    permission_classes = [permissions.AllowAny]
    throttle_scope = "register"

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        if not email:
            return Response({"email": ["This field is required."]}, status=400)

        # Always 200 — never reveal whether an account exists.
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            PasswordResetToken.objects.filter(user=user, used=False).update(used=True)
            token_str = secrets.token_hex(32)
            PasswordResetToken.objects.create(user=user, token=token_str)
            _send_reset_email(user, token_str)

        return Response({"detail": (
            "If that e-mail address is registered, you will receive a reset link shortly."
        )})


class ResetPasswordView(APIView):
    """Step 2: user clicks the link, submits { token, new_password }."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token_str = (request.data.get("token") or "").strip().strip("'\"").rstrip(".,;")
        # Handle Quoted-Printable artifacts from terminal-printed emails (where '=' becomes '=3D' and lines wrap with '=')
        token_str = token_str.replace("=\n", "").replace("=\r\n", "").replace("\n", "").replace("\r", "")
        if token_str.startswith(("3D", "3d")) and len(token_str) > 64:
            token_str = token_str[2:]
        token_str = token_str.replace("=", "").strip()
        new_password = request.data.get("new_password") or ""

        if not token_str:
            return Response({"token": ["Token is required."]}, status=400)
        if not new_password:
            return Response({"new_password": ["New password is required."]}, status=400)

        reset = PasswordResetToken.objects.select_related("user").filter(token__iexact=token_str).first()
        if not reset:
            return Response({"token": ["This reset link is invalid or has already been used."]}, status=400)

        if not reset.is_valid():
            return Response({"token": [
                "This reset link has expired or was already used. Please request a new one."
            ]}, status=400)

        user = reset.user
        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as exc:
            return Response({"new_password": list(exc.messages)}, status=400)

        user.set_password(new_password)
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password"])

        reset.used = True
        reset.save(update_fields=["used"])

        return Response({"detail": "Password reset successfully. You can now sign in with your new password."})
