"""TriageDock settings. Production requires explicit credentials."""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.getenv("DJANGO_DEBUG", "0").lower() in {"1", "true", "yes"}
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY") or (
    "unsafe-development-key-not-for-deployment" if DEBUG else ""
)
if not SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set outside development")

def _strong_secret(value, name, minimum=32):
    if (not value or len(value) < minimum or len(set(value)) < 8
            or value.lower().startswith(("replace-", "change-", "unsafe-", "example"))):
        raise ImproperlyConfigured(f"{name} must be a unique, non-example secret of at least {minimum} characters")

if not DEBUG:
    _strong_secret(SECRET_KEY, "DJANGO_SECRET_KEY")
    _strong_secret(os.getenv("INGEST_API_KEY", ""), "INGEST_API_KEY")
    if os.getenv("DATABASE_ENGINE", "postgresql") != "sqlite":
        _strong_secret(os.getenv("POSTGRES_PASSWORD", ""), "POSTGRES_PASSWORD", 16)

ALLOWED_HOSTS = [
    item.strip() for item in os.getenv(
        "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1"
    ).split(",") if item.strip()
]
CSRF_TRUSTED_ORIGINS = [
    item.strip() for item in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if item.strip()
]
CSRF_COOKIE_SECURE = os.getenv("SECURE_COOKIES", "0") == "1"
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_REFERRER_POLICY = "same-origin"
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "0") == "1"
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv("SECURE_HSTS_SUBDOMAINS", "0") == "1"
if os.getenv("TRUST_PROXY_SSL_HEADER", "0") == "1":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "incidents",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "config.security_headers.DashboardSecurityHeaders",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"

if os.getenv("DATABASE_ENGINE", "postgresql") == "sqlite":
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }}
else:
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "triagedock"),
        "USER": os.getenv("POSTGRES_USER", "triagedock"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
        "HOST": os.getenv("POSTGRES_HOST", "db"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    }}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []
STORAGES = {"staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"user": "120/min", "anon": "30/min", "ingest": "60/min"},
}

# Shared cache is required for limits across multiple Gunicorn worker processes.
CACHES = {"default": {
    "BACKEND": ("django.core.cache.backends.locmem.LocMemCache"
                if DEBUG and os.getenv("DATABASE_ENGINE") == "sqlite" else
                "django.core.cache.backends.redis.RedisCache"),
    **({} if DEBUG and os.getenv("DATABASE_ENGINE") == "sqlite" else
       {"LOCATION": os.getenv("REDIS_CACHE_URL", "redis://redis:6379/1")}),
}}
DATA_UPLOAD_MAX_MEMORY_SIZE = 65536

INGEST_API_KEY = os.getenv("INGEST_API_KEY", "")
INGEST_SHARED_KEY_ENABLED = os.getenv("INGEST_SHARED_KEY_ENABLED", "1") == "1"
NOTIFICATION_WEBHOOK_URL = os.getenv("NOTIFICATION_WEBHOOK_URL", "")
if NOTIFICATION_WEBHOOK_URL:
    from incidents.webhook import validate_webhook_url
    webhook_host = validate_webhook_url(NOTIFICATION_WEBHOOK_URL)
    allowed_hosts = {
        host.strip().lower() for host in
        os.getenv("NOTIFICATION_WEBHOOK_ALLOWED_HOSTS", "").split(",") if host.strip()
    }
    if not DEBUG and webhook_host not in allowed_hosts:
        raise ImproperlyConfigured(
            "Production webhook host must appear in NOTIFICATION_WEBHOOK_ALLOWED_HOSTS"
        )
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_TASK_IGNORE_RESULT = True
CELERY_TIMEZONE = "UTC"
