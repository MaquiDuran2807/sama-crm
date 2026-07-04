# SPDX-License-Identifier: MIT
# Copyright (c) 2026 SAMA AdTech

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-env")

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "django_extensions",
    "ingesta",
    "tenants.apps.TenantsConfig",
    "crm.apps.CrmConfig",
    "auth.apps.AuthConfig",
    "core.apps.CoreConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "sama_core.audit_middleware.AuditLogMiddleware",
]

ROOT_URLCONF = "sama_core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates", BASE_DIR / "auth" / "templates"],
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

WSGI_APPLICATION = "sama_core.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "es-es"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
    BASE_DIR / "auth" / "static",
    BASE_DIR / "core" / "static",
]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("THROTTLE_ANON_RATE", "10/minute"),
        "user": os.getenv("THROTTLE_USER_RATE", "100/minute"),
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "SAMA AdTech API",
    "DESCRIPTION": "CRM multi-tenant para la industria AdTech. Gestión de leads, contactos, products, y pipeline de ventas con integración de WhatsApp e IA.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/",
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": False,
    },
}

SECURE_CONTENT_TYPE_NOSNIFF = os.getenv(
    "SECURE_CONTENT_TYPE_NOSNIFF", "True"
).lower() == "true"

LOGIN_REDIRECT_URL = "/"

EVOLUTION_BASE_URL = os.getenv("EVOLUTION_BASE_URL", "http://localhost:8080")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "")
EVOLUTION_INSTANCES_ENDPOINT = os.getenv(
    "EVOLUTION_INSTANCES_ENDPOINT", "/instance/fetchInstances"
)
EVOLUTION_MESSAGES_ENDPOINT = os.getenv(
    "EVOLUTION_MESSAGES_ENDPOINT", "/message/findMessages"
)
EVOLUTION_SYNC_OVERLAP_HOURS = int(os.getenv("EVOLUTION_SYNC_OVERLAP_HOURS", "6"))
EVOLUTION_STOP_AFTER_STALE_PAGES = int(
    os.getenv("EVOLUTION_STOP_AFTER_STALE_PAGES", "2")
)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
AI_SUMMARY_TIMEOUT_SECONDS = int(os.getenv("AI_SUMMARY_TIMEOUT_SECONDS", "90"))
AI_SUMMARY_SCHEDULER_ENABLED = (
    os.getenv("AI_SUMMARY_SCHEDULER_ENABLED", "True").lower() == "true"
)
AI_SUMMARY_STARTUP_LOOKBACK_HOURS = int(
    os.getenv("AI_SUMMARY_STARTUP_LOOKBACK_HOURS", "48")
)
AI_SUMMARY_CHECK_INTERVAL_SECONDS = int(
    os.getenv("AI_SUMMARY_CHECK_INTERVAL_SECONDS", "300")
)

PIPER_VOICE_MODEL = os.getenv("PIPER_VOICE_MODEL", "es_ES-davefx-medium")
PIPER_VOICE_FALLBACKS = os.getenv(
    "PIPER_VOICE_FALLBACKS", "es_ES-davefx-medium,es_MX-claude-high,es_MX-ald-medium"
)
PIPER_USE_GPU = os.getenv("PIPER_USE_GPU", "True").lower() == "true"
PIPER_GPU_DEVICE = int(os.getenv("PIPER_GPU_DEVICE", "0"))
AUTO_SEND_BRIEFING_AUDIO = (
    os.getenv("AUTO_SEND_BRIEFING_AUDIO", "False").lower() == "true"
)
AUDIO_BRIEFING_ENABLED = (
    os.getenv("AUDIO_BRIEFING_ENABLED", "True").lower() == "true"
)
AUDIO_BRIEFING_MAX_CLIENTS = int(os.getenv("AUDIO_BRIEFING_MAX_CLIENTS", "20"))
AUDIO_BRIEFING_MAX_SUMMARY_CHARS = int(
    os.getenv("AUDIO_BRIEFING_MAX_SUMMARY_CHARS", "380")
)
AUDIO_BRIEFING_MAX_SAMPLE_CHARS = int(
    os.getenv("AUDIO_BRIEFING_MAX_SAMPLE_CHARS", "160")
)
AUDIO_BRIEFING_MAX_TOTAL_CHARS = int(
    os.getenv("AUDIO_BRIEFING_MAX_TOTAL_CHARS", "12000")
)
AUDIO_BRIEFING_TTS_SPEED = float(os.getenv("AUDIO_BRIEFING_TTS_SPEED", "0.7"))

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "change-me-in-env")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": "%(message)s",
        },
    },
    "handlers": {
        "audit_file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "audit.log",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "json",
        },
    },
    "loggers": {
        "sama.audit": {
            "handlers": ["audit_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "local_auth.User"

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379/0"
)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

from datetime import timedelta  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    "auto-advance-stale-leads-every-4h": {
        "task": "crm.tasks.auto_advance_stale_leads",
        "schedule": timedelta(hours=4),
    },
    "permanently-delete-old-leads-daily": {
        "task": "crm.tasks.permanently_delete_old_leads",
        "schedule": timedelta(days=1),
    },
    "send-task-reminders-every-hour": {
        "task": "crm.tasks.send_task_reminders",
        "schedule": timedelta(hours=1),
    },
    "ai-summary-scheduler-every-5m": {
        "task": "ingesta.tasks.ai_summary_periodic_task",
        "schedule": timedelta(seconds=300),
    },
}
