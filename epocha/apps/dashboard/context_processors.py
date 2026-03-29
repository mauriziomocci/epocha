"""Context processors for the dashboard — available in all templates."""
from django.utils import timezone

from epocha.apps.llm_adapter.models import LLMRequest

# Groq free tier daily limit
DAILY_REQUEST_LIMIT = 14400

# Language configuration
LANGUAGES = {
    "en": {"name": "English", "instruction": "Respond in English."},
    "it": {"name": "Italiano", "instruction": "Rispondi in italiano."},
    "fr": {"name": "Francais", "instruction": "Reponds en francais."},
    "de": {"name": "Deutsch", "instruction": "Antworte auf Deutsch."},
    "es": {"name": "Espanol", "instruction": "Responde en espanol."},
}


def llm_quota(request):
    """Add today's LLM usage stats to every template context."""
    today = timezone.now().date()
    today_count = LLMRequest.objects.filter(
        created_at__date=today,
    ).count()

    # Language preference from session
    current_language = request.session.get("epocha_language", "en")
    language_instruction = LANGUAGES.get(current_language, LANGUAGES["en"])["instruction"]

    return {
        "llm_today_count": today_count,
        "llm_daily_limit": DAILY_REQUEST_LIMIT,
        "llm_remaining": max(0, DAILY_REQUEST_LIMIT - today_count),
        "current_language": current_language,
        "language_instruction": language_instruction,
    }
