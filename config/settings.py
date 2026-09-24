from pathlib import Path
import os
from datetime import timedelta

from dotenv import load_dotenv


# ============================================================
# BASE CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env
load_dotenv(BASE_DIR / ".env")


# ============================================================
# SECURITY
# ============================================================

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "dev-secret-key-change-this-in-production"
)

DEBUG = os.getenv("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "ALLOWED_HOSTS",
        "127.0.0.1,localhost"
    ).split(",")
    if host.strip()
]


# Application port
# NOTE:
# Django does not automatically use this value with runserver.
# It is mainly kept here so the application configuration has
# a single place for the configured port.
APP_PORT = int(os.getenv("APP_PORT", "8003"))


# ============================================================
# APPLICATIONS
# ============================================================

INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "corsheaders",
    "rest_framework",
    "django_filters",

    # KukuFarm applications
    "apps.accounts",
    "apps.flocks",
    "apps.production",
    "apps.feed",
    "apps.health",
    "apps.customers",
    "apps.sales",
    "apps.expenses",
    "apps.suppliers",
    "apps.reports",
    "apps.settings",
]


# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",

    "django.middleware.security.SecurityMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",

    "django.middleware.common.CommonMiddleware",

    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",

    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ============================================================
# URL / WSGI / ASGI
# ============================================================

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"

ASGI_APPLICATION = "config.asgi.application"


# ============================================================
# TEMPLATES
# ============================================================

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


# ============================================================
# DATABASE
#
# Supported:
#   sqlite
#   mysql
#   postgres / postgresql
#
# Select database using:
#
# DB_ENGINE=mysql
# DB_ENGINE=postgres
# DB_ENGINE=sqlite
# ============================================================

DB_ENGINE = os.getenv("DB_ENGINE", "sqlite").lower()


if DB_ENGINE == "mysql":

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",

            "NAME": os.getenv(
                "DB_NAME",
                "kukufarm"
            ),

            "USER": os.getenv(
                "DB_USER",
                "root"
            ),

            "PASSWORD": os.getenv(
                "DB_PASSWORD",
                ""
            ),

            "HOST": os.getenv(
                "DB_HOST",
                "127.0.0.1"
            ),

            "PORT": os.getenv(
                "DB_PORT",
                "3306"
            ),

            "OPTIONS": {
                "charset": "utf8mb4",
            },

            "CONN_MAX_AGE": 60,
        }
    }


elif DB_ENGINE in ("postgres", "postgresql"):

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",

            "NAME": os.getenv(
                "DB_NAME",
                "kukufarm"
            ),

            "USER": os.getenv(
                "DB_USER",
                "postgres"
            ),

            "PASSWORD": os.getenv(
                "DB_PASSWORD",
                ""
            ),

            "HOST": os.getenv(
                "DB_HOST",
                "127.0.0.1"
            ),

            "PORT": os.getenv(
                "DB_PORT",
                "5432"
            ),

            "CONN_MAX_AGE": 60,
        }
    }


else:

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",

            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# ============================================================
# PASSWORD VALIDATION
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# ============================================================
# INTERNATIONALIZATION
# ============================================================

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Africa/Dar_es_Salaam"

USE_I18N = True

USE_TZ = True


# ============================================================
# STATIC FILES
# ============================================================

STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "staticfiles"


# ============================================================
# MEDIA FILES
# ============================================================

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# ============================================================
# DEFAULT PRIMARY KEY
# ============================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ============================================================
# CORS
# ============================================================

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if origin.strip()
]

CORS_ALLOW_CREDENTIALS = True


# ============================================================
# CSRF TRUSTED ORIGINS
#
# Required when Django is accessed through HTTPS and forms/API
# requests come from trusted frontend domains.
# ============================================================

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CSRF_TRUSTED_ORIGINS",
        ""
    ).split(",")
    if origin.strip()
]


# ============================================================
# DJANGO REST FRAMEWORK
# ============================================================

REST_FRAMEWORK = {

    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),

    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),

    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",

        "rest_framework.filters.SearchFilter",

        "rest_framework.filters.OrderingFilter",
    ),

    "DEFAULT_PAGINATION_CLASS": (
        "rest_framework.pagination.PageNumberPagination"
    ),

    "PAGE_SIZE": 50,
}


# ============================================================
# SIMPLE JWT
# ============================================================

SIMPLE_JWT = {

    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=int(
            os.getenv(
                "JWT_ACCESS_TOKEN_MINUTES",
                "60"
            )
        )
    ),

    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=int(
            os.getenv(
                "JWT_REFRESH_TOKEN_DAYS",
                "7"
            )
        )
    ),

    "AUTH_HEADER_TYPES": (
        "Bearer",
    ),
}


# ============================================================
# HTTPS / PROXY SECURITY
# ============================================================

SECURE_SSL_REDIRECT = (
    os.getenv(
        "SECURE_SSL_REDIRECT",
        "False"
    ).lower() == "true"
)


# Django is behind Nginx in production.
SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)


# ============================================================
# PRODUCTION SECURITY
# ============================================================

if not DEBUG:

    SECURE_CONTENT_TYPE_NOSNIFF = True

    X_FRAME_OPTIONS = "DENY"

    SESSION_COOKIE_SECURE = True

    CSRF_COOKIE_SECURE = True

    SESSION_COOKIE_HTTPONLY = True

    CSRF_COOKIE_HTTPONLY = False

    SECURE_HSTS_SECONDS = 31536000

    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

    SECURE_HSTS_PRELOAD = True


# ============================================================
# LOGGING
# ============================================================

LOG_LEVEL = os.getenv(
    "LOG_LEVEL",
    "INFO"
)


LOGGING = {
    "version": 1,

    "disable_existing_loggers": False,

    "formatters": {
        "verbose": {
            "format": (
                "{levelname} {asctime} "
                "{module} {process:d} {thread:d} "
                "{message}"
            ),
            "style": "{",
        },
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },

    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },

    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}

