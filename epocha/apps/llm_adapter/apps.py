from django.apps import AppConfig


class LlmAdapterConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "epocha.apps.llm_adapter"
    verbose_name = "LLM Adapter"
