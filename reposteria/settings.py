"""
Configuracion base del proyecto reposteria.
Preparada para desarrollo y produccion usando variables de entorno.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv(*args, **kwargs):
        return False


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


DEBUG = env_bool("DJANGO_DEBUG", default=True)

if DEBUG:
    SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-dev-key-change-me")
else:
    SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
    if not SECRET_KEY:
        raise ImproperlyConfigured("Debes definir DJANGO_SECRET_KEY cuando DJANGO_DEBUG=False")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", default="127.0.0.1,localhost,192.168.1.4,192.168.1.5")

# Render inyecta el hostname público del servicio
RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

CSRF_TRUSTED_ORIGINS = ["https://*.onrender.com"]
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "BebesitaAPP",
    "gestion",
]

# Cloudinary: almacenamiento permanente de imágenes subidas (admin/productos).
# Solo se activa si existe CLOUDINARY_URL en el entorno; si no, usa el disco local.
# Render borra el disco en cada deploy, por eso las fotos deben vivir en Cloudinary.
CLOUDINARY_URL = os.getenv("CLOUDINARY_URL")
USE_CLOUDINARY = bool(CLOUDINARY_URL)
if USE_CLOUDINARY:
    INSTALLED_APPS += ["cloudinary", "cloudinary_storage"]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "gestion.middleware.GestionLoginRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Acceso a la gestión privada (/panel/)
LOGIN_URL = "gestion:login"
LOGIN_REDIRECT_URL = "gestion:dashboard"
LOGOUT_REDIRECT_URL = "gestion:login"

ROOT_URLCONF = "reposteria.urls"

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
                "BebesitaAPP.context_processors.cart_count",
                "BebesitaAPP.context_processors.site_config",
            ],
        },
    },
]

WSGI_APPLICATION = "reposteria.wsgi.application"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# En producción (Render) usar Postgres vía DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    import dj_database_url

    DATABASES["default"] = dj_database_url.parse(DATABASE_URL, conn_max_age=600)
    # SSL obligatorio solo en Postgres (Render)
    if "postgresql" in DATABASES["default"].get("ENGINE", ""):
        DATABASES["default"].setdefault("OPTIONS", {})["sslmode"] = "require"


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


LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True


STATIC_URL = "/static/"
# Usa carpeta global /static solo si existe.
# Los archivos de la app se toman desde BebesitaAPP/static via AppDirectoriesFinder.
GLOBAL_STATIC_DIR = BASE_DIR / "static"
STATICFILES_DIRS = [GLOBAL_STATIC_DIR] if GLOBAL_STATIC_DIR.exists() else []
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise sirve y comprime los estáticos en producción
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# Si hay Cloudinary, las imágenes subidas (MEDIA) se guardan ahí de forma permanente.
# Los estáticos siguen en WhiteNoise. La librería cloudinary lee CLOUDINARY_URL sola.
if USE_CLOUDINARY:
    STORAGES["default"] = {"BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage"}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


has_smtp_credentials = bool(os.getenv("EMAIL_HOST_USER") and os.getenv("EMAIL_HOST_PASSWORD"))
default_email_backend = (
    "django.core.mail.backends.smtp.EmailBackend"
    if has_smtp_credentials or not DEBUG
    else "django.core.mail.backends.console.EmailBackend"
)
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", default_email_backend)
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "15"))
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "no-reply@dulcecitaa.local")
# Correo de contacto público (se muestra en footer y formularios)
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL") or "contacto@dulcecita.cl"

BRAND_NAME = os.getenv("BRAND_NAME", "Dulcecita")
WEBSITE_URL = os.getenv("WEBSITE_URL", "")
# Botones flotantes de redes
WHATSAPP_URL = os.getenv("WHATSAPP_URL") or "https://wa.me/56961192192"
INSTAGRAM_URL = os.getenv("INSTAGRAM_URL") or "https://instagram.com/dulcecitaa.cl"
SHIPPING_COST = int(os.getenv("SHIPPING_COST", "2500"))
PICKUP_POINT_LABEL = os.getenv("PICKUP_POINT_LABEL", "Retiro coordinado por WhatsApp")
BUSINESS_HOURS = os.getenv("BUSINESS_HOURS", "Lunes a sabado de 09:00 a 19:00")
DEFAULT_OG_IMAGE = os.getenv("DEFAULT_OG_IMAGE", "/static/img/hero/slide1.jpg")


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
