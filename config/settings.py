import os
import json
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from django.utils.csp import CSP
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


DEBUG = env_bool("DJANGO_DEBUG", True)
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-placeholder-change-in-production")
if not DEBUG and SECRET_KEY == "dev-placeholder-change-in-production":
    raise ImproperlyConfigured("DJANGO_SECRET_KEY é obrigatória em produção.")
NKATA_FRONTEND_URL = os.getenv("NKATA_FRONTEND_URL", "http://localhost:5173").rstrip("/")

# Em desenvolvimento HTTPS, o Vite termina TLS e encaminha /api para
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
NKATA_WEBRTC_TURN_SHARED_SECRET = os.getenv(
    "NKATA_WEBRTC_TURN_SHARED_SECRET",
    "",
).strip()
NKATA_WEBRTC_TURN_CREDENTIAL_TTL = int(
    os.getenv("NKATA_WEBRTC_TURN_CREDENTIAL_TTL", "3600")
)

# Web Push/PWA. As chaves VAPID ficam exclusivamente no ambiente do servidor.
# Sem estas variáveis o centro de notificações continua operacional, mas o
# frontend apresenta o push como ainda não configurado.
NKATA_WEBPUSH_PUBLIC_KEY = os.getenv("NKATA_WEBPUSH_PUBLIC_KEY", "").strip()
NKATA_WEBPUSH_PRIVATE_KEY = os.getenv("NKATA_WEBPUSH_PRIVATE_KEY", "").strip()
NKATA_WEBPUSH_SUBJECT = os.getenv(
    "NKATA_WEBPUSH_SUBJECT",
    "mailto:suporte@nkata.online",
).strip()
NKATA_WEBPUSH_TTL = int(os.getenv("NKATA_WEBPUSH_TTL", "300"))

allowed_hosts_env = os.getenv("DJANGO_ALLOWED_HOSTS", "").strip()
if allowed_hosts_env:
    ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_env.split(",") if host.strip()]
elif DEBUG:
    # Facilita testes locais no computador e no telemóvel ligado à mesma rede.
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = []

if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS é obrigatório em produção.")

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
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "config.middleware.RequestBodySizeLimitMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.csp.ContentSecurityPolicyMiddleware",
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

