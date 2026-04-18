"""Demography app configuration."""
from django.apps import AppConfig


class DemographyConfig(AppConfig):
    """Config for the demography subsystem.

    Scientific foundation: births, aging, reproduction, inheritance,
    migration, and deaths as an emergent agent-level process calibrated
    on historical demographic data. See
    docs/superpowers/specs/2026-04-18-demography-design-it.md.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "epocha.apps.demography"
    label = "demography"
