"""Tests for the template loader contract of amendment A9 (2026-08-07).

The amendment records that the loader accepted, all at once and without
protesting, an invented top-level key, an `era_noize` section with a typo,
an `estate_tax_rate` of 40, a heritability of 5.0 and a negative regression
coefficient -- while whitepaper section 6.2 published the opposite. These
tests are the six clauses of the contract that closes that gap, and each is
written so it fails against the loader as it was.

Success criterion SC-015a requires all six clauses, so each has its own
test: a criterion that covers four of six is how SC-015 came to pass
against an `era_noise` section that was present but empty.
"""

from __future__ import annotations

import copy
import json

import pytest

from epocha.apps.demography.template_loader import (
    list_available_templates,
    load_template,
    validate_template,
)


@pytest.fixture
def template() -> dict:
    """A shipped template, as the loader returns it. Mutated per test."""
    return copy.deepcopy(load_template("industrial"))


class TestShippedTemplatesStayValid:
    """The contract must not reject what the project actually ships.

    This is the first thing a strict schema breaks, and the two traps are
    real: two templates carry a free-text `_note`, and
    `sexual_orientation_distribution` is shipped by all five while the
    pre-amendment required-key set never mentioned it.
    """

    @pytest.mark.parametrize("name", list_available_templates())
    def test_every_shipped_template_loads(self, name):
        assert load_template(name)

    def test_the_optional_note_key_is_accepted(self, template):
        template["_note"] = "free text an author left for the next reader"
        validate_template(template, source="test")


class TestClauseOneUnknownKeys:
    """Clause 1: every unknown key, at any nesting level."""

    def test_rejects_an_unknown_top_level_key(self, template):
        template["invented_key"] = 1.0
        with pytest.raises(ValueError, match="invented_key"):
            validate_template(template, source="test")

    def test_rejects_an_unknown_nested_key(self, template):
        template["mortality"]["invented_nested"] = 1.0
        with pytest.raises(ValueError, match="invented_nested"):
            validate_template(template, source="test")

    def test_rejects_a_typo_in_a_section_name(self, template):
        """The amendment's own example: `era_noize` for `era_noise`."""
        template["trait_inheritance"]["era_noize"] = template["trait_inheritance"].pop("era_noise")
        with pytest.raises(ValueError) as excinfo:
            validate_template(template, source="test")
        assert "era_noize" in str(excinfo.value)

    def test_rejects_a_deeply_nested_unknown_key(self, template):
        template["couple"]["homogamy_weights"]["w_invented"] = 0.1
        with pytest.raises(ValueError, match="w_invented"):
            validate_template(template, source="test")


class TestClauseTwoValueRanges:
    """Clause 2: rates and heritabilities in [0,1], regressions in [0,1],
    amplitudes positive. All three are the amendment's own examples."""

    def test_rejects_an_estate_tax_rate_expressed_in_percentage_points(self, template):
        template["economic_inheritance"]["estate_tax_rate"] = 40
        with pytest.raises(ValueError) as excinfo:
            validate_template(template, source="test")
        message = str(excinfo.value)
        assert "estate_tax_rate" in message
        assert "[0, 1]" in message  # the admitted interval must be named

    def test_rejects_an_out_of_scale_heritability(self, template):
        template["trait_inheritance"]["heritability"]["intelligence"] = 5.0
        with pytest.raises(ValueError, match="intelligence"):
            validate_template(template, source="test")

    def test_rejects_a_negative_regression_coefficient(self, template):
        template["social_inheritance"]["education_regression_rho"] = -0.4
        with pytest.raises(ValueError, match="education_regression_rho"):
            validate_template(template, source="test")

    def test_rejects_a_non_positive_amplitude(self, template):
        template["trait_inheritance"]["era_noise"]["intelligence"]["era_sd"] = 0.0
        with pytest.raises(ValueError, match="era_sd"):
            validate_template(template, source="test")

    def test_accepts_the_interval_endpoints(self, template):
        """[0, 1] is closed for rates: three templates ship a zero tax rate."""
        template["economic_inheritance"]["estate_tax_rate"] = 0.0
        validate_template(template, source="test")
        template["economic_inheritance"]["estate_tax_rate"] = 1.0
        validate_template(template, source="test")


class TestClauseThreeMandatorySections:
    """Clause 3: the two era_noise sections, named by identity not by depth.

    The loader already rejected several absences, three of them nested under
    `mortality`, so nesting is not what discriminates -- the identity of the
    section is.
    """

    def test_rejects_a_missing_trait_era_noise(self, template):
        del template["trait_inheritance"]["era_noise"]
        with pytest.raises(ValueError, match="era_noise"):
            validate_template(template, source="test")

    def test_rejects_a_missing_social_era_noise(self, template):
        del template["social_inheritance"]["era_noise"]
        with pytest.raises(ValueError, match="era_noise"):
            validate_template(template, source="test")

    def test_still_rejects_the_absences_it_already_rejected(self, template):
        del template["mortality"]["heligman_pollard"]
        with pytest.raises(ValueError, match="heligman_pollard"):
            validate_template(template, source="test")


