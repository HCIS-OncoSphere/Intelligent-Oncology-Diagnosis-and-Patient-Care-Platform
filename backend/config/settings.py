import getpass
import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env_file(path):
    """Read KEY=VALUE lines from backend/.env into os.environ (real env vars win)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file(BASE_DIR / ".env")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me-please-use-a-long-random-key-123")
DEBUG = os.getenv("DEBUG", "1") == "1"

# SECURITY: Restrict hosts. Production should override via the ALLOWED_HOSTS
# environment variable (comma-separated list).
_env_hosts = os.getenv("ALLOWED_HOSTS", "")
ALLOWED_HOSTS = (
    [h.strip() for h in _env_hosts.split(",") if h.strip()]
    if _env_hosts
    else ["localhost", "127.0.0.1", "0.0.0.0"]
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "corsheaders",
    "accounts",
    "patients",
    "appointments",
    "imaging",
    "reports",
    "billing",
    "records",
    "integration.apps.IntegrationConfig",
    "administration",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # CorsMiddleware must be placed before CommonMiddleware
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "administration.middleware.AuditMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {
        "context_processors": [
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
        ]
    },
}]

WSGI_APPLICATION = "config.wsgi.application"

# Database, in order of preference:
#   1. DATABASE_URL (e.g. the Neon connection string, sslmode=require included)
#   2. DB_ENGINE=postgres plus DB_* variables (DB_SSLMODE=require for Neon)
#   3. SQLite, only when USE_SQLITE=1 (otherwise startup stops with an error,
#      so nobody silently works on a private SQLite file instead of Neon)
_database_url = os.getenv("DATABASE_URL", "").strip()
if _database_url:
    _url = urlparse(_database_url)
    if _url.scheme not in ("postgres", "postgresql"):
        raise ValueError("DATABASE_URL must start with postgres:// or postgresql://")
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(_url.path.lstrip("/")),
            "USER": unquote(_url.username or ""),
            "PASSWORD": unquote(_url.password or ""),
            "HOST": _url.hostname or "",
            "PORT": str(_url.port or 5432),
            # Query params such as sslmode / channel_binding go straight to libpq.
            "OPTIONS": dict(parse_qsl(_url.query)),
            # Opening a connection to Neon (TCP + TLS + SCRAM login) takes ~1 s from
            # Egypt. A connection pool (psycopg 3) opens a few once and every request
            # borrows one, even under `runserver`. `runserver` starts a new thread per
            # request, so CONN_MAX_AGE alone would reconnect every time. Django
            # requires CONN_MAX_AGE = 0 when pooling. Set DB_POOL=0 to turn the pool off.
            "CONN_MAX_AGE": 0,
            # With the pool on, this makes the pool test a connection before handing
            # it out (one quick round trip), so a connection Neon dropped while
            # idle is replaced instead of failing the request.
            "CONN_HEALTH_CHECKS": True,
            # Neon's "-pooler" host is PgBouncer in transaction mode, which
            # cannot hold Django's server-side cursors.
            "DISABLE_SERVER_SIDE_CURSORS": "-pooler" in (_url.hostname or ""),
        }
    }
    if os.getenv("DB_POOL", "1") != "0":
        DATABASES["default"]["OPTIONS"]["pool"] = {
            "min_size": 1,   # keep one connection open and ready
            "max_size": int(os.getenv("DB_POOL_MAX", "4")),  # several teammates share Neon's connection limit
            "max_idle": 240,  # close spare idle connections before Neon suspends the compute (5 min)
            "timeout": 30,    # seconds to wait for a free connection before erroring
        }
    else:
        DATABASES["default"]["CONN_MAX_AGE"] = int(os.getenv("DB_CONN_MAX_AGE", "60"))
    # Teammates share one Neon project, so give each person's `manage.py test`
    # its own throwaway database instead of everyone fighting over test_neondb.
    _who = "".join(c for c in getpass.getuser().lower() if c.isalnum()) or "dev"
    DATABASES["default"]["TEST"] = {"NAME": f"test_{DATABASES['default']['NAME']}_{_who}"}
elif os.getenv("DB_ENGINE") == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "oncosphere"),
            "USER": os.getenv("DB_USER", "postgres"),
            "PASSWORD": os.getenv("DB_PASSWORD", "postgres"),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
            "OPTIONS": {"sslmode": os.getenv("DB_SSLMODE", "prefer")},
            "DISABLE_SERVER_SIDE_CURSORS": "-pooler" in os.getenv("DB_HOST", ""),
        }
    }
elif os.getenv("USE_SQLITE") == "1":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    raise ImproperlyConfigured(
        "No database configured. The team uses the shared Neon database:\n"
        "  copy backend/.env.example to backend/.env and paste the DATABASE_URL\n"
        "  the team lead sent you (never commit it - the repo is public).\n"
        "To work offline on a local SQLite file instead, set USE_SQLITE=1."
    )

AUTH_USER_MODEL = "accounts.User"

# Argon2 first: Django's recommended hasher. It takes ~50-100 ms per password here,
# where the default PBKDF2 (1M iterations) took ~2 s on each sign-up and each login.
# The others stay listed so passwords saved earlier with PBKDF2 still work; Django
# re-hashes them with Argon2 the next time each user logs in.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

# Password rules = the ones shown on the sign-up page: at least 8 characters, not only numbers.
# (No "too similar to your username" / "too common" checks: their messages confused users.)
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

STATIC_URL = "static/"

# Uploaded files (profile photos and covers). Served by Django only while DEBUG is on;
# in production let the web server serve MEDIA_ROOT.
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", BASE_DIR / "media"))
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "Africa/Cairo"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # public sign-up pages are limited per IP (only views that set throttle_scope = "register")
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.ScopedRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"register": os.getenv("REGISTER_RATE", "60/hour")},
}

# E-mail (approval decisions, new-account credentials). With no EMAIL_HOST set, messages are printed in the
# server console. To send for real, put EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD in .env
# (Gmail: smtp.gmail.com, port 587, an "app password").
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
if EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "1") == "1"
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "OncoSphere <no-reply@oncosphere.local>")

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
}

# CORS — allow the React dev server and production frontend.
# Production should set CORS_ALLOWED_ORIGINS via environment variable.
_cors_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
if _cors_origins:
    CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_origins.split(",") if o.strip()]
else:
    # Development defaults
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

SPECTACULAR_SETTINGS = {"TITLE": "OncoSphere API", "VERSION": "0.2.0"}

# HL7 v2 MLLP link
HL7_ENABLED = os.getenv("HL7_ENABLED", "0") == "1"
HL7_HOST = os.getenv("HL7_HOST", "127.0.0.1")
HL7_PORT = int(os.getenv("HL7_PORT", "2575"))


# Orthanc (DICOM archive) used by the imaging app
ORTHANC_URL = os.getenv("ORTHANC_URL", "http://localhost:8042")

# Google OAuth client ID (Web application) for "Sign in with Google".
# Set this in backend/.env (never commit it). Optional: if set, the Google ID
# token's audience is checked against it so only your app's tokens are accepted.
GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
