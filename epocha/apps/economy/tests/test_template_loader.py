"""Tests for the economy template loader."""

import pytest

from epocha.apps.economy.models import EconomyTemplate
from epocha.apps.economy.template_loader import (
    get_template,
    load_default_templates,
)


@pytest.mark.django_db
class TestLoadDefaultTemplates:
    def test_creates_four_templates(self):
        load_default_templates()
        assert EconomyTemplate.objects.count() == 4

    def test_template_names(self):
        load_default_templates()
        names = set(EconomyTemplate.objects.values_list("name", flat=True))
        assert names == {"pre_industrial", "industrial", "modern", "sci_fi"}

    def test_idempotent(self):
        load_default_templates()
        load_default_templates()
        assert EconomyTemplate.objects.count() == 4

    def test_pre_industrial_has_correct_sigma(self):
        load_default_templates()
        t = EconomyTemplate.objects.get(name="pre_industrial")
        # CES sigma for pre-industrial: 0.5 (Antras 2004)
        assert t.production_config["default_sigma"] == 0.5

    def test_pre_industrial_has_five_goods(self):
        load_default_templates()
        t = EconomyTemplate.objects.get(name="pre_industrial")
        assert len(t.goods_config) == 5

    def test_pre_industrial_has_currency(self):
        load_default_templates()
        t = EconomyTemplate.objects.get(name="pre_industrial")
        assert len(t.currencies_config) >= 1

    def test_modern_has_higher_sigma(self):
        load_default_templates()
        t = EconomyTemplate.objects.get(name="modern")
        assert t.production_config["default_sigma"] > 1.0


@pytest.mark.django_db
class TestGetTemplate:
    def test_get_existing_template(self):
        load_default_templates()
        t = get_template("pre_industrial")
        assert t.name == "pre_industrial"

    def test_get_nonexistent_raises(self):
        load_default_templates()
        with pytest.raises(EconomyTemplate.DoesNotExist):
            get_template("nonexistent")