class TestClauseFourMissingEntries:
    """Clause 4: a section present but incomplete is rejected, naming what is
    missing. This is what SC-015 could not catch."""

    def test_rejects_an_empty_trait_era_noise(self, template):
        template["trait_inheritance"]["era_noise"] = {}
        with pytest.raises(ValueError) as excinfo:
            validate_template(template, source="test")
        message = str(excinfo.value)
        assert "era_noise" in message
        # the rejection must name what is absent, not merely that it is empty
        assert "creativity" in message

    def test_rejects_an_empty_heritability(self, template):
        template["trait_inheritance"]["heritability"] = {}
        with pytest.raises(ValueError, match="era_noise"):
            validate_template(template, source="test")

    def test_rejects_a_template_that_transmits_nothing(self, template):
        """Both sections empty is the arrangement the symmetric difference
        cannot see: it is zero, and the admissible-region pass then iterates
        nothing. Emptying only one side is caught by clauses 4 and 6; emptying
        both was accepted whole until this check existed."""
        template["trait_inheritance"]["heritability"] = {}
        template["trait_inheritance"]["era_noise"] = {}
        with pytest.raises(ValueError, match="no transmitted character"):
            validate_template(template, source="test")

    def test_accepts_an_era_that_derives_no_traits(self, template):
        """A9 requires an entry per TRANSMITTED character, and a derived trait
        is not one: an era that derives none is legitimate and must load."""
        template["trait_inheritance"]["derived_trait_formulas"] = {}
        validate_template(template, source="test")

    def test_rejects_a_single_missing_character(self, template):
        del template["trait_inheritance"]["era_noise"]["creativity"]
        with pytest.raises(ValueError, match="creativity"):
            validate_template(template, source="test")

    def test_rejects_a_missing_moment_within_an_entry(self, template):
        del template["trait_inheritance"]["era_noise"]["creativity"]["era_sd"]
        with pytest.raises(ValueError, match="era_sd"):
            validate_template(template, source="test")

    def test_rejects_a_social_era_noise_without_education(self, template):
        del template["social_inheritance"]["era_noise"]["education"]
        with pytest.raises(ValueError, match="education"):
            validate_template(template, source="test")

    def test_rejects_a_social_era_noise_without_the_rank_dispersion(self, template):
        del template["social_inheritance"]["era_noise"]["class_rank"]
        with pytest.raises(ValueError, match="class_rank"):
            validate_template(template, source="test")


class TestClauseFiveAdmissibleRegion:
    """Clause 5: A1's three checks per pair, plus the rank bound."""

    def test_rejects_a_pair_outside_the_admissible_region(self, template):
        """(0.80, 0.15) realizes 92% of its declared amplitude: A1 rejects it."""
        for entry in template["trait_inheritance"]["era_noise"].values():
            entry["era_mean"] = 0.80
        with pytest.raises(ValueError) as excinfo:
            validate_template(template, source="test")
        assert "realized stationary amplitude" in str(excinfo.value)

    def test_rejects_a_mean_on_the_boundary(self, template):
        template["trait_inheritance"]["era_noise"]["creativity"]["era_mean"] = 0.0
        with pytest.raises(ValueError, match="creativity"):
            validate_template(template, source="test")

    def test_rejects_a_rank_dispersion_below_the_unique_root_interval(self, template):
        template["social_inheritance"]["era_noise"]["class_rank"]["target_dispersion"] = 0.5
        with pytest.raises(ValueError, match="target_dispersion"):
            validate_template(template, source="test")

    def test_rejects_a_rank_dispersion_above_the_unique_root_interval(self, template):
        template["social_inheritance"]["era_noise"]["class_rank"]["target_dispersion"] = 1.5
        with pytest.raises(ValueError, match="target_dispersion"):
            validate_template(template, source="test")

    def test_the_rank_dispersion_is_exempt_from_the_pair_checks(self, template):
        """It is not a pair on [0,1]: 1.0 exceeds any amplitude bound there and
        must still be accepted."""
        template["social_inheritance"]["era_noise"]["class_rank"]["target_dispersion"] = 1.0
        validate_template(template, source="test")


