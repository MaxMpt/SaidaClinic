import os
from pathlib import Path
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
DEBUG = os.environ.get("DEBUG", "1") not in {"0", "false", "False"}
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "*").split(",") if h.strip()]

csrf = os.environ.get("CSRF_TRUSTED_ORIGINS", "")
mini = os.environ.get("MINI_APP_URL", "").rstrip("/")
CSRF_TRUSTED_ORIGINS = [x.strip() for x in csrf.split(",") if x.strip()]
if mini and mini not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(mini)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "clinic.apps.ClinicConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "docsaya.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]
WSGI_APPLICATION = "docsaya.wsgi.application"

db_url = os.environ.get("DATABASE_URL", "").strip()
if db_url:
    u = urlparse(db_url)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote((u.path or "/docsaya").lstrip("/").split("?")[0]),
            "USER": unquote(u.username or "docsaya"),
            "PASSWORD": unquote(u.password or ""),
            "HOST": u.hostname or "127.0.0.1",
            "PORT": str(u.port or 5432),
            "CONN_MAX_AGE": 60,
        }
    }
elif DEBUG:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    raise RuntimeError("На сервере нужен DATABASE_URL с PostgreSQL.")

AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
X_FRAME_OPTIONS = "ALLOWALL"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
if not DEBUG:
    use_https = (os.environ.get("MINI_APP_URL") or "").startswith("https")
    CSRF_COOKIE_SECURE = use_https
    SESSION_COOKIE_SECURE = use_https
    CSRF_COOKIE_SAMESITE = "None" if use_https else "Lax"
    SESSION_COOKIE_SAMESITE = "None" if use_https else "Lax"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
MINI_APP_URL = mini
ADMIN_TELEGRAM_ID = os.environ.get("ADMIN_TELEGRAM_ID", "6935237776").strip()
