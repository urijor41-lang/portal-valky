
from pathlib import Path
import os

# =====================================================
# RUTAS DEL PROYECTO
# =====================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# =====================================================
# SEGURIDAD
# =====================================================

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")

if not SECRET_KEY:
    raise ValueError("No se ha configurado DJANGO_SECRET_KEY")


DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = os.environ.get(
    "DJANGO_ALLOWED_HOSTS",
    "127.0.0.1,localhost"
).split(",")


# =====================================================
# APLICACIONES
# =====================================================

INSTALLED_APPS = [
    "portal",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]


# =====================================================
# MIDDLEWARE
# =====================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# =====================================================
# CONFIGURACIÓN GENERAL
# =====================================================

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


# =====================================================
# BASE DE DATOS
# =====================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# =====================================================
# VALIDACIÓN DE CONTRASEÑAS
# =====================================================

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


# =====================================================
# IDIOMA Y ZONA HORARIA
# =====================================================

LANGUAGE_CODE = "es"

TIME_ZONE = "America/Bogota"

USE_I18N = True

USE_TZ = True


# =====================================================
# ARCHIVOS ESTÁTICOS
# =====================================================

STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "staticfiles"


# =====================================================
# ARCHIVOS MULTIMEDIA
# =====================================================

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# =====================================================
# SEGURIDAD ADICIONAL EN PRODUCCIÓN
# =====================================================

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"


# =====================================================
# CLAVE PRIMARIA POR DEFECTO
# =====================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
