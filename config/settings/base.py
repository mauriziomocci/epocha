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
    "django.contrib.gis",
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
    "epocha.apps.demography",
    "epocha.apps.knowledge",
    "epocha.apps.economy",
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
                "epocha.apps.dashboard.context_processors.llm_quota",
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

# --- Information Flow ---
# Minimum emotional weight for an action to propagate through the social network.
# Actions below this threshold are considered too mundane for gossip.
# Source: threshold aligns with _ACTION_EMOTIONAL_WEIGHT in engine.py where
# socialize=0.2 (excluded) and help=0.3 (included).
EPOCHA_INFO_FLOW_PROPAGATION_THRESHOLD = env.float("EPOCHA_INFO_FLOW_PROPAGATION_THRESHOLD", default=0.3)

# Reliability decay factor per hop in the communication chain.
# Source: Bartlett (1932) serial reproduction experiments show ~30% detail loss per step.
EPOCHA_INFO_FLOW_RELIABILITY_DECAY = env.float("EPOCHA_INFO_FLOW_RELIABILITY_DECAY", default=0.7)

# Maximum hops before information stops propagating.
EPOCHA_INFO_FLOW_MAX_HOPS = env.int("EPOCHA_INFO_FLOW_MAX_HOPS", default=3)

# Belief filter acceptance threshold (0.0-1.0).
EPOCHA_INFO_FLOW_BELIEF_THRESHOLD = env.float("EPOCHA_INFO_FLOW_BELIEF_THRESHOLD", default=0.4)

# Maximum recipients per memory per tick (prevents unbounded fan-out).
EPOCHA_INFO_FLOW_MAX_RECIPIENTS = env.int("EPOCHA_INFO_FLOW_MAX_RECIPIENTS", default=20)

# --- Faction Dynamics ---
# How often faction dynamics run (every N ticks).
EPOCHA_FACTION_DYNAMICS_INTERVAL = env.int("EPOCHA_FACTION_DYNAMICS_INTERVAL", default=5)

# Minimum pairwise affinity for agents to be considered a potential faction cluster.
# Source: calibrated so that agents sharing social class + positive relationship
# (circumstance_score ~0.5, relationship_score ~0.5) cross the threshold.
EPOCHA_FACTION_AFFINITY_THRESHOLD = env.float("EPOCHA_FACTION_AFFINITY_THRESHOLD", default=0.5)

# Minimum members required to form a faction.
EPOCHA_FACTION_MIN_MEMBERS = env.int("EPOCHA_FACTION_MIN_MEMBERS", default=3)

# Maximum members in a newly formed faction (prevents oversized initial groups).
EPOCHA_FACTION_MAX_INITIAL_MEMBERS = env.int("EPOCHA_FACTION_MAX_INITIAL_MEMBERS", default=8)

# Cohesion threshold below which a group dissolves.
EPOCHA_FACTION_DISSOLUTION_THRESHOLD = env.float("EPOCHA_FACTION_DISSOLUTION_THRESHOLD", default=0.2)

# Leadership legitimacy threshold below which the leader is replaced.
EPOCHA_FACTION_LEGITIMACY_THRESHOLD = env.float("EPOCHA_FACTION_LEGITIMACY_THRESHOLD", default=0.3)

# --- Government and Political System ---
# How often the political cycle runs (every N ticks).
EPOCHA_GOVERNMENT_CYCLE_INTERVAL = env.int("EPOCHA_GOVERNMENT_CYCLE_INTERVAL", default=10)

# Default ticks between elections (for government types that hold elections).
EPOCHA_GOVERNMENT_ELECTION_INTERVAL = env.int("EPOCHA_GOVERNMENT_ELECTION_INTERVAL", default=50)

# Gini coefficient threshold above which revolt probability increases.
# Source: Acemoglu & Robinson (2006), most revolutions occur at Gini 0.6-0.8.
EPOCHA_GOVERNMENT_GINI_REVOLT_THRESHOLD = env.float("EPOCHA_GOVERNMENT_GINI_REVOLT_THRESHOLD", default=0.6)

# Government stability threshold below which coups become possible.
EPOCHA_GOVERNMENT_COUP_STABILITY_THRESHOLD = env.float("EPOCHA_GOVERNMENT_COUP_STABILITY_THRESHOLD", default=0.3)

# --- Knowledge Graph ---
# Master switch for the Knowledge Graph feature.
EPOCHA_KG_ENABLED = env.bool("EPOCHA_KG_ENABLED", default=True)

# Maximum number of text chunks produced per uploaded document.
EPOCHA_KG_MAX_CHUNKS_PER_DOC = env.int("EPOCHA_KG_MAX_CHUNKS_PER_DOC", default=50)

# Maximum number of characters accepted from a single uploaded document.
EPOCHA_KG_MAX_DOCUMENT_CHARS = env.int("EPOCHA_KG_MAX_DOCUMENT_CHARS", default=500000)

# Batch size used when computing embeddings for chunks.
EPOCHA_KG_EMBEDDING_BATCH_SIZE = env.int("EPOCHA_KG_EMBEDDING_BATCH_SIZE", default=10)
