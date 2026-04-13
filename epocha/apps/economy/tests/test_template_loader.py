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
class TestBehavioralConfig:
    """Tests for the Spec 2 Part 1 behavioral config in templates."""

    def test_all_templates_have_credit_config(self):
        load_default_templates()
        for name in ("pre_industrial", "industrial", "modern", "sci_fi"):
            t = EconomyTemplate.objects.get(name=name)
            assert "credit_config" in t.config, f"{name} missing credit_config"
            cc = t.config["credit_config"]
            assert "loan_to_value" in cc
            assert "max_rollover" in cc
            assert "default_loan_duration_ticks" in cc

    def test_all_templates_have_banking_config(self):
        load_default_templates()
        for name in ("pre_industrial", "industrial", "modern", "sci_fi"):
            t = EconomyTemplate.objects.get(name=name)
            assert "banking_config" in t.config, f"{name} missing banking_config"
            bc = t.config["banking_config"]
            assert "initial_deposits" in bc
            assert "base_interest_rate" in bc
            assert "reserve_ratio" in bc

    def test_all_templates_have_expectations_config(self):
        load_default_templates()
        for name in ("pre_industrial", "industrial", "modern", "sci_fi"):
            t = EconomyTemplate.objects.get(name=name)
            assert "expectations_config" in t.config, (
                f"{name} missing expectations_config"
            )
            ec = t.config["expectations_config"]
            assert "lambda_base" in ec
            assert "trend_threshold" in ec

    def test_all_templates_have_expropriation_policies(self):
        load_default_templates()
        for name in ("pre_industrial", "industrial", "modern", "sci_fi"):
            t = EconomyTemplate.objects.get(name=name)
            assert "expropriation_policies" in t.config, (
                f"{name} missing expropriation_policies"
            )
            ep = t.config["expropriation_policies"]
            assert ep["democracy"] == "none"
            assert ep["autocracy"] == "elite_seizure"
            assert ep["totalitarian"] == "nationalize_all"

    def test_pre_industrial_credit_values(self):
        load_default_templates()
        t = EconomyTemplate.objects.get(name="pre_industrial")
        assert t.config["credit_config"]["loan_to_value"] == 0.5
        assert t.config["banking_config"]["base_interest_rate"] == 0.08
        assert t.config["banking_config"]["initial_deposits"] == 5000.0

    def test_modern_credit_values(self):
        load_default_templates()
        t = EconomyTemplate.objects.get(name="modern")
        assert t.config["credit_config"]["loan_to_value"] == 0.8
        assert t.config["banking_config"]["base_interest_rate"] == 0.03
        assert t.config["banking_config"]["initial_deposits"] == 100000.0
        assert t.config["banking_config"]["reserve_ratio"] == 0.05

    def test_sci_fi_credit_values(self):
        load_default_templates()
        t = EconomyTemplate.objects.get(name="sci_fi")
        assert t.config["credit_config"]["loan_to_value"] == 0.9
        assert t.config["banking_config"]["reserve_ratio"] == 0.03

    def test_backfill_existing_templates(self):
        """Templates created before Spec 2 Part 1 get behavioral config on reload."""
        # First load creates templates without behavioral config
        EconomyTemplate.objects.create(
            name="pre_industrial",
            description="old",
            era_label="old",
            goods_config=[],
            factors_config=[],
            currencies_config=[],
            production_config={},
            tax_config={},
            properties_config={},
            initial_distribution={},
            config={},
        )
        # Second load should backfill behavioral config
        load_default_templates()
        t = EconomyTemplate.objects.get(name="pre_industrial")
        assert "credit_config" in t.config
        assert "banking_config" in t.config
        assert "expectations_config" in t.config
        assert "expropriation_policies" in t.config


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
