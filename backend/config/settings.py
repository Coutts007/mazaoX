"""Django settings for MazaoX. All environment-specific values come from env vars."""

from datetime import timedelta
from pathlib import Path

import environ
from corsheaders.defaults import default_headers

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent

env = environ.Env(DJANGO_DEBUG=(bool, False))
environ.Env.read_env(REPO_ROOT / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "rest_framework_simplejwt.token_blacklist",
    "core",
    "apps.identity",
    "apps.profiles",
    "apps.catalogue",
    "apps.inventory",
    "apps.orders",
    "apps.payments",
    "apps.notifications",
    "apps.delivery",
    "apps.reviews",
    "apps.issues",
    "apps.audit",
    "apps.quality",
    "apps.administration",
    "apps.demand",
]

MIDDLEWARE = [
    "core.middleware.RequestIdMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "core.middleware.ApiNoStoreMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST", default="localhost"),
        "PORT": env("DB_PORT", default="5433"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = env("MEDIA_ROOT", default=str(REPO_ROOT / "media"))  # uploads live on disk, never in PostgreSQL

AUTH_USER_MODEL = "identity.User"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:5180"])
CORS_ALLOW_CREDENTIALS = True  # the refresh token travels in an httpOnly cookie
CORS_ALLOW_HEADERS = [*default_headers, "idempotency-key"]
CORS_EXPOSE_HEADERS = ["Idempotent-Replay", "X-Request-ID", "X-Cache"]
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# ---- Cache (Redis when REDIS_URL is set, per-process memory otherwise) ----
REDIS_URL = env("REDIS_URL", default="")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "KEY_PREFIX": "mazaox",
            "TIMEOUT": 300,
            "OPTIONS": {"socket_connect_timeout": 1, "socket_timeout": 1},  # fail fast; callers fail open
        }
    }
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "KEY_PREFIX": "mazaox"}}
PUBLIC_CACHE_ENABLED = env.bool("PUBLIC_CACHE_ENABLED", default=True)

# ---- Static files (Django admin CSS) ----
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# ---- Security ----
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_SSL = env.bool("SECURE_SSL", default=False)  # set true behind HTTPS in hosted environments
if SECURE_SSL:
    SECURE_SSL_REDIRECT = True
    SECURE_REDIRECT_EXEMPT = [r"^api/v1/health$"]
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = env.int("HSTS_SECONDS", default=31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# ---- Logging (every line carries the request id) ----
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"request_id": {"()": "core.middleware.RequestIdFilter"}},
    "formatters": {"std": {"format": "%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "filters": ["request_id"], "formatter": "std"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
    "loggers": {"django.server": {"level": "WARNING"}},
}

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "EXCEPTION_HANDLER": "core.exceptions.api_exception_handler",
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": ["core.throttling.SafeAnonRateThrottle", "core.throttling.SafeUserRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": "120/min", "user": "600/min", "auth": "20/min"},
}

SPECTACULAR_SETTINGS = {
    "TITLE": "MazaoX API",
    "DESCRIPTION": "Kenyan agricultural produce marketplace (academic prototype). Payments are simulated only.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api/v1",
    "COMPONENT_SPLIT_REQUEST": True,
}
API_DOCS_ENABLED = env.bool("API_DOCS_ENABLED", default=DEBUG)

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,  # rotation is done explicitly in the refresh view
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Listing photos (stored outside PostgreSQL via Django's replaceable storage backend).
MEDIA_MAX_BYTES = env.int("MEDIA_MAX_BYTES", default=5 * 1024 * 1024)
MEDIA_MAX_PIXELS = 36_000_000
MEDIA_MAX_PER_LISTING = 8
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024  # request bodies larger than this are rejected early

# Inventory: how long an unpaid order holds stock (minutes).
RESERVATION_TTL_MINUTES = env.int("RESERVATION_TTL_MINUTES", default=15)

# Payments are SIMULATED. The completion endpoint is a demo tool: keep it off in any hosted environment.
PAYMENT_SIMULATION_ENABLED = env.bool("PAYMENT_SIMULATION_ENABLED", default=False)
