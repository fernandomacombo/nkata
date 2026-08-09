import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-placeholder-change-in-production")
DEBUG = env_bool("DJANGO_DEBUG", True)
NKATA_FRONTEND_URL = os.getenv("NKATA_FRONTEND_URL", "http://localhost:5173").rstrip("/")

# Em desenvolvimento HTTPS, o Vite termina TLS e encaminha /api e /media para
# o runserver Django. Confiamos apenas no indicador de protocolo enviado por
# esse proxy para que build_absolute_uri gere URLs HTTPS do origin público.
# Em produção fica desligado por padrão e deve ser ativado somente atrás de um
# proxy reverso controlado pela própria infraestrutura NKATA.
NKATA_TRUST_PROXY_HEADERS = env_bool("NKATA_TRUST_PROXY_HEADERS", DEBUG)
if NKATA_TRUST_PROXY_HEADERS:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Pré-moderação de media. O padrão é manual/fail-closed: nenhum conteúdo é
# automaticamente publicado. A moderação de segurança e a inspeção visual são
# ativadas apenas por variáveis de ambiente.
NKATA_MEDIA_MODERATION_PROVIDER = os.getenv(
    "NKATA_MEDIA_MODERATION_PROVIDER",
    "manual",
).strip().lower()
NKATA_OPENAI_MODERATION_MODEL = os.getenv(
    "NKATA_OPENAI_MODERATION_MODEL",
    "omni-moderation-latest",
).strip()
NKATA_MEDIA_MODERATION_TIMEOUT = int(os.getenv("NKATA_MEDIA_MODERATION_TIMEOUT", "20"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
NKATA_MEDIA_VISION_SCAN_ENABLED = env_bool("NKATA_MEDIA_VISION_SCAN_ENABLED", False)
NKATA_MEDIA_VISION_MODEL = os.getenv("NKATA_MEDIA_VISION_MODEL", "gpt-5.6-luna").strip()
NKATA_MEDIA_VISION_MAX_IMAGES = int(os.getenv("NKATA_MEDIA_VISION_MAX_IMAGES", "4"))

# WebRTC. STUN/TURN são configurados no backend para não fixar credenciais
# dentro da bundle React. STUN público ajuda na descoberta de endereço; TURN
# deve ser configurado em produção para servir de relay quando a ligação direta
# falhar em NATs/firewalls mais restritivos.
NKATA_WEBRTC_STUN_URLS = env_list(
    "NKATA_WEBRTC_STUN_URLS",
    "stun:stun.cloudflare.com:3478",
)
NKATA_WEBRTC_TURN_URLS = env_list("NKATA_WEBRTC_TURN_URLS")
NKATA_WEBRTC_TURN_USERNAME = os.getenv("NKATA_WEBRTC_TURN_USERNAME", "").strip()
NKATA_WEBRTC_TURN_CREDENTIAL = os.getenv("NKATA_WEBRTC_TURN_CREDENTIAL", "").strip()

allowed_hosts_env = os.getenv("DJANGO_ALLOWED_HOSTS", "").strip()
if allowed_hosts_env:
    ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_env.split(",") if host.strip()]
elif DEBUG:
    # Facilita testes locais no computador e no telemóvel ligado à mesma rede.
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "entradas",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
PASSWORD_RESET_TIMEOUT = int(os.getenv("DJANGO_PASSWORD_RESET_TIMEOUT", "3600"))

LANGUAGE_CODE = "pt-mz"
TIME_ZONE = "Africa/Maputo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

EMAIL_BACKEND = os.getenv("DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = os.getenv("DJANGO_DEFAULT_FROM_EMAIL", "NKATA <no-reply@nkata.local>")
EMAIL_HOST = os.getenv("DJANGO_EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("DJANGO_EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("DJANGO_EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("DJANGO_EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("DJANGO_EMAIL_USE_TLS", True)
EMAIL_USE_SSL = env_bool("DJANGO_EMAIL_USE_SSL", False)
EMAIL_TIMEOUT = int(os.getenv("DJANGO_EMAIL_TIMEOUT", "15"))

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}

CORS_ALLOW_ALL_ORIGINS = env_bool("CORS_ALLOW_ALL_ORIGINS", DEBUG)
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]

csrf_default_origins = (
    "http://localhost:5173,"
    "http://127.0.0.1:5173,"
    "http://localhost:3000,"
    "http://127.0.0.1:3000"
)
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", csrf_default_origins).split(",")
    if origin.strip()
]

SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", not DEBUG)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", not DEBUG)
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = os.getenv("CSRF_COOKIE_SAMESITE", "Lax")
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", False)
