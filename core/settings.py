"""Django settings for Scare-TV. Everything is read from environment variables (a .env file locally)."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env(name, default=""):
    """Like os.getenv, but an empty variable ("NAME=") counts as unset."""
    return os.getenv(name, "").strip() or default


SECRET_KEY = env("DJANGO_SECRET_KEY", "development-only-scare-tv-nothing-secret-here")
DEBUG = env("DJANGO_DEBUG", "1").lower() in ("1", "true", "yes")
ALLOWED_HOSTS = [h.strip() for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,.lhr.life,.pinggy.link").split(",") if h.strip()]
if env("RENDER_EXTERNAL_HOSTNAME"):                    # set by Render on the deployed web service
    ALLOWED_HOSTS.append(env("RENDER_EXTERNAL_HOSTNAME"))
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "domain.apps.DomainConfig",
    "infrastructure.apps.InfrastructureConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",      # serves the web mirror (web/) efficiently, also in production
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "core.urls"
ASGI_APPLICATION = "core.asgi.application"
WSGI_APPLICATION = "core.wsgi.application"
TEMPLATES = []

# The night log: numbers only, never images or sound.
DB_PATH = Path(env("SCARE_TV_DB", str(BASE_DIR / "data" / "scare_tv.sqlite3")))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(DB_PATH),
    }
}
if env("DATABASE_URL"):                                # production (Render): PostgreSQL
    import dj_database_url

    DATABASES["default"] = dj_database_url.parse(env("DATABASE_URL"), conn_max_age=600)
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = env("TIME_ZONE", "Europe/Madrid")
LANGUAGE_CODE = "en-us"

STATIC_URL = "static/"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "UNAUTHENTICATED_USER": None,
}

WHITENOISE_ROOT = BASE_DIR / "web"
WHITENOISE_INDEX_FILE = True

SCARE_TV = {
    "MEDIA_DIR": BASE_DIR / "media",
    "REAL_MEDIA_DIR": BASE_DIR / "media_real",
    "WEB_DIR": BASE_DIR / "web",
    "ASSETS_DIR": BASE_DIR / "assets",
    "LOGS_DIR": Path(env("SCARE_TV_LOGS", str(BASE_DIR / "logs"))),
    "POSE_MODEL": BASE_DIR / "yolo11n-pose.pt",
}