database_url = os.getenv("DATABASE_URL", "").strip()
if database_url:
    DATABASES = {
        "default": dj_database_url.parse(
            database_url,
            conn_max_age=int(os.getenv("DJANGO_DB_CONN_MAX_AGE", "60")),
            conn_health_checks=True,
            ssl_require=env_bool("DJANGO_DB_SSL_REQUIRED", not DEBUG),
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

redis_url = os.getenv("REDIS_URL", "").strip()
if redis_url:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": redis_url,
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
            "KEY_PREFIX": os.getenv("NKATA_CACHE_KEY_PREFIX", "nkata"),
            "TIMEOUT": 300,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "nkata-local",
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
WHITENOISE_ROOT = BASE_DIR / "frontend" / "dist"
WHITENOISE_MAX_AGE = 31536000 if not DEBUG else 0
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
PRIVATE_MEDIA_ROOT = Path(
    os.getenv("NKATA_PRIVATE_MEDIA_ROOT", str(BASE_DIR / "private_media"))
)
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


def env_json(name: str, default=None):
    raw = os.getenv(name, "").strip()
    if not raw:
        return {} if default is None else default
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ImproperlyConfigured(f"{name} deve conter JSON válido.") from exc
    if not isinstance(value, dict):
        raise ImproperlyConfigured(f"{name} deve conter um objeto JSON.")
    return value


storage_bucket = os.getenv("NKATA_STORAGE_BUCKET", "").strip()
if storage_bucket:
    storage_base_options = {
        "bucket_name": storage_bucket,
        "region_name": os.getenv("NKATA_STORAGE_REGION", "").strip() or None,
        "endpoint_url": os.getenv("NKATA_STORAGE_ENDPOINT_URL", "").strip() or None,
        "access_key": os.getenv("NKATA_STORAGE_ACCESS_KEY", "").strip() or None,
        "secret_key": os.getenv("NKATA_STORAGE_SECRET_KEY", "").strip() or None,
        "default_acl": "private",
        "file_overwrite": False,
        "querystring_auth": True,
        **env_json("NKATA_STORAGE_OPTIONS"),
    }
    storage_base_options = {
        key: value for key, value in storage_base_options.items() if value is not None
    }
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {**storage_base_options, "location": "uploads"},
        },
        "profiles": {
            "BACKEND": "entradas.storage_backends.ProtectedS3Storage",
            "OPTIONS": {**storage_base_options, "location": "profiles"},
        },
        "identity": {
            "BACKEND": "entradas.storage_backends.ProtectedS3Storage",
            "OPTIONS": {**storage_base_options, "location": "identity"},
        },
        "private": {
            "BACKEND": "entradas.storage_backends.ProtectedS3Storage",
            "OPTIONS": {**storage_base_options, "location": "private"},
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {"location": MEDIA_ROOT, "base_url": MEDIA_URL},
        },
        "profiles": {
            "BACKEND": "entradas.storage_backends.ProtectedFileSystemStorage",
            "OPTIONS": {"location": MEDIA_ROOT, "base_url": None},
        },
        "identity": {
            "BACKEND": "entradas.storage_backends.ProtectedFileSystemStorage",
            "OPTIONS": {"location": MEDIA_ROOT, "base_url": None},
        },
        "private": {
            "BACKEND": "entradas.storage_backends.ProtectedFileSystemStorage",
            "OPTIONS": {
                "location": PRIVATE_MEDIA_ROOT,
                "base_url": None,
                # Lê uploads existentes antes da separação da mídia privada.
                # Novos ficheiros continuam a ser guardados em PRIVATE_MEDIA_ROOT.
                "legacy_location": MEDIA_ROOT,
            },
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

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
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("NKATA_THROTTLE_ANON", "120/min"),
        "user": os.getenv("NKATA_THROTTLE_USER", "1200/min"),
        "login": os.getenv("NKATA_THROTTLE_LOGIN", "10/min"),
        "password_reset": os.getenv("NKATA_THROTTLE_PASSWORD_RESET", "5/hour"),
        "access_request": os.getenv("NKATA_THROTTLE_ACCESS_REQUEST", "3/hour"),
        "access_status": os.getenv("NKATA_THROTTLE_ACCESS_STATUS", "30/hour"),
        "token_flow": os.getenv("NKATA_THROTTLE_TOKEN_FLOW", "60/hour"),
    },
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ] + (["rest_framework.renderers.BrowsableAPIRenderer"] if DEBUG else []),
}

CORS_ALLOW_ALL_ORIGINS = env_bool("CORS_ALLOW_ALL_ORIGINS", DEBUG)
CORS_ALLOW_CREDENTIALS = True
if not DEBUG and CORS_ALLOW_ALL_ORIGINS:
    raise ImproperlyConfigured("CORS_ALLOW_ALL_ORIGINS deve ser False em produção.")

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
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = os.getenv("CSRF_COOKIE_SAMESITE", "Lax")
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", not DEBUG)
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "0" if DEBUG else "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", False)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

SECURE_CSP = {
    "default-src": [CSP.SELF],
    "base-uri": [CSP.SELF],
    "connect-src": [CSP.SELF],
    "font-src": [CSP.SELF, "https://fonts.gstatic.com", "data:"],
    "form-action": [CSP.SELF],
    "frame-ancestors": [CSP.NONE],
    "img-src": [CSP.SELF, "data:", "blob:"],
    "media-src": [CSP.SELF, "blob:"],
    "object-src": [CSP.NONE],
    "script-src": [CSP.SELF],
    "style-src": [CSP.SELF, "https://fonts.googleapis.com", CSP.UNSAFE_INLINE],
}

DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv("DJANGO_DATA_UPLOAD_MAX_MEMORY_SIZE", str(2 * 1024 * 1024)))
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv("DJANGO_FILE_UPLOAD_MAX_MEMORY_SIZE", str(2 * 1024 * 1024)))
NKATA_MAX_REQUEST_BODY_SIZE = int(
    os.getenv("NKATA_MAX_REQUEST_BODY_SIZE", str(66 * 1024 * 1024))
)

LOG_LEVEL = os.getenv("DJANGO_LOG_LEVEL", "INFO").upper()
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "entradas": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
}
