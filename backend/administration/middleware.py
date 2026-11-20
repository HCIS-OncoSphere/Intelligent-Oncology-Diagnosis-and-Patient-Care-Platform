from .models import AuditLog


class AuditMiddleware:
    """Logs every successful write (POST/PUT/PATCH/DELETE) to /api/ with the acting user."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (
            request.path.startswith("/api/")
            and request.method in ("POST", "PUT", "PATCH", "DELETE")
            and response.status_code < 400
        ):
            user = None
            auth = request.META.get("HTTP_AUTHORIZATION", "")
            if auth.startswith("Bearer "):
                try:
                    from rest_framework_simplejwt.authentication import JWTAuthentication

                    user = JWTAuthentication().get_user(
                        JWTAuthentication().get_validated_token(auth[7:].encode())
                    )
                except Exception:
                    pass
            elif getattr(request, "user", None) and request.user.is_authenticated:
                user = request.user

            if request.path.startswith("/api/auth/login") or request.path.startswith("/api/auth/refresh"):
                return response

            AuditLog.objects.create(
                user=user,
                action=request.method,
                path=request.path[:255],
                status_code=response.status_code,
                ip_address=request.META.get("REMOTE_ADDR", ""),
            )
        return response
