"""Context processors for the dashboard — available in all templates."""
from django.utils import timezone

from epocha.apps.llm_adapter.models import LLMRequest

# Gemini free tier daily limit
DAILY_REQUEST_LIMIT = 1000


def llm_quota(request):
    """Add today's LLM usage stats to every template context."""
    today = timezone.now().date()
    today_count = LLMRequest.objects.filter(
        created_at__date=today,
    ).count()

    return {
        "llm_today_count": today_count,
        "llm_daily_limit": DAILY_REQUEST_LIMIT,
        "llm_remaining": max(0, DAILY_REQUEST_LIMIT - today_count),
    }
