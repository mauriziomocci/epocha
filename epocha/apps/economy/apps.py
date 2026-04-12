"""Economy Django app -- neoclassical general equilibrium model.

Implements CES production, Walrasian market clearing, multi-currency,
property ownership, and fiscal policy. Replaces the placeholder economy
in world/economy.py.

Scientific paradigm: neoclassical (Arrow et al. 1961, Walras 1874,
Fisher 1911, Ricardo 1817). See the spec for full references:
docs/superpowers/specs/2026-04-12-economy-base-design.md
"""
from django.apps import AppConfig


class EconomyConfig(AppConfig):
    """App configuration for the Economy module."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "epocha.apps.economy"
    label = "economy"
    verbose_name = "Economy"
