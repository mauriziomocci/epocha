"""Settings shared across all environments."""
import environ

env = environ.Env()

ROOT_DIR = environ.Path(__file__) - 3  # epocha/
APPS_DIR = ROOT_DIR.path("epocha")

# GENERAL
DEBUG = env.bool("DJANGO_DEBUG", False)
TIME_ZONE = "UTC"
LANGUAGE_CODE = "en-us"
USE_I18N = True
USE_TZ = True

# STATIC FILES
STATIC_URL = "/static/"
STATIC_ROOT = str(ROOT_DIR("staticfiles"))

# DATABASES
DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres:///epocha"),
}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# APPS
DJANGO_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "channels",
    "django_celery_beat",
]

LOCAL_APPS = [
    "epocha.apps.users",
    "epocha.apps.simulation",
    "epocha.apps.agents",
    "epocha.apps.world",
    "epocha.apps.chat",
    "epocha.apps.llm_adapter",
    "epocha.apps.dashboard",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# MIDDLEWARE
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

# URLS
ROOT_URLCONF = "config.urls"

# TEMPLATES (minimal, for admin)
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

# AUTH
AUTH_USER_MODEL = "users.User"

# PASSWORDS
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# DRF
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PAGINATION_CLASS": "epocha.common.pagination.StandardPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
}

# CHANNELS
ASGI_APPLICATION = "config.asgi.application"
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [env("REDIS_URL", default="redis://localhost:6379/0")],
        },
    },
}

# CELERY
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# CORS
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:3000"])

# EPOCHA SETTINGS
# Main LLM provider (used for ticks, world generation, reports)
EPOCHA_DEFAULT_LLM_PROVIDER = env("EPOCHA_LLM_PROVIDER", default="openai")
EPOCHA_LLM_API_KEY = env("EPOCHA_LLM_API_KEY", default="")
EPOCHA_LLM_MODEL = env("EPOCHA_LLM_MODEL", default="gpt-4o-mini")
EPOCHA_LLM_BASE_URL = env("EPOCHA_LLM_BASE_URL", default="")

# Chat LLM provider (used for conversations — can be a smarter model)
# Falls back to the main provider if not set.
EPOCHA_CHAT_LLM_API_KEY = env("EPOCHA_CHAT_LLM_API_KEY", default="")
EPOCHA_CHAT_LLM_MODEL = env("EPOCHA_CHAT_LLM_MODEL", default="")
EPOCHA_CHAT_LLM_BASE_URL = env("EPOCHA_CHAT_LLM_BASE_URL", default="")
EPOCHA_MAX_AGENTS_PER_SIMULATION = env.int("EPOCHA_MAX_AGENTS", default=50)
EPOCHA_DEFAULT_TICK_INTERVAL_SECONDS = env.int("EPOCHA_TICK_INTERVAL", default=5)
