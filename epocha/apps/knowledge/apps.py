"""Knowledge Graph Django app."""
from django.apps import AppConfig


class KnowledgeConfig(AppConfig):
    """App configuration for the Knowledge Graph module."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "epocha.apps.knowledge"
    label = "knowledge"
    verbose_name = "Knowledge Graph"
