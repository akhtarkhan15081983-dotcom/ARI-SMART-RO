"""Django settings for ARI SMART RO."""

import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name, default=""):
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


def _required_env(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"{name} is required in production.")
    return value


DEBUG = _env_bool("DJANGO_DEBUG", True)

_secret_key = os.getenv("DJANGO_SECRET_KEY", "").strip()
if not _secret_key:
    if not DEBUG:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY is required when DJANGO_DEBUG=0.")
    _secret_key = "django-insecure-local-development-only-change-me"
SECRET_KEY = _secret_key

ALLOWED_HOSTS = ["*"] if DEBUG else _env_list("DJANGO_ALLOWED_HOSTS")
if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS is required when DJANGO_DEBUG=0.")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "partmaster",
    "purchase",
    "inventory",
    "accounts",
    "employees",
    "customers",
    "products",
    "assets",
    "installation",
    "jobs",
    "corsheaders",
    "attendance",
    "django_extensions",
    "service",
    "complaints",
    "referrals",
    "andy",
    "reporting",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
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

_database_name = os.getenv("DB_NAME", "").strip()
if not DEBUG and not _database_name:
    raise ImproperlyConfigured("DB_NAME is required when DJANGO_DEBUG=0; SQLite is development-only.")

if _database_name:
    DATABASES = {
        "default": {
            "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.postgresql"),
            "NAME": _database_name,
            "USER": os.getenv("DB_USER", ""),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "127.0.0.1"),
            "PORT": os.getenv("DB_PORT", "5432"),
            "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "Asia/Kolkata")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_STORAGE_BACKEND = os.getenv(
    "DJANGO_MEDIA_STORAGE_BACKEND",
    "filesystem" if DEBUG else "",
).strip().lower()

if not MEDIA_STORAGE_BACKEND:
    raise ImproperlyConfigured("DJANGO_MEDIA_STORAGE_BACKEND is required in production.")

if MEDIA_STORAGE_BACKEND == "filesystem":
    media_root = os.getenv("DJANGO_MEDIA_ROOT", "").strip()
    if not DEBUG and not media_root:
        raise ImproperlyConfigured(
            "DJANGO_MEDIA_ROOT must point to a persistent mounted volume in production."
        )
    MEDIA_ROOT = Path(media_root) if media_root else BASE_DIR / "media"
elif MEDIA_STORAGE_BACKEND == "s3":
    AWS_ACCESS_KEY_ID = _required_env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = _required_env("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = _required_env("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "ap-south-1").strip()
    AWS_S3_ENDPOINT_URL = os.getenv("AWS_S3_ENDPOINT_URL", "").strip() or None
    AWS_QUERYSTRING_AUTH = True
    AWS_DEFAULT_ACL = None
    AWS_S3_FILE_OVERWRITE = False
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
    }
else:
    raise ImproperlyConfigured(
        "DJANGO_MEDIA_STORAGE_BACKEND must be either 'filesystem' or 's3'."
    )

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = [
    "accounts.backends.PhoneAuthenticationBackend",
    "django.contrib.auth.backends.ModelBackend",
]

DISABLE_AUTH_THROTTLING = _env_bool("DJANGO_DISABLE_AUTH_THROTTLING", False)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "accounts.authentication.VerifiedCustomerJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "login": os.getenv("DJANGO_LOGIN_THROTTLE", "10/min"),
        "otp": os.getenv("DJANGO_OTP_THROTTLE", "5/min"),
    },
}

CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = _env_list(
    "DJANGO_CORS_ALLOWED_ORIGINS",
    (
        "http://localhost:5500,http://127.0.0.1:5500,"
        "http://localhost:3000,http://127.0.0.1:3000"
        if DEBUG
        else ""
    ),
)
CSRF_TRUSTED_ORIGINS = _env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
SECURE_SSL_REDIRECT = _env_bool("DJANGO_SECURE_SSL_REDIRECT", not DEBUG)
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "0" if DEBUG else "3600"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = False

OTP_SMS_BACKEND = os.getenv(
    "OTP_SMS_BACKEND",
    "memory" if DEBUG else "",
).strip().lower()
OTP_SMS_COUNTRY_CODE = os.getenv("OTP_SMS_COUNTRY_CODE", "91").strip()
OTP_SMS_TIMEOUT_SECONDS = int(os.getenv("OTP_SMS_TIMEOUT_SECONDS", "10"))
MSG91_AUTH_KEY = os.getenv("MSG91_AUTH_KEY", "").strip()
MSG91_TEMPLATE_ID = os.getenv("MSG91_TEMPLATE_ID", "").strip()
OTP_SMS_WEBHOOK_URL = os.getenv("OTP_SMS_WEBHOOK_URL", "").strip()
OTP_SMS_WEBHOOK_TOKEN = os.getenv("OTP_SMS_WEBHOOK_TOKEN", "").strip()

if not DEBUG:
    if OTP_SMS_BACKEND == "msg91":
        if not MSG91_AUTH_KEY or not MSG91_TEMPLATE_ID:
            raise ImproperlyConfigured(
                "MSG91_AUTH_KEY and MSG91_TEMPLATE_ID are required for MSG91 OTP delivery."
            )
    elif OTP_SMS_BACKEND == "webhook":
        if not OTP_SMS_WEBHOOK_URL:
            raise ImproperlyConfigured(
                "OTP_SMS_WEBHOOK_URL is required for webhook OTP delivery."
            )
    else:
        raise ImproperlyConfigured(
            "OTP_SMS_BACKEND must be 'msg91' or 'webhook' in production."
        )