class TestClauseSixCrossSectionConsistency:
    """Clause 6: the symmetric difference between heritability and the trait
    era_noise, and that pair of sections only."""

    def test_rejects_a_character_in_era_noise_absent_from_heritability(self, template):
        template["trait_inheritance"]["era_noise"]["invented_trait"] = {
            "era_mean": 0.5,
            "era_sd": 0.15,
        }
        with pytest.raises(ValueError, match="invented_trait"):
            validate_template(template, source="test")

    def test_rejects_a_character_in_heritability_absent_from_era_noise(self, template):
        del template["trait_inheritance"]["era_noise"]["stamina"]
        with pytest.raises(ValueError, match="stamina"):
            validate_template(template, source="test")

    def test_does_not_require_education_to_appear_in_heritability(self, template):
        """The social era_noise declares education and the rank dispersion,
        which by construction have no heritability entry -- their coefficient
        is education_regression_rho. Clause 6 must not reach them."""
        assert "education" not in template["trait_inheritance"]["heritability"]
        validate_template(template, source="test")


class TestTheDefaultSentinelIsGone:
    """A9 orders `heritability["default"]` out of the schema: every declared
    trait carries its own coefficient, so the sentinel was only ever reachable
    through the personality keys the amendment closes out."""

    def test_no_shipped_template_declares_it(self):
        for name in list_available_templates():
            assert "default" not in load_template(name)["trait_inheritance"]["heritability"]

    def test_reintroducing_it_is_rejected(self, template):
        """Matched on the dedicated message, not merely on the word "default".

        Clause 4 also fires here, because a `default` in heritability has no
        era_noise entry, and its message contains the word too -- so a test
        matching only "default" passes with the dedicated check disabled, and
        tells the author to add a noise entry for a sentinel instead of
        removing it.
        """
        template["trait_inheritance"]["heritability"]["default"] = 0.30
        with pytest.raises(ValueError, match="removed from the schema"):
            validate_template(template, source="test")


class TestErrorsNameTheField:
    """A9 requires rejection 'nominando il campo e l'intervallo ammesso'.

    An error that says only that something is wrong sends the author hunting
    through a two-hundred-line JSON file, which is how a typo survives.
    """

    def test_the_message_carries_the_path_not_just_the_leaf(self, template):
        template["couple"]["homogamy_weights"]["w_invented"] = 0.1
        with pytest.raises(ValueError) as excinfo:
            validate_template(template, source="test")
        assert "couple.homogamy_weights" in str(excinfo.value)

    def test_the_message_carries_the_source(self, template):
        template["invented_key"] = 1
        with pytest.raises(ValueError, match="my-template.json"):
            validate_template(template, source="my-template.json")


class TestValidationRunsOnLoad:
    """The contract is worthless if it only fires when called directly."""

    def test_load_template_rejects_a_broken_file(self, tmp_path, monkeypatch):
        from epocha.apps.demography import template_loader

        broken = copy.deepcopy(load_template("industrial"))
        broken["economic_inheritance"]["estate_tax_rate"] = 40
        path = tmp_path / "broken.json"
        path.write_text(json.dumps(broken))
        monkeypatch.setattr(template_loader, "TEMPLATES_DIR", tmp_path)
        with pytest.raises(ValueError, match="estate_tax_rate"):
            template_loader.load_template("broken")


class TestNonConvergenceIsAValueError:
    """`load_template` documents ValueError for any A9 violation.

    The fixed point can also fail to settle, and that raised a RuntimeError
    naming neither the template nor the field, against A9's requirement to
    name the field and A1's to name the pair.
    """

    def test_a_fixed_point_that_does_not_settle_fails_as_a_validation_error(
        self, template, monkeypatch
    ):
        from epocha.apps.demography import truncated_moments

        monkeypatch.setattr(truncated_moments, "MAX_ITERATIONS", 1)
        truncated_moments._solve.cache_clear()
        try:
            with pytest.raises(ValueError) as excinfo:
                validate_template(template, source="my-template.json")
            message = str(excinfo.value)
            assert "my-template.json" in message
            assert "era_noise" in message
            assert "did not settle" in message
        finally:
            truncated_moments._solve.cache_clear()


class TestBoundaryMassIsReported:
    """A1 requires the boundary mass reported at load, naming its branch.

    It is an observable, not a gate -- the amendment deleted the ceiling it
    once had, for want of any source fixing a tolerable value.
    """

    def test_load_reports_amplitude_and_boundary_mass_with_its_branch(self, caplog):
        import logging

        from epocha.apps.demography import template_loader

        template_loader.load_template("industrial")  # warm the fixed-point cache
        with caplog.at_level(logging.INFO, logger=template_loader.__name__):
            template_loader.load_template("industrial")
        messages = [r.getMessage() for r in caplog.records]
        assert any("boundary mass" in m for m in messages)
        assert any(
            branch in m for m in messages for branch in ("two-parent", "single-parent", "no-parent")
        )
