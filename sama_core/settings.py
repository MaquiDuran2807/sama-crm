import os
from pathlib import Path

from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-env")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'ingesta',
    'tenants.apps.TenantsConfig',
    'crm.apps.CrmConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'sama_core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'sama_core.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.getenv('DB_NAME', 'db.sqlite3').strip(),
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'es-es'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

TEMPLATES[0]['DIRS'] = [BASE_DIR / 'templates']

EVOLUTION_BASE_URL = os.getenv('EVOLUTION_BASE_URL', 'http://localhost:8080')
EVOLUTION_API_KEY = os.getenv('EVOLUTION_API_KEY', '')
EVOLUTION_INSTANCES_ENDPOINT = os.getenv('EVOLUTION_INSTANCES_ENDPOINT', '/instance/fetchInstances')
EVOLUTION_MESSAGES_ENDPOINT = os.getenv('EVOLUTION_MESSAGES_ENDPOINT', '/message/findMessages')
EVOLUTION_SYNC_OVERLAP_HOURS = int(os.getenv('EVOLUTION_SYNC_OVERLAP_HOURS', '6'))
EVOLUTION_STOP_AFTER_STALE_PAGES = int(os.getenv('EVOLUTION_STOP_AFTER_STALE_PAGES', '2'))

OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.2')
AI_SUMMARY_TIMEOUT_SECONDS = int(os.getenv('AI_SUMMARY_TIMEOUT_SECONDS', '90'))
AI_SUMMARY_SCHEDULER_ENABLED = os.getenv('AI_SUMMARY_SCHEDULER_ENABLED', 'True').lower() == 'true'
AI_SUMMARY_STARTUP_LOOKBACK_HOURS = int(os.getenv('AI_SUMMARY_STARTUP_LOOKBACK_HOURS', '48'))
AI_SUMMARY_CHECK_INTERVAL_SECONDS = int(os.getenv('AI_SUMMARY_CHECK_INTERVAL_SECONDS', '300'))

# Audio Briefing (Piper-TTS)
PIPER_VOICE_MODEL = os.getenv('PIPER_VOICE_MODEL', 'es_ES-davefx-medium')
PIPER_VOICE_FALLBACKS = os.getenv('PIPER_VOICE_FALLBACKS', 'es_ES-davefx-medium,es_MX-claude-high,es_MX-ald-medium')
PIPER_USE_GPU = os.getenv('PIPER_USE_GPU', 'True').lower() == 'true'
PIPER_GPU_DEVICE = int(os.getenv('PIPER_GPU_DEVICE', '0'))
AUTO_SEND_BRIEFING_AUDIO = os.getenv('AUTO_SEND_BRIEFING_AUDIO', 'False').lower() == 'true'
AUDIO_BRIEFING_ENABLED = os.getenv('AUDIO_BRIEFING_ENABLED', 'True').lower() == 'true'
AUDIO_BRIEFING_MAX_CLIENTS = int(os.getenv('AUDIO_BRIEFING_MAX_CLIENTS', '20'))
AUDIO_BRIEFING_MAX_SUMMARY_CHARS = int(os.getenv('AUDIO_BRIEFING_MAX_SUMMARY_CHARS', '380'))
AUDIO_BRIEFING_MAX_SAMPLE_CHARS = int(os.getenv('AUDIO_BRIEFING_MAX_SAMPLE_CHARS', '160'))
AUDIO_BRIEFING_MAX_TOTAL_CHARS = int(os.getenv('AUDIO_BRIEFING_MAX_TOTAL_CHARS', '12000'))
AUDIO_BRIEFING_TTS_SPEED = float(os.getenv('AUDIO_BRIEFING_TTS_SPEED', '0.7'))

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
