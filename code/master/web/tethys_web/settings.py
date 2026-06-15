import os
import sys
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Make the shared `globals` package (code/master/globals) importable so the
# canonical TIME_ZONE can be read from a single source (mirrors the api
# settings). BASE_DIR is the `web/` directory, so its parent is `code/master`.
MASTER_DIR = BASE_DIR.parent
if str(MASTER_DIR) not in sys.path:
    sys.path.insert(0, str(MASTER_DIR))

# Single source of truth for secrets (git-ignored). WEB_SECRET_KEY is this app's
# Django secret; TETHYS_API_KEY is needed because the web backend polls the API
# server-side and the API now requires the key on reads too.
try:
    from globals.secrets import WEB_SECRET_KEY, TETHYS_API_KEY
except ImportError as exc:  # pragma: no cover - configuration error path
    raise ImportError(
        "Missing globals/secrets.py or a required value. Copy "
        "code/master/globals/secrets.example.py to code/master/globals/secrets.py "
        "and set WEB_SECRET_KEY and TETHYS_API_KEY (or run install/install.sh, which "
        "generates them). Existing installs predating the Django key move must add "
        "API_SECRET_KEY / WEB_SECRET_KEY to secrets.py."
    ) from exc

# Attached to every server-side GET/POST the web backend makes against the API.
API_AUTH_HEADERS = {"X-API-Key": TETHYS_API_KEY}


DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
DATETIME_FORMAT_NO_MILL = "%Y-%m-%dT%H:%M:%S"
LOGGING_INDENT_INNER = " > "
LOGGING_INDENT_OUTER = " ▩▩▩▩ "
API_BASE = ":5000/api/"
API_URL = "http://localhost" + API_BASE
POLL_FREQUENCY_SEC = 10
CHANNEL_GROUP_NAME = "tethys.websocket.clients"


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# Secret key now lives in the git-ignored globals/secrets.py (imported above).
SECRET_KEY = WEB_SECRET_KEY

# Off by default; opt in for local dev with TETHYS_DEBUG=1. The systemd units set
# this from the installer's --debug flag (default false).
DEBUG = os.environ.get("TETHYS_DEBUG") == "1"

# Base hosts plus any supplied via TETHYS_ALLOWED_HOSTS (comma-separated), e.g. a
# Tailscale name like tethys.<tailnet>.ts.net for remote (VPN) access.
ALLOWED_HOSTS = [
    "tethys.local",
    "127.0.0.1",
    "localhost"]
ALLOWED_HOSTS += [h for h in os.environ.get("TETHYS_ALLOWED_HOSTS", "").split(",") if h]

# Plus any hostnames from the optional git-ignored globals/allowed_hosts.py (e.g. a
# Tailscale name). Mirrors globals/secrets.py but is NON-FATAL when missing: an absent
# file just means no extra hosts. See globals/allowed_hosts.example.py.
try:
    from globals.allowed_hosts import EXTRA_ALLOWED_HOSTS
except ImportError:
    EXTRA_ALLOWED_HOSTS = []
ALLOWED_HOSTS += [h for h in EXTRA_ALLOWED_HOSTS if h]


# Application definition

INSTALLED_APPS = [
    "daphne",
    "channels",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "tethys_web",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "tethys_web.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        
        "DIRS": [
            './templates',
            './web/templates',
        ],
        
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


TEMPLATE_DIRS = (os.path.join(BASE_DIR, "templates"),)

WSGI_APPLICATION = "tethys_web.wsgi.application"

ASGI_APPLICATION = "tethys_web.asgi.application"


CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        
        "CONFIG": {
            "hosts": [
                ('127.0.0.1', 6379),
            ],
        },
    },
}


'''
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}
'''


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en-us"

# Sourced from the single canonical definition (globals/config.py).
from globals.config import TIME_ZONE

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticcollect/')
#STATICFILES_DIRS = ['/static/']

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]


# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
