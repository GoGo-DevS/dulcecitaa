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

# --- Acceso desde el celular en la misma red (solo en desarrollo) ---
# Las IPs de esta maquina se detectan solas: escribirlas a mano obliga a
# corregir el archivo cada vez que el router entrega otra, y el sintoma es un
# 400 que no dice que la culpa es de ALLOWED_HOSTS.
if DEBUG:
    import socket
    _nombre = socket.gethostname()
    _ips = {socket.gethostbyname(_nombre)}
    try:
        _ips |= {d[4][0] for d in socket.getaddrinfo(_nombre, None, socket.AF_INET)}
    except OSError:
        pass
    ALLOWED_HOSTS = list(dict.fromkeys(list(ALLOWED_HOSTS) + sorted(_ips)))

# Render inyecta el hostname público del servicio
RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Dominios propios del sitio. Sin esto, al entrar por dulcecita.cl Django
# responde 400 (host no permitido) y los formularios POST (checkout, contacto,
# arma tu box) fallan con 403 de CSRF: solo se confiaba en *.onrender.com.
SITE_DOMAINS = env_list("SITE_DOMAINS", default="dulcecita.cl,www.dulcecita.cl")
ALLOWED_HOSTS = list(dict.fromkeys(list(ALLOWED_HOSTS) + SITE_DOMAINS))

CSRF_TRUSTED_ORIGINS = ["https://*.onrender.com"] + [f"https://{d}" for d in SITE_DOMAINS]
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")

if not DEBUG:
    # Render termina el HTTPS en su proxy y le pasa la peticion a Django por
    # HTTP; esta cabecera es la que dice que el cliente entro por https.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    # WhiteNoise sirve los estaticos tambien en runserver. El servidor de
    # desarrollo de Django no responde pedidos por tramos (Range) y Safari de
    # iPhone NO reproduce un video sin eso: en local se veia solo el poster.
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.sitemaps",
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
                "BebesitaAPP.context_processors.seo",
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
# En produccion, nombres con huella (style.abc123.css): el navegador los guarda
# un año sin volver a pedirlos, y un cambio genera otro nombre. Es lo que mas
# pesa en la velocidad de la segunda visita (Core Web Vitals). En local no:
# obligaria a correr collectstatic tras cada cambio.
if not DEBUG:
    STORAGES["staticfiles"] = {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}

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

# Minimo de compra por producto. La venta es por volumen: no se despacha de a
# una unidad. Va por variable de entorno para poder cambiarlo sin tocar codigo.
MINIMO_UNIDADES = max(1, int(os.getenv("MINIMO_UNIDADES", "10")))

BRAND_NAME = os.getenv("BRAND_NAME", "Dulcecita")
WEBSITE_URL = os.getenv("WEBSITE_URL", "")
# Logo para los correos (URL absoluta publica; los clientes de email no leen estaticos relativos).
# Usa el PNG (los clientes no soportan SVG). Se puede sobreescribir con EMAIL_LOGO_URL.
EMAIL_LOGO_URL = os.getenv("EMAIL_LOGO_URL") or (
    (WEBSITE_URL or "https://dulcecitaa.onrender.com").rstrip("/") + "/static/img/logo-dulcecita-mascota.jpg"
)
# Botones flotantes de redes
WHATSAPP_URL = os.getenv("WHATSAPP_URL") or "https://wa.me/56961192192"
INSTAGRAM_URL = os.getenv("INSTAGRAM_URL") or "https://instagram.com/dulcecitaa.cl"
SHIPPING_COST = int(os.getenv("SHIPPING_COST", "2500"))
BOX_PRICE = int(os.getenv("BOX_PRICE", "1490"))
# Minimo por linea dentro de "Arma tu box" (en el pedido normal es MINIMO_UNIDADES)
MINIMO_BOX = max(1, int(os.getenv("MINIMO_BOX", "3")))
PICKUP_POINT_LABEL = os.getenv("PICKUP_POINT_LABEL", "Retiro coordinado por WhatsApp")

# Horas entre que se confirma el pago y sale el pedido (todo se hace a mano).
DESPACHO_HORAS = int(os.getenv("DESPACHO_HORAS", "48"))

# Pago por transferencia. Los datos van en el entorno (Render > Environment),
# nunca en el codigo. Mientras TRANSFER_NUMERO este vacio, la web no muestra
# datos: le dice al cliente que se los mandan por WhatsApp.
TRANSFERENCIA = {
    "titular": os.getenv("TRANSFER_TITULAR", ""),
    "rut": os.getenv("TRANSFER_RUT", ""),
    "banco": os.getenv("TRANSFER_BANCO", ""),
    "tipo_cuenta": os.getenv("TRANSFER_TIPO_CUENTA", ""),
    "numero": os.getenv("TRANSFER_NUMERO", ""),
    "email": os.getenv("TRANSFER_EMAIL", ""),
}
BUSINESS_HOURS = os.getenv("BUSINESS_HOURS", "Lunes a sábado de 09:00 a 19:00")
DEFAULT_OG_IMAGE = os.getenv("DEFAULT_OG_IMAGE", "/static/img/sello-dulcecita.jpg")

# --- SEO y medicion -----------------------------------------------------
# Dominio oficial: canonical, sitemap y datos estructurados usan SIEMPRE este,
# aunque la visita llegue por dulcecitaa.onrender.com o con ?utm=. Si no, Google
# ve dos sitios iguales compitiendo entre si.
SITE_URL = (os.getenv("SITE_URL") or "https://dulcecita.cl").rstrip("/")

# IDs de medicion. Vacios = no se carga nada (en local y en tests no se mide).
# Todos se pegan en Render > Environment; ninguno es secreto, pero asi se
# cambian sin tocar codigo.
GA4_ID = os.getenv("GA4_ID", "")                          # G-XXXXXXXXXX (Google Analytics 4)
GTM_ID = os.getenv("GTM_ID", "")                          # GTM-XXXXXXX (opcional, Tag Manager)
CLARITY_ID = os.getenv("CLARITY_ID", "")                  # Microsoft Clarity: mapas de calor y grabaciones
META_PIXEL_ID = os.getenv("META_PIXEL_ID", "")            # Pixel de Meta, para medir anuncios de Instagram
GOOGLE_SITE_VERIFICATION = os.getenv("GOOGLE_SITE_VERIFICATION", "")  # Search Console (metodo etiqueta HTML)
BING_SITE_VERIFICATION = os.getenv("BING_SITE_VERIFICATION", "")      # Bing Webmaster Tools


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
