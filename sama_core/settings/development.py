# SPDX-License-Identifier: MIT
# Copyright (c) 2026 SAMA AdTech

from .base import *

DEBUG = True

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

DB_ENGINE = os.getenv("DB_ENGINE", "django.db.backends.sqlite3")

if "postgresql" in DB_ENGINE:
    DATABASES = {
        "default": {
            "ENGINE": DB_ENGINE,
            "NAME": os.getenv("DB_NAME", "sama_dev"),
            "USER": os.getenv("DB_USER", "sama"),
            "PASSWORD": os.getenv("DB_PASSWORD", "sama_dev_pass"),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": DB_ENGINE,
            "NAME": os.getenv("DB_NAME", BASE_DIR / "db.sqlite3"),
        }
    }

CACHES = {
    "default": {
        "BACKEND": os.getenv(
            "CACHE_BACKEND",
            "django.core.cache.backends.locmem.LocMemCache",
        ),
        "LOCATION": os.getenv("CACHE_URL", "sama-dev-cache"),
        "KEY_PREFIX": "sama",
    }
}

SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
