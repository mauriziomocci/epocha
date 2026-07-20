"""Unit tests for demography/inheritance.py.

Covers the polygenic additive inheritance kernel `inherit_trait`:
- two-parent midparent formula with an exact RNG-predicted expected value
- clamping of the raw result into [lo, hi]
- fix I-1 single-parent fallback (child_T = h2 * parent_T + (1 - h2) * noise)

Scientific reference: Falconer, D.S. & Mackay, T.F.C. (1996), Introduction
to Quantitative Genetics (4th ed.), Longman, chapter 8 (polygenic additive
model with environmental noise term).

Also covers `evaluate_derived_formula` (SC-006), the restricted AST-based
evaluator used to compute derived-trait formulas (design spec Sezione 4,
e.g. the `cunning` Machiavellism proxy) without exposing an eval() injection
surface.

Also covers `apply_trait_inheritance` (Plan 3, T008/T009), the birth-pipeline
orchestrator that applies the polygenic pass to every heritable trait (scalar
Agent fields and Agent.personality JSONB entries alike) and then evaluates
`derived_trait_formulas` (e.g. `cunning`) against the freshly inherited
values, per the "Responsibility contract" in the design spec (Sezione 4).

Also covers `apply_social_inheritance` (Plan 3, T012/T013), the social-class
transmission and education-level regression mechanism (design spec Sezione
5): the four `class_rule` branches (patrilineal_rigid -- Goody 1976, Wrigley
1981; clark_regression -- Clark 2014; becker_tomes_elasticity_0.4 -- Solon
1999, Chetty et al. 2014; meritocratic -- speculative sci_fi design choice)
and the education-level regression toward the era mean that runs after
every rule.

Also covers `resolve_heirs` (Plan 3, T016/T017, user story 2 -- estate
succession) and `apply_estate_tax` (Plan 3, T018/T019, user story 2): the
flat estate tax routed to the government treasury before the remainder is
split among the resolved heirs (design spec Sezione 5, "Ereditarietà
economica alla morte"; the modern-democracy 0.40 rate corresponds to
Piketty, T. (2014), "Capital in the Twenty-First Century", tables
14.1-14.2).
"""

from __future__ import annotations

import logging
import random

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent
from epocha.apps.demography.couple import form_couple
from epocha.apps.demography.inheritance import (
    DEFAULT_ERA_MEAN,
    DEFAULT_ERA_MEAN_EDUCATION,
    DEFAULT_ERA_SD,
    apply_estate_tax,
    apply_inheritance_at_birth,
    apply_social_inheritance,
    apply_trait_inheritance,
    evaluate_derived_formula,
    inherit_trait,
    resolve_birth_attributes,
    resolve_heirs,
)
from epocha.apps.demography.rng import get_seeded_rng
from epocha.apps.demography.template_loader import load_template
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import Government, World, Zone


class TestInheritTraitTwoParents:
    """Two known parents: exact midparent + single-draw noise formula."""

    def test_matches_hand_computed_formula_with_seeded_rng(self):
        """h2 * midparent + (1 - h2) * noise, noise = rng.gauss(era_mean, era_sd).

        The expected value is computed independently with an identically
        seeded random.Random so the assertion is exact (mirrors the RNG
        sequence the implementation is expected to draw from), not merely
        plausible.
        """
        mother_val = 0.60
        father_val = 0.40
        h2 = 0.45
        era_mean = 0.50
        era_sd = 0.10

        expected_rng = random.Random(1234)
        expected_noise = expected_rng.gauss(era_mean, era_sd)
        midparent = (mother_val + father_val) / 2
        expected = h2 * midparent + (1 - h2) * expected_noise

        actual_rng = random.Random(1234)
        actual = inherit_trait(mother_val, father_val, h2, era_mean, era_sd, actual_rng)

        assert actual == pytest.approx(expected)

    def test_draws_gauss_exactly_once(self):
        """A single rng.gauss draw is consumed per call.

        Verified indirectly: two identically seeded RNGs, one consumed by
        inherit_trait and one consumed by a single manual gauss draw, must
        be left in the same state (their next draw agrees).
        """
        rng_under_test = random.Random(99)
        rng_reference = random.Random(99)

        inherit_trait(0.5, 0.5, 0.5, 0.5, 0.1, rng_under_test)
        rng_reference.gauss(0.5, 0.1)

        # Both RNGs must now be positioned identically: their next draw matches.
        assert rng_under_test.random() == rng_reference.random()


class TestInheritTraitClamping:
    """Clamp the raw polygenic result into [lo, hi] (default [0.0, 1.0])."""

    def test_clamps_above_hi(self):
        """Parents/h2/era chosen so the raw value exceeds 1.0; result is exactly 1.0."""
        # midparent = 1.0 (both parents at the trait ceiling), h2 = 1.0 removes
        # the noise term entirely and would give exactly 1.0 without help, so
        # push further: use an era_mean above the ceiling to force the raw
        # value above hi even with h2 < 1.
        mother_val = 1.0
        father_val = 1.0
        h2 = 0.5
        era_mean = 5.0  # far above hi=1.0, guarantees raw > 1.0 regardless of noise sign
        era_sd = 0.01

        rng = random.Random(7)
        result = inherit_trait(mother_val, father_val, h2, era_mean, era_sd, rng)

        assert result == 1.0

    def test_clamps_below_lo(self):
        """Parents/h2/era chosen so the raw value drops below 0.0; result is exactly 0.0."""
        mother_val = 0.0
        father_val = 0.0
        h2 = 0.5
        era_mean = -5.0  # far below lo=0.0, guarantees raw < 0.0 regardless of noise sign
        era_sd = 0.01

        rng = random.Random(7)
        result = inherit_trait(mother_val, father_val, h2, era_mean, era_sd, rng)

        assert result == 0.0

    def test_custom_bounds_are_respected(self):
        """Non-default lo/hi clamp the result into the custom range."""
        rng = random.Random(3)
        result = inherit_trait(
            0.5, 0.5, 0.5, era_mean=100.0, era_sd=0.01, rng=rng, lo=-10.0, hi=10.0
        )
        assert result == 10.0


class TestInheritTraitSingleParentFallback:
    """Fix I-1: exactly one known parent halves the genetic signal."""

    def test_mother_only_uses_mother_as_parent_t(self):
        """father_val is None: child_T = h2 * mother_val + (1 - h2) * noise."""
        mother_val = 0.70
        h2 = 0.4
        era_mean = 0.5
        era_sd = 0.1

        expected_rng = random.Random(42)
        expected_noise = expected_rng.gauss(era_mean, era_sd)
        expected = h2 * mother_val + (1 - h2) * expected_noise

        actual_rng = random.Random(42)
        actual = inherit_trait(mother_val, None, h2, era_mean, era_sd, actual_rng)

        assert actual == pytest.approx(expected)

    def test_father_only_uses_father_as_parent_t(self):
        """mother_val is None: child_T = h2 * father_val + (1 - h2) * noise."""
        father_val = 0.30
        h2 = 0.4
        era_mean = 0.5
        era_sd = 0.1

        expected_rng = random.Random(42)
        expected_noise = expected_rng.gauss(era_mean, era_sd)
        expected = h2 * father_val + (1 - h2) * expected_noise

        actual_rng = random.Random(42)
        actual = inherit_trait(None, father_val, h2, era_mean, era_sd, actual_rng)

        assert actual == pytest.approx(expected)

    def test_single_parent_does_not_raise(self):
        """Sanity check: single-parent calls complete without exception."""
        rng = random.Random(0)
        result = inherit_trait(0.5, None, 0.3, 0.5, 0.1, rng)
        assert isinstance(result, float)


class TestEvaluateDerivedFormulaHappyPath:
    """Arithmetic-only formulas resolve against the provided symbol table."""

    def test_matches_hand_computed_cunning_formula(self):
        """The actual `cunning` (Machiavellism proxy) derived-trait formula.

        cunning = 0.4*(1-agreeableness) + 0.3*neuroticism + 0.3*intelligence
        (design spec Sezione 4). Expected value computed independently in
        plain Python arithmetic from the same symbol values passed in.
        """
        symbols = {"agreeableness": 0.2, "neuroticism": 0.7, "intelligence": 0.8}
        expected = (
            0.4 * (1 - symbols["agreeableness"])
            + 0.3 * symbols["neuroticism"]
            + 0.3 * symbols["intelligence"]
        )

        result = evaluate_derived_formula(
            "0.4*(1-agreeableness) + 0.3*neuroticism + 0.3*intelligence", symbols
        )

        assert result == pytest.approx(expected)

    def test_unary_minus_resolves(self):
        """Simple arithmetic with a leading unary minus works."""
        symbols = {"neuroticism": 0.7}
        expected = -symbols["neuroticism"] + 1

        result = evaluate_derived_formula("-neuroticism + 1", symbols)

        assert result == pytest.approx(expected)


class TestEvaluateDerivedFormulaRefusals:
    """Security-critical: the evaluator must refuse anything beyond arithmetic.

    Five distinct refusal categories plus an unresolvable bare name, all of
    which must raise rather than silently degrade or execute arbitrary code.
    """

    def test_refuses_function_call(self):
        """A function call (e.g. abs(...)) is not arithmetic and must raise."""
        with pytest.raises(Exception):
            evaluate_derived_formula("abs(intelligence)", {"intelligence": 0.8})

    def test_refuses_attribute_access(self):
        """Attribute access (e.g. .__class__) is a potential injection vector."""
        with pytest.raises(Exception):
            evaluate_derived_formula("intelligence.__class__", {"intelligence": 0.8})

    def test_refuses_dunder_bare_name(self):
        """A bare dunder name not present in symbols must raise.

        __import__ is not a symbol supplied by any caller, so it is refused
        on the same path as any other unknown name -- there is no special
        casing that would let a dunder name resolve.
        """
        with pytest.raises(Exception):
            evaluate_derived_formula("__import__", {"intelligence": 0.8})

    def test_refuses_subscript(self):
        """Subscript access (e.g. name[0]) is refused."""
        with pytest.raises(Exception):
            evaluate_derived_formula("intelligence[0]", {"intelligence": 0.8})

    def test_refuses_comprehension(self):
        """List/set/dict/generator comprehensions are refused."""
        with pytest.raises(Exception):
            evaluate_derived_formula("[x for x in (1,2)]", {"intelligence": 0.8})

    def test_refuses_unknown_bare_name(self):
        """A bare name absent from the symbol table must raise, not resolve to 0."""
        with pytest.raises(Exception):
            evaluate_derived_formula("unknown_trait", {"intelligence": 0.8})


# ---------------------------------------------------------------------------
# apply_trait_inheritance (Plan 3, T008/T009)
# ---------------------------------------------------------------------------

# Heritability keys in the pre_industrial_christian template (and every other
# era template -- verified identical across all five templates) that map to
# a concrete Agent model FloatField, versus keys with no matching field that
# therefore live inside Agent.personality JSONB. Split verified directly
# against epocha/apps/agents/models.py: Agent has intelligence,
# emotional_intelligence, creativity, strength, stamina, agility, fertility
# as scalar fields, but no field named mental_health_baseline (only the
# unrelated `mental_health`), openness, conscientiousness, extraversion,
# agreeableness, or neuroticism -- those five plus mental_health_baseline
# only exist inside the JSONB personality blob.
SCALAR_HERITABLE_TRAITS = {
    "intelligence",
    "emotional_intelligence",
    "creativity",
    "strength",
    "stamina",
    "agility",
    "fertility",
}
PERSONALITY_HERITABLE_TRAITS = {
    "openness",
    "conscientiousness",
    "extraversion",
    "agreeableness",
    "neuroticism",
    "mental_health_baseline",
}


@pytest.fixture
def sim_with_zone(db):
    """Minimal scaffolding: user, simulation, world, zone (mirrors test_couple.py)."""
    user = User.objects.create_user(
        email="inheritance@epocha.dev",
        username="inheritanceuser",
        password="pass1234",
    )
    sim = Simulation.objects.create(
        name="InheritanceTest",
        seed=2026,
        owner=user,
        current_tick=10,
    )
    world = World.objects.create(simulation=sim, stability_index=0.7)
    zone = Zone.objects.create(
        world=world,
        name="InheritanceZone",
        zone_type="residential",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    return sim, zone


def _make_agent(sim, zone, name, personality=None, **kwargs):
    """Helper: create an Agent with sensible defaults (mirrors test_couple.py)."""
    defaults = dict(
        role="farmer",
        location=Point(50, 50),
        health=1.0,
        wealth=100.0,
        age=30,
        birth_tick=0,
        mood=0.5,
        education_level=0.5,
        social_class="working",
        gender=Agent.Gender.FEMALE,
        personality=personality if personality is not None else {},
    )
    defaults.update(kwargs)
    return Agent.objects.create(simulation=sim, name=name, zone=zone, **defaults)


class TestApplyTraitInheritanceHeritabilityCoverage:
    """Every heritable trait in the template is written to the child."""

    @pytest.mark.django_db
    def test_writes_every_heritability_trait_to_child(self, sim_with_zone):
        """Requirement 1: scalars via getattr, Big Five/mental_health_baseline
        via child.personality, for every key in heritability except "default".
        """
        sim, zone = sim_with_zone
        template = load_template("pre_industrial_christian")
        heritability = template["trait_inheritance"]["heritability"]
        trait_names = set(heritability) - {"default"}

        # Self-check: the two hand-verified splits above must exactly cover
        # every heritability key, or this test is silently under-testing.
        assert trait_names == SCALAR_HERITABLE_TRAITS | PERSONALITY_HERITABLE_TRAITS

        mother_personality = {name: 0.65 for name in PERSONALITY_HERITABLE_TRAITS}
        father_personality = {name: 0.35 for name in PERSONALITY_HERITABLE_TRAITS}
        mother = _make_agent(
            sim,
            zone,
            "Mother",
            personality=mother_personality,
            **{name: 0.65 for name in SCALAR_HERITABLE_TRAITS},
        )
        father = _make_agent(
            sim,
            zone,
            "Father",
            personality=father_personality,
            **{name: 0.35 for name in SCALAR_HERITABLE_TRAITS},
        )
        child = _make_agent(sim, zone, "Child")

        rng = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        apply_trait_inheritance(child, mother, father, template, rng)

        for name in SCALAR_HERITABLE_TRAITS:
            value = getattr(child, name)
            assert isinstance(value, float), f"{name} was not written as a scalar float"
            assert 0.0 <= value <= 1.0, f"{name}={value} outside [0, 1]"

        for name in PERSONALITY_HERITABLE_TRAITS:
            assert name in child.personality, f"{name} missing from child.personality"
            value = child.personality[name]
            assert isinstance(value, float), f"{name} was not written as a float"
            assert 0.0 <= value <= 1.0, f"{name}={value} outside [0, 1]"


class TestApplyTraitInheritanceDefaultHeritability:
    """Personality traits absent from the heritability table use default h2=0.30."""

    @pytest.mark.django_db
    def test_unpublished_personality_trait_uses_default_h2(self, sim_with_zone):
        """Requirement 2: humor_style (not in heritability) is inherited with
        default_h2 = heritability["default"] = 0.30, using the documented
        DEFAULT_ERA_MEAN / DEFAULT_ERA_SD noise prior since no era template
        carries a per-trait noise spec (verified: none of the five era
        templates declare era_mean/era_sd under trait_inheritance).

        A minimal synthetic template isolates humor_style as the only
        heritable trait, so the RNG draw sequence is unambiguous and the
        expected value can be hand-computed exactly against a rng cloned
        from the same seed/tick/phase (mirrors the exact-match style of
        TestInheritTraitTwoParents above).
        """
        sim, zone = sim_with_zone
        synthetic_template = {
            "trait_inheritance": {
                "heritability": {"default": 0.30},
                "derived_trait_formulas": {},
            }
        }
        mother_val = 0.8
        father_val = 0.2
        mother = _make_agent(sim, zone, "Mother", personality={"humor_style": mother_val})
        father = _make_agent(sim, zone, "Father", personality={"humor_style": father_val})
        child = _make_agent(sim, zone, "Child")

        expected_rng = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        expected = inherit_trait(
            mother_val, father_val, 0.30, DEFAULT_ERA_MEAN, DEFAULT_ERA_SD, expected_rng
        )

        actual_rng = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        apply_trait_inheritance(child, mother, father, synthetic_template, actual_rng)

        assert "humor_style" in child.personality
        assert child.personality["humor_style"] == pytest.approx(expected)


class TestApplyTraitInheritanceDerivedTrait:
    """cunning is computed at birth from the derived formula, not inherited."""

    @pytest.mark.django_db
    def test_cunning_matches_derived_formula_over_inherited_traits(self, sim_with_zone):
        """Requirement 3: cunning must equal evaluate_derived_formula applied
        to the child's own freshly-inherited traits -- not a polygenic draw
        of its own. Parents' `cunning` scalar field is set far from the
        expected derived value (0.95) so a regression that mistakenly
        inherits cunning biologically would be caught by the mismatch.
        """
        sim, zone = sim_with_zone
        template = load_template("pre_industrial_christian")
        heritability = template["trait_inheritance"]["heritability"]
        formula_spec = template["trait_inheritance"]["derived_trait_formulas"]["cunning"]

        mother_personality = {name: 0.65 for name in PERSONALITY_HERITABLE_TRAITS}
        father_personality = {name: 0.35 for name in PERSONALITY_HERITABLE_TRAITS}
        mother = _make_agent(
            sim,
            zone,
            "Mother",
            personality=mother_personality,
            cunning=0.95,
            **{name: 0.65 for name in SCALAR_HERITABLE_TRAITS},
        )
        father = _make_agent(
            sim,
            zone,
            "Father",
            personality=father_personality,
            cunning=0.95,
            **{name: 0.35 for name in SCALAR_HERITABLE_TRAITS},
        )
        child = _make_agent(sim, zone, "Child")

        rng = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        apply_trait_inheritance(child, mother, father, template, rng)

        symbols = {name: getattr(child, name) for name in SCALAR_HERITABLE_TRAITS}
        symbols.update({name: child.personality[name] for name in PERSONALITY_HERITABLE_TRAITS})
        lo, hi = formula_spec["range"]
        expected_cunning = max(
            lo, min(hi, evaluate_derived_formula(formula_spec["formula"], symbols))
        )

        assert child.cunning == pytest.approx(expected_cunning)
        assert not (heritability.get("cunning"))  # cunning has no published h2 entry


# ---------------------------------------------------------------------------
# resolve_birth_attributes (Plan 3, T010/T011)
# ---------------------------------------------------------------------------
#
# Pure function -- no ORM, no persistence -- so none of these tests use
# @pytest.mark.django_db. `load_template` reads a JSON fixture from disk,
# which needs no database.


def _expected_gender_and_orientation(template: dict, rng: random.Random) -> tuple[str, str]:
    """Independently replay the two documented rng draws against `rng`.

    Mirrors the draw order and selection rule specified for
    `resolve_birth_attributes`: gender first from a single `rng.random()`
    compared against p_male = sex_ratio / (1 + sex_ratio), then orientation
    from a second `rng.random()` walked cumulatively over
    `sexual_orientation_distribution` in the dict's own insertion order,
    falling back to the last key if the cumulative sum falls fractionally
    short of the draw.
    """
    sex_ratio = template["sex_ratio_at_birth"]
    p_male = sex_ratio / (1.0 + sex_ratio)
    gender_draw = rng.random()
    gender = "male" if gender_draw < p_male else "female"

    distribution = template["sexual_orientation_distribution"]
    orientation_draw = rng.random()
    cumulative = 0.0
    orientation = None
    for key, probability in distribution.items():
        cumulative += probability
        if orientation_draw < cumulative:
            orientation = key
            break
    if orientation is None:
        orientation = list(distribution.keys())[-1]

    return gender, orientation


class TestResolveBirthAttributesExactness:
    """Exact RNG-predicted (gender, orientation) pair for a seeded rng."""

    def test_matches_hand_replayed_two_draw_sequence(self):
        """The two draws (gender then orientation) are replayed independently
        against an identically-seeded random.Random and the documented
        selection rules, mirroring the exact-match style used for
        `inherit_trait` above.
        """
        template = load_template("pre_industrial_christian")

        expected_rng = random.Random(2026)
        expected = _expected_gender_and_orientation(template, expected_rng)

        actual_rng = random.Random(2026)
        actual = resolve_birth_attributes(template, actual_rng)

        assert actual == expected

    def test_matches_hand_replayed_two_draw_sequence_different_seed(self):
        """Same replay, a different seed, so the exactness check is not an
        artifact of one lucky seed value.
        """
        template = load_template("pre_industrial_christian")

        expected_rng = random.Random(777)
        expected = _expected_gender_and_orientation(template, expected_rng)

        actual_rng = random.Random(777)
        actual = resolve_birth_attributes(template, actual_rng)

        assert actual == expected


class TestResolveBirthAttributesValidDomain:
    """Over many seeds, the return values stay within their valid domains."""

    def test_gender_and_orientation_always_in_domain(self):
        template = load_template("pre_industrial_christian")
        valid_orientations = set(template["sexual_orientation_distribution"].keys())

        for seed in range(200):
            gender, orientation = resolve_birth_attributes(template, random.Random(seed))
            assert gender in {"male", "female"}
            assert orientation in valid_orientations


class TestResolveBirthAttributesSexRatioDirection:
    """The sex_ratio_at_birth parameter steers the gender draw as expected."""

    def test_high_sex_ratio_yields_mostly_male(self):
        """sex_ratio_at_birth = 99.0 -> p_male = 99/100 = 0.99: an overwhelming
        majority of "male" over a seeded batch. A strong-majority assertion
        keeps the test robust to which exact seeds land on the female side.
        """
        template = {
            "sex_ratio_at_birth": 99.0,
            "sexual_orientation_distribution": {"heterosexual": 1.0},
        }
        male_count = sum(
            1
            for seed in range(300)
            if resolve_birth_attributes(template, random.Random(seed))[0] == "male"
        )
        assert male_count > 270  # 90% of 300, well below the ~99% expectation

    def test_low_sex_ratio_yields_mostly_female(self):
        """sex_ratio_at_birth = 0.01 -> p_male = 0.01/1.01 ~= 0.0099: an
        overwhelming majority of "female" over a seeded batch.
        """
        template = {
            "sex_ratio_at_birth": 0.01,
            "sexual_orientation_distribution": {"heterosexual": 1.0},
        }
        female_count = sum(
            1
            for seed in range(300)
            if resolve_birth_attributes(template, random.Random(seed))[0] == "female"
        )
        assert female_count > 270  # 90% of 300, well below the ~99% expectation


class TestResolveBirthAttributesBucketCorrectness:
    """A degenerate distribution deterministically selects the non-zero bucket."""

    def test_zero_probability_bucket_is_never_selected(self):
        """{"heterosexual": 0.0, "homosexual": 1.0} returns "homosexual" on
        every draw: the cumulative sum after "heterosexual" stays at 0.0, so
        `draw < cumulative` never selects it (rng.random() draws are >= 0.0),
        and the cumulative sum after "homosexual" reaches 1.0, which every
        draw in [0.0, 1.0) satisfies.
        """
        template = {
            "sex_ratio_at_birth": 1.05,
            "sexual_orientation_distribution": {"heterosexual": 0.0, "homosexual": 1.0},
        }
        for seed in range(100):
            _, orientation = resolve_birth_attributes(template, random.Random(seed))
            assert orientation == "homosexual"


# ---------------------------------------------------------------------------
# apply_social_inheritance (Plan 3, T012/T013)
# ---------------------------------------------------------------------------
#
# Social-class transmission and education-level regression at birth (design
# spec Sezione 5, docs/superpowers/specs/2026-04-18-demography-design-it.md).
# Reuses the sim_with_zone fixture / _make_agent helper defined above for
# apply_trait_inheritance.

# Hand-maintained rank ladder mirroring
# epocha.apps.world.stratification._CLASS_RANK, extended with "enslaved" one
# rank below "poor". Kept independent of the implementation's own copy (the
# file's established exact-match testing style) so a test failure cannot be
# masked by trusting a constant the implementation might get wrong.
# Agent.social_class's help_text (epocha/apps/agents/models.py) lists
# "enslaved" as a valid value, but the stratification module (wealth-
# percentile class assignment) never assigns it -- it is only ever
# reachable through social inheritance (patrilineal_rigid transmission from
# an already-enslaved father in a pre-industrial template).
_TEST_CLASS_RANK = {
    "elite": 0,
    "wealthy": 1,
    "middle": 2,
    "working": 3,
    "poor": 4,
    "enslaved": 5,
}
_TEST_VALID_CLASS_LABELS = set(_TEST_CLASS_RANK)


class TestApplySocialInheritancePatrilinealRigid:
    """class_rule = "patrilineal_rigid": verbatim copy of the father's class
    (Goody 1976; Wrigley 1981).
    """

    @pytest.mark.django_db
    def test_child_copies_fathers_class_exactly(self, sim_with_zone):
        sim, zone = sim_with_zone
        template = {
            "social_inheritance": {
                "class_rule": "patrilineal_rigid",
                "education_regression_rho": 0.5,
            }
        }
        mother = _make_agent(sim, zone, "Mother", social_class="middle", education_level=0.5)
        father = _make_agent(sim, zone, "Father", social_class="wealthy", education_level=0.6)
        child = _make_agent(sim, zone, "Child")

        rng = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        apply_social_inheritance(child, mother, father, template, zone_class_mean=2.0, rng=rng)

        assert child.social_class == "wealthy"

    @pytest.mark.django_db
    def test_enslaved_status_transmits_from_father(self, sim_with_zone):
        """A pure string copy transmits "enslaved" exactly like any other
        label -- the whole reason the extended rank ladder (_TEST_CLASS_RANK
        above, and its implementation counterpart per decision A) exists.
        """
        sim, zone = sim_with_zone
        template = {
            "social_inheritance": {
                "class_rule": "patrilineal_rigid",
                "education_regression_rho": 0.5,
            }
        }
        mother = _make_agent(sim, zone, "Mother", social_class="poor", education_level=0.2)
        father = _make_agent(sim, zone, "Father", social_class="enslaved", education_level=0.1)
        child = _make_agent(sim, zone, "Child")

        rng = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        apply_social_inheritance(child, mother, father, template, zone_class_mean=4.0, rng=rng)

        assert child.social_class == "enslaved"


class TestApplySocialInheritanceClarkRegression:
    """class_rule = "clark_regression": 70% father's rank / 30% regression
    toward the zone's mean class rank (Clark, G. (2014), "The Son Also
    Rises").
    """

    @pytest.mark.django_db
    def test_child_regresses_toward_zone_mean_between_father_and_mean(self, sim_with_zone):
        """A high-class father ("elite", rank 0) in a low-class zone
        (zone_class_mean = 4.0, the "poor" rank) must land the child
        strictly between the two ranks -- neither a plain copy of the
        father's class nor a jump straight to the zone mean. The 70/30
        weighting (child_rank = 0.7*0 + 0.3*4.0 = 1.2) makes this hold for
        any reasonable nearest-label rounding rule (floor, round, or ceil
        all land inside (0, 4.0)), so the assertion does not depend on the
        exact rounding tie-break the implementation chooses.
        """
        sim, zone = sim_with_zone
        template = {
            "social_inheritance": {
                "class_rule": "clark_regression",
                "education_regression_rho": 0.4,
            }
        }
        mother = _make_agent(sim, zone, "Mother", social_class="elite", education_level=0.9)
        father = _make_agent(sim, zone, "Father", social_class="elite", education_level=0.9)
        child = _make_agent(sim, zone, "Child")

        rng = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        apply_social_inheritance(child, mother, father, template, zone_class_mean=4.0, rng=rng)

        assert child.social_class in _TEST_VALID_CLASS_LABELS
        child_rank = _TEST_CLASS_RANK[child.social_class]
        assert 0 < child_rank < 4.0


class TestApplySocialInheritanceBeckerTomes:
    """class_rule = "becker_tomes_elasticity_0.4": intergenerational income
    elasticity 0.4 (Solon 1999; Chetty et al. 2014), sampled rather than
    deterministic.
    """

    @pytest.mark.django_db
    def test_outcome_varies_across_seeds_and_stays_in_valid_label_set(self, sim_with_zone):
        """A batch of independent seeds must NOT all resolve to the same
        label as a deterministic copy would -- the rule samples a
        perturbation around the shifted mean -- and every result must stay
        inside the six valid social_class labels.
        """
        sim, zone = sim_with_zone
        template = {
            "social_inheritance": {
                "class_rule": "becker_tomes_elasticity_0.4",
                "education_regression_rho": 0.4,
            }
        }
        mother = _make_agent(sim, zone, "Mother", social_class="elite", education_level=0.9)
        father = _make_agent(sim, zone, "Father", social_class="elite", education_level=0.9)

        results = set()
        for seed in range(40):
            child = _make_agent(sim, zone, f"BeckerChild{seed}")
            rng = random.Random(seed)
            apply_social_inheritance(child, mother, father, template, zone_class_mean=3.0, rng=rng)
            results.add(child.social_class)

        assert results <= _TEST_VALID_CLASS_LABELS
        assert len(results) > 1, "expected sampling variability, got a deterministic copy"


class TestApplySocialInheritanceMeritocratic:
    """class_rule = "meritocratic": 20% inherited, 80% merit-based
    reassignment from the child's own intelligence/education_level
    (speculative sci_fi design choice, design spec Sezione 5 -- no
    citation).
    """

    @pytest.mark.django_db
    def test_higher_merit_yields_a_numerically_lower_better_rank(self, sim_with_zone):
        """Two children of the same parents/zone, differing only in their
        already-inherited intelligence/education_level, must resolve to a
        strictly better (lower) rank for the high-merit child than for the
        low-merit child. Deterministic -- meritocratic consumes no rng
        draws -- so the comparison holds exactly, not just on average.
        """
        sim, zone = sim_with_zone
        template = {
            "social_inheritance": {
                "class_rule": "meritocratic",
                "education_regression_rho": 0.25,
            }
        }
        mother = _make_agent(sim, zone, "Mother", social_class="middle", education_level=0.5)
        father = _make_agent(sim, zone, "Father", social_class="middle", education_level=0.5)

        high_merit_child = _make_agent(
            sim, zone, "HighMeritChild", intelligence=0.95, education_level=0.95
        )
        low_merit_child = _make_agent(
            sim, zone, "LowMeritChild", intelligence=0.05, education_level=0.05
        )

        rng_high = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        apply_social_inheritance(
            high_merit_child, mother, father, template, zone_class_mean=2.0, rng=rng_high
        )
        rng_low = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        apply_social_inheritance(
            low_merit_child, mother, father, template, zone_class_mean=2.0, rng=rng_low
        )

        high_rank = _TEST_CLASS_RANK[high_merit_child.social_class]
        low_rank = _TEST_CLASS_RANK[low_merit_child.social_class]
        assert high_rank < low_rank


class TestApplySocialInheritanceEducationRegression:
    """child.education_level = rho*(mother.education_level +
    father.education_level)/2 + (1-rho)*era_mean_education, clamped to
    [0.0, 1.0]. Runs identically after every class_rule (design spec
    Sezione 5). TRAP 1 guard: the field under test is `education_level`,
    never `education` -- Agent has no such attribute.
    """

    @pytest.mark.django_db
    def test_matches_hand_computed_formula_with_known_rho(self, sim_with_zone):
        sim, zone = sim_with_zone
        rho = 0.6
        mother_edu = 0.8
        father_edu = 0.4
        template = {
            "social_inheritance": {
                "class_rule": "patrilineal_rigid",
                "education_regression_rho": rho,
            }
        }
        mother = _make_agent(sim, zone, "Mother", social_class="middle", education_level=mother_edu)
        father = _make_agent(sim, zone, "Father", social_class="middle", education_level=father_edu)
        child = _make_agent(sim, zone, "Child")

        expected = rho * (mother_edu + father_edu) / 2.0 + (1.0 - rho) * DEFAULT_ERA_MEAN_EDUCATION

        rng = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        apply_social_inheritance(child, mother, father, template, zone_class_mean=2.0, rng=rng)

        assert not hasattr(child, "education")  # TRAP 1: no such field on Agent
        assert child.education_level == pytest.approx(expected)

    @pytest.mark.django_db
    def test_result_is_clamped_into_zero_one(self, sim_with_zone):
        """rho = 0.0 isolates the era-mean term: an out-of-range
        era_mean_education (only reachable via a template override -- the
        Agent.education_level field itself is not range-restricted at the
        DB level either, so this also guards against a future caller
        passing an out-of-range value) must still clamp the final
        education_level into [0.0, 1.0].
        """
        sim, zone = sim_with_zone
        mother = _make_agent(sim, zone, "Mother", social_class="middle", education_level=0.5)
        father = _make_agent(sim, zone, "Father", social_class="middle", education_level=0.5)

        template_high = {
            "social_inheritance": {
                "class_rule": "patrilineal_rigid",
                "education_regression_rho": 0.0,
                "era_mean_education": 2.0,
            }
        }
        child_high = _make_agent(sim, zone, "ChildHighEdu")
        rng_high = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        apply_social_inheritance(
            child_high, mother, father, template_high, zone_class_mean=2.0, rng=rng_high
        )
        assert child_high.education_level == 1.0

        template_low = {
            "social_inheritance": {
                "class_rule": "patrilineal_rigid",
                "education_regression_rho": 0.0,
                "era_mean_education": -1.0,
            }
        }
        child_low = _make_agent(sim, zone, "ChildLowEdu")
        rng_low = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        apply_social_inheritance(
            child_low, mother, father, template_low, zone_class_mean=2.0, rng=rng_low
        )
        assert child_low.education_level == 0.0

    @pytest.mark.django_db
    def test_single_parent_fallback_uses_that_parents_value_alone(self, sim_with_zone):
        """Consistent with fix I-1 in `inherit_trait`: when only the mother
        is known, the midparent term degrades to her value alone.
        """
        sim, zone = sim_with_zone
        rho = 0.5
        mother_edu = 0.9
        template = {
            "social_inheritance": {
                "class_rule": "patrilineal_rigid",
                "education_regression_rho": rho,
            }
        }
        mother = _make_agent(sim, zone, "Mother", social_class="middle", education_level=mother_edu)
        child = _make_agent(sim, zone, "Child")

        expected = rho * mother_edu + (1.0 - rho) * DEFAULT_ERA_MEAN_EDUCATION

        rng = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        apply_social_inheritance(child, mother, None, template, zone_class_mean=2.0, rng=rng)

        assert child.education_level == pytest.approx(expected)


class TestApplySocialInheritanceUnknownClassRule:
    """Decision A/contract: an unrecognized class_rule must never raise."""

    @pytest.mark.django_db
    def test_unknown_class_rule_falls_back_to_patrilineal_rigid_with_warning(
        self, sim_with_zone, caplog
    ):
        sim, zone = sim_with_zone
        template = {
            "social_inheritance": {
                "class_rule": "not_a_real_rule",
                "education_regression_rho": 0.5,
            }
        }
        mother = _make_agent(sim, zone, "Mother", social_class="middle", education_level=0.5)
        father = _make_agent(sim, zone, "Father", social_class="wealthy", education_level=0.5)
        child = _make_agent(sim, zone, "Child")

        rng = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        with caplog.at_level(logging.WARNING):
            apply_social_inheritance(child, mother, father, template, zone_class_mean=2.0, rng=rng)

        assert child.social_class == "wealthy"
        assert any("not_a_real_rule" in message for message in caplog.messages)


class TestApplySocialInheritanceUnknownClassValue:
    """Decision A: an unrecognized social_class value is treated as the
    "working" rank rather than raising during rank arithmetic.
    """

    @pytest.mark.django_db
    def test_unknown_father_class_value_falls_back_to_working_rank(self, sim_with_zone):
        sim, zone = sim_with_zone
        template = {
            "social_inheritance": {
                "class_rule": "clark_regression",
                "education_regression_rho": 0.4,
            }
        }
        mother = _make_agent(sim, zone, "Mother", social_class="middle", education_level=0.5)
        father = _make_agent(
            sim, zone, "Father", social_class="not_a_real_class", education_level=0.5
        )
        child = _make_agent(sim, zone, "Child")

        rng = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        # "working" rank fallback (3): 0.7*3 + 0.3*2.0 = 2.7 -> rounds to 3.
        apply_social_inheritance(child, mother, father, template, zone_class_mean=2.0, rng=rng)

        assert child.social_class == "working"


# ---------------------------------------------------------------------------
# apply_inheritance_at_birth (Plan 3, T014/T015)
# ---------------------------------------------------------------------------
#
# The single birth-pipeline entry point wiring apply_trait_inheritance,
# resolve_birth_attributes, and apply_social_inheritance behind ONE
# deterministic RNG stream (design spec Sezione 4/5, "Responsibility
# contract"). Reuses sim_with_zone / _make_agent from above, plus
# SCALAR_HERITABLE_TRAITS / PERSONALITY_HERITABLE_TRAITS /
# _TEST_CLASS_RANK / _TEST_VALID_CLASS_LABELS already defined for the
# lower-level orchestrators.


class TestApplyInheritanceAtBirthEndToEnd:
    """A single call populates every inherited attribute on the child.

    Uses the real "pre_industrial_christian" template (the simulation.config
    default), exercising the full production template-resolution path
    rather than a synthetic dict.
    """

    @pytest.mark.django_db
    def test_populates_every_inherited_attribute_and_wealth_and_zone(self, sim_with_zone):
        sim, zone = sim_with_zone
        mother_personality = {name: 0.65 for name in PERSONALITY_HERITABLE_TRAITS}
        father_personality = {name: 0.35 for name in PERSONALITY_HERITABLE_TRAITS}
        mother = _make_agent(
            sim,
            zone,
            "Mother",
            personality=mother_personality,
            social_class="wealthy",
            education_level=0.6,
            **{name: 0.65 for name in SCALAR_HERITABLE_TRAITS},
        )
        father = _make_agent(
            sim,
            zone,
            "Father",
            personality=father_personality,
            social_class="middle",
            education_level=0.4,
            **{name: 0.35 for name in SCALAR_HERITABLE_TRAITS},
        )
        child = _make_agent(sim, zone, "Child")

        apply_inheritance_at_birth(child, mother, father, sim, sim.current_tick)

        for name in SCALAR_HERITABLE_TRAITS:
            value = getattr(child, name)
            assert isinstance(value, float), f"{name} was not written as a scalar float"
            assert 0.0 <= value <= 1.0, f"{name}={value} outside [0, 1]"

        for name in PERSONALITY_HERITABLE_TRAITS:
            assert name in child.personality, f"{name} missing from child.personality"
            value = child.personality[name]
            assert isinstance(value, float), f"{name} was not written as a float"
            assert 0.0 <= value <= 1.0, f"{name}={value} outside [0, 1]"

        assert child.gender in {"male", "female"}
        assert child.sexual_orientation in {"heterosexual", "bisexual", "homosexual"}
        assert child.social_class in _TEST_VALID_CLASS_LABELS
        assert 0.0 <= child.education_level <= 1.0
        assert child.wealth == 0.0
        assert child.zone == mother.zone


class TestApplyInheritanceAtBirthDeterminism:
    """SC-003: identical simulation seed and tick reproduce an identical
    child state bit for bit -- proof that the fixed step order feeds all
    three inheritance mechanisms from a single continuous RNG stream.
    """

    @pytest.mark.django_db
    def test_same_seed_and_tick_yields_identical_child_state(self, sim_with_zone):
        sim, zone = sim_with_zone
        mother = _make_agent(
            sim,
            zone,
            "Mother",
            social_class="wealthy",
            education_level=0.6,
            personality={name: 0.6 for name in PERSONALITY_HERITABLE_TRAITS},
            **{name: 0.6 for name in SCALAR_HERITABLE_TRAITS},
        )
        father = _make_agent(
            sim,
            zone,
            "Father",
            social_class="middle",
            education_level=0.4,
            personality={name: 0.4 for name in PERSONALITY_HERITABLE_TRAITS},
            **{name: 0.4 for name in SCALAR_HERITABLE_TRAITS},
        )
        child_a = _make_agent(sim, zone, "ChildA")
        child_b = _make_agent(sim, zone, "ChildB")

        apply_inheritance_at_birth(child_a, mother, father, sim, sim.current_tick)
        apply_inheritance_at_birth(child_b, mother, father, sim, sim.current_tick)

        for name in SCALAR_HERITABLE_TRAITS:
            assert getattr(child_a, name) == getattr(child_b, name), name
        for name in PERSONALITY_HERITABLE_TRAITS:
            assert child_a.personality[name] == child_b.personality[name], name
        assert child_a.gender == child_b.gender
        assert child_a.sexual_orientation == child_b.sexual_orientation
        assert child_a.social_class == child_b.social_class
        assert child_a.education_level == child_b.education_level
        assert child_a.wealth == child_b.wealth == 0.0
        assert child_a.zone == child_b.zone == mother.zone


class TestApplyInheritanceAtBirthEmptyZoneGuard:
    """A zone with zero living agents does not raise, and the zone-mean
    fallback rank is actually threaded through to a verifiable outcome.

    Uses the "industrial" template (class_rule = clark_regression,
    deterministic -- no rng draw), so the child's exact social_class can be
    hand-computed from the documented fallback rank
    (_UNKNOWN_CLASS_FALLBACK_RANK, the "working" rank = 3) rather than only
    asserting "no exception raised".
    """

    @pytest.mark.django_db
    def test_empty_zone_falls_back_to_working_rank_mean(self, sim_with_zone):
        sim, populated_zone = sim_with_zone
        empty_zone = Zone.objects.create(
            world=populated_zone.world,
            name="EmptyZone",
            zone_type="residential",
            boundary=Polygon.from_bbox((200, 200, 300, 300)),
            center=Point(250, 250),
        )
        sim.config = {"demography_template": "industrial"}

        mother = _make_agent(
            sim,
            populated_zone,
            "Mother",
            social_class="middle",
            personality={name: 0.5 for name in PERSONALITY_HERITABLE_TRAITS},
        )
        father = _make_agent(
            sim,
            populated_zone,
            "Father",
            social_class="middle",
            personality={name: 0.5 for name in PERSONALITY_HERITABLE_TRAITS},
        )
        # Reassign in memory only, never saved: the query the function runs
        # is Agent.objects.filter(zone=mother.zone, is_alive=True), so this
        # is sufficient to make that query return zero rows without
        # depending on the mother's own persisted row being agent-free.
        mother.zone = empty_zone
        child = _make_agent(sim, populated_zone, "Child")

        apply_inheritance_at_birth(child, mother, father, sim, sim.current_tick)

        # clark_regression: child_rank = 0.7*parent_rank + 0.3*zone_class_mean.
        # father.social_class = "middle" -> parent_rank = 2. Empty-zone
        # fallback -> zone_class_mean = 3.0 ("working" rank). rank =
        # 0.7*2 + 0.3*3.0 = 2.3 -> round(2.3) = 2 -> "middle". If the
        # fallback were anything else (e.g. 0.0 from an unguarded empty
        # mean), this would resolve to a different label.
        assert child.social_class == "middle"
        assert child.social_class in _TEST_VALID_CLASS_LABELS
        assert child.zone == empty_zone


class TestApplyInheritanceAtBirthNoPersistence:
    """The function never calls child.save() -- persistence stays the
    caller's responsibility, matching apply_trait_inheritance's and
    apply_social_inheritance's own no-save contract.
    """

    @pytest.mark.django_db
    def test_child_mutations_are_not_persisted(self, sim_with_zone):
        sim, zone = sim_with_zone
        mother = _make_agent(
            sim,
            zone,
            "Mother",
            social_class="wealthy",
            personality={name: 0.5 for name in PERSONALITY_HERITABLE_TRAITS},
        )
        father = _make_agent(
            sim,
            zone,
            "Father",
            social_class="middle",
            personality={name: 0.5 for name in PERSONALITY_HERITABLE_TRAITS},
        )
        # _make_agent always calls Agent.objects.create(...), so the child
        # already has a pk and a persisted wealth=100.0 (the helper's own
        # default) before the call under test -- this is the case the task
        # flags explicitly: assert the function performed no save by
        # checking a field left unsaved in the database, since the fixture
        # helper itself always saves.
        child = _make_agent(sim, zone, "Child")
        assert child.pk is not None
        original_wealth = child.wealth
        assert original_wealth == 100.0

        apply_inheritance_at_birth(child, mother, father, sim, sim.current_tick)

        # In-memory mutation happened...
        assert child.wealth == 0.0
        # ...but was never persisted: re-fetching from the database still
        # shows the pre-call value, proving no save() occurred.
        persisted = Agent.objects.get(pk=child.pk)
        assert persisted.wealth == original_wealth == 100.0


# ---------------------------------------------------------------------------
# resolve_heirs (Plan 3, T016/T017, user story 2 -- estate/succession)
# ---------------------------------------------------------------------------
#
# The heir-priority ladder (design spec Sezione 5, "Ereditarietà economica
# alla morte"): every era template's economic_inheritance.heir_priority is
# ["spouse", "children", "siblings", "extended_family", "government"]
# (verified identical across all five templates under
# epocha/apps/demography/templates/). resolve_heirs resolves WHO occupies
# each category -- never how the estate is split among them, which is a
# separate later mechanism (T019+, the primogeniture/equal_split/shari'a/
# matrilineal/nationalized distribution rules).
#
# Reuses sim_with_zone / _make_agent from above.


def _heir_template() -> dict:
    """Minimal synthetic template carrying only what resolve_heirs reads.

    Mirrors the real heir_priority order from every era template (verified
    identical across all five in the design spec and the templates
    themselves), isolated from the rest of the demography_template schema so
    these tests do not depend on unrelated template sections.
    """
    return {
        "economic_inheritance": {
            "heir_priority": ["spouse", "children", "siblings", "extended_family", "government"],
        }
    }


class TestResolveHeirsSpouse:
    """spouse category: the surviving partner from the deceased's active
    Couple (design spec Sezione 5, heir priority item 1).
    """

    @pytest.mark.django_db
    def test_spouse_of_active_couple_is_the_sole_heir(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        partner = _make_agent(sim, zone, "Partner")
        form_couple(deceased, partner, formed_at_tick=1)

        heirs = resolve_heirs(deceased, _heir_template())

        assert heirs["spouse"] == [partner]

    @pytest.mark.django_db
    def test_no_active_couple_yields_empty_spouse_list(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")

        heirs = resolve_heirs(deceased, _heir_template())

        assert heirs["spouse"] == []


class TestResolveHeirsChildren:
    """children category: living children found through EITHER parentage FK
    (design spec Sezione 5, heir priority item 2: "tramite parent_agent +
    other_parent_agent"), oldest first (primogeniture-dependent ordering).
    """

    @pytest.mark.django_db
    def test_children_via_both_parent_fks_are_found_ordered_oldest_first(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")

        younger = _make_agent(sim, zone, "Younger", parent_agent=deceased, birth_tick=20)
        older = _make_agent(sim, zone, "Older", other_parent_agent=deceased, birth_tick=5)

        heirs = resolve_heirs(deceased, _heir_template())

        assert heirs["children"] == [older, younger]

    @pytest.mark.django_db
    def test_dead_children_are_excluded(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        _make_agent(sim, zone, "DeadChild", parent_agent=deceased, birth_tick=5, is_alive=False)
        living_child = _make_agent(sim, zone, "LivingChild", parent_agent=deceased, birth_tick=10)

        heirs = resolve_heirs(deceased, _heir_template())

        assert heirs["children"] == [living_child]


class TestResolveHeirsSiblings:
    """siblings category: living agents sharing at least one non-null parent
    with the deceased (either parent_agent or other_parent_agent), never
    including the deceased itself.
    """

    @pytest.mark.django_db
    def test_siblings_sharing_a_parent_are_found_excluding_deceased(self, sim_with_zone):
        sim, zone = sim_with_zone
        common_parent = _make_agent(sim, zone, "CommonParent")
        deceased = _make_agent(sim, zone, "Deceased", parent_agent=common_parent, birth_tick=10)
        sibling = _make_agent(sim, zone, "Sibling", parent_agent=common_parent, birth_tick=5)

        heirs = resolve_heirs(deceased, _heir_template())

        assert heirs["siblings"] == [sibling]
        assert deceased not in heirs["siblings"]

    @pytest.mark.django_db
    def test_half_sibling_via_other_parent_agent_is_found(self, sim_with_zone):
        """A half-sibling sharing only the father (other_parent_agent) must
        also be found -- the "either parent" broadening documented on
        resolve_heirs, wider than the design spec's literal single-FK
        prose.
        """
        sim, zone = sim_with_zone
        common_father = _make_agent(sim, zone, "CommonFather")
        deceased = _make_agent(
            sim, zone, "Deceased", other_parent_agent=common_father, birth_tick=10
        )
        half_sibling = _make_agent(
            sim, zone, "HalfSibling", other_parent_agent=common_father, birth_tick=5
        )

        heirs = resolve_heirs(deceased, _heir_template())

        assert heirs["siblings"] == [half_sibling]

    @pytest.mark.django_db
    def test_dead_siblings_are_excluded(self, sim_with_zone):
        sim, zone = sim_with_zone
        common_parent = _make_agent(sim, zone, "CommonParent")
        deceased = _make_agent(sim, zone, "Deceased", parent_agent=common_parent, birth_tick=10)
        _make_agent(
            sim, zone, "DeadSibling", parent_agent=common_parent, birth_tick=5, is_alive=False
        )

        heirs = resolve_heirs(deceased, _heir_template())

        assert heirs["siblings"] == []


class TestResolveHeirsExtendedFamily:
    """extended_family category: living descendants of the deceased's
    grandparents, bounded to two generations down from them -- aunts/uncles
    and first cousins (design spec Sezione 5, heir priority item 4:
    "Famiglia estesa (lineage di nonno, fino a 2 generazioni)") -- excluding
    whoever is already counted as a child or sibling, and excluding the
    deceased.
    """

    @pytest.mark.django_db
    def test_aunt_and_cousin_are_found_via_grandparent_lineage(self, sim_with_zone):
        sim, zone = sim_with_zone
        grandparent = _make_agent(sim, zone, "Grandparent")
        parent = _make_agent(sim, zone, "Parent", parent_agent=grandparent, birth_tick=-60)
        aunt = _make_agent(sim, zone, "Aunt", parent_agent=grandparent, birth_tick=-58)
        deceased = _make_agent(sim, zone, "Deceased", parent_agent=parent, birth_tick=-30)
        cousin = _make_agent(sim, zone, "Cousin", parent_agent=aunt, birth_tick=-5)

        heirs = resolve_heirs(deceased, _heir_template())

        extended_ids = {agent.id for agent in heirs["extended_family"]}
        assert extended_ids == {aunt.id, cousin.id}

    @pytest.mark.django_db
    def test_no_recorded_parents_yields_empty_extended_family(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Orphan")

        heirs = resolve_heirs(deceased, _heir_template())

        assert heirs["extended_family"] == []


class TestResolveHeirsGovernmentFallbackShape:
    """When every category resolves empty (no heirs at all), the returned
    dict still carries every category key from heir_priority except
    "government" itself -- the terminal treasury fallback is represented by
    every OTHER category being empty, not by a key holding objects -- and
    nothing raises (design spec Sezione 5, heir priority item 5).
    """

    @pytest.mark.django_db
    def test_isolated_agent_yields_every_category_empty_and_no_government_key(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Isolated")

        heirs = resolve_heirs(deceased, _heir_template())

        assert heirs == {
            "spouse": [],
            "children": [],
            "siblings": [],
            "extended_family": [],
        }
        assert "government" not in heirs


class TestResolveHeirsDeterminism:
    """Two calls against the same deceased agent return identical ordering
    in every category -- required for reproducible estate settlement.
    """

    @pytest.mark.django_db
    def test_repeated_calls_return_identical_ordering(self, sim_with_zone):
        sim, zone = sim_with_zone
        grandparent = _make_agent(sim, zone, "Grandparent")
        parent = _make_agent(sim, zone, "Parent", parent_agent=grandparent, birth_tick=-60)
        aunt = _make_agent(sim, zone, "Aunt", parent_agent=grandparent, birth_tick=-58)
        deceased = _make_agent(sim, zone, "Deceased", parent_agent=parent, birth_tick=-30)
        _make_agent(sim, zone, "Cousin", parent_agent=aunt, birth_tick=-5)
        partner = _make_agent(sim, zone, "Partner", birth_tick=-28)
        form_couple(deceased, partner, formed_at_tick=1)
        _make_agent(sim, zone, "Sibling", parent_agent=parent, birth_tick=-25)
        _make_agent(sim, zone, "ChildA", parent_agent=deceased, birth_tick=15)
        _make_agent(sim, zone, "ChildB", parent_agent=deceased, birth_tick=5)

        first = resolve_heirs(deceased, _heir_template())
        second = resolve_heirs(deceased, _heir_template())

        for category in ("spouse", "children", "siblings", "extended_family"):
            assert [agent.id for agent in first[category]] == [
                agent.id for agent in second[category]
            ], category


class TestResolveHeirsQueryBudget:
    """Efficiency requirement: resolve_heirs runs once per death today, and
    the Plan 4 birth/death orchestrator will call it every tick -- the total
    query count must stay bounded and independent of family size (no N+1).
    """

    @pytest.mark.django_db
    def test_full_ladder_stays_within_fixed_query_budget(
        self, sim_with_zone, django_assert_num_queries
    ):
        sim, zone = sim_with_zone
        grandparent = _make_agent(sim, zone, "Grandparent")
        parent = _make_agent(sim, zone, "Parent", parent_agent=grandparent, birth_tick=-60)
        aunt = _make_agent(sim, zone, "Aunt", parent_agent=grandparent, birth_tick=-58)
        _make_agent(sim, zone, "Cousin", parent_agent=aunt, birth_tick=-20)
        deceased = _make_agent(sim, zone, "Deceased", parent_agent=parent, birth_tick=-30)
        partner = _make_agent(sim, zone, "Partner", birth_tick=-28)
        form_couple(deceased, partner, formed_at_tick=1)
        _make_agent(sim, zone, "Sibling", parent_agent=parent, birth_tick=-25)
        _make_agent(sim, zone, "Child", parent_agent=deceased, birth_tick=1)

        # 7 queries total, documented in resolve_heirs's own docstring:
        # spouse (Couple lookup + partner fetch) = 2, children = 1,
        # siblings = 1, extended_family (grandparent ids + aunts/uncles +
        # cousins) = 3. Fixed regardless of how many agents populate each
        # category.
        with django_assert_num_queries(7):
            resolve_heirs(deceased, _heir_template())


# ---------------------------------------------------------------------------
# apply_estate_tax (Plan 3, T018/T019, user story 2 -- estate/succession).
# Routes the era's flat `economic_inheritance.estate_tax_rate` to the
# government treasury via `add_to_treasury`, and returns the inheritable
# remainder -- the amount a later distribution step (T020+) actually splits
# among `resolve_heirs`'s resolved heirs.
# ---------------------------------------------------------------------------

# Tolerance for the conservation assertions below (remainder + treasury
# delta == total_estate_value). At the magnitudes used in these tests
# (estates of a few thousand to ~12,000 units), IEEE 754 double precision's
# ~2^-52 relative epsilon bounds any single multiplication's rounding error
# to roughly 1e-12 in absolute terms; two multiplications plus one addition
# cannot plausibly accumulate beyond that by more than a small constant
# factor. 1e-6 is therefore several orders of magnitude more generous than
# the rounding error these operations can actually produce -- verified
# empirically (see the T018 implementation notes) to be exactly 0.0 for the
# representative estate values exercised here. Used explicitly rather than
# relying on pytest.approx's own default so the tolerance is a documented,
# reviewed choice, not an implicit one.
_CONSERVATION_TOLERANCE = 1e-6


@pytest.fixture
def sim_with_government(sim_with_zone):
    """Extends `sim_with_zone` with a saved Government row for treasury tests.

    `add_to_treasury` (epocha.apps.world.government) requires a real,
    already-saved Government instance -- it calls `government.save(
    update_fields=["government_treasury"])` -- so an in-memory-only stub
    would fail. Reuses `sim_with_zone` rather than duplicating its
    user/simulation/world/zone scaffolding.
    """
    sim, zone = sim_with_zone
    government = Government.objects.create(simulation=sim)
    return sim, zone, government


class TestApplyEstateTaxModernRate:
    """Modern-democracy era: `estate_tax_rate` 0.40 (Piketty 2014, tables
    14.1-14.2 -- top marginal estate/inheritance tax rates)."""

    @pytest.mark.django_db
    def test_treasury_grows_by_exactly_forty_percent_and_remainder_is_sixty_percent(
        self, sim_with_government
    ):
        sim, zone, government = sim_with_government
        total_estate_value = 10_000.0
        rate = 0.40

        remainder = apply_estate_tax(total_estate_value, rate, government, "USD")

        assert remainder == pytest.approx(6_000.0, abs=_CONSERVATION_TOLERANCE)

        # Read back from the database (not the in-memory `government`
        # object add_to_treasury already mutated) to prove the credit was
        # actually persisted, not merely held in memory.
        government.refresh_from_db()
        assert government.government_treasury["USD"] == pytest.approx(
            4_000.0, abs=_CONSERVATION_TOLERANCE
        )


class TestApplyEstateTaxConservation:
    """remainder + treasury delta reproduces `total_estate_value` exactly,
    up to floating-point rounding -- the load-bearing invariant for
    whitepaper Sezione 4.2/4.8's accounting."""

    @pytest.mark.django_db
    def test_remainder_plus_treasury_delta_equals_input_estate(self, sim_with_government):
        sim, zone, government = sim_with_government
        total_estate_value = 12_345.67
        rate = 0.40

        remainder = apply_estate_tax(total_estate_value, rate, government, "USD")

        government.refresh_from_db()
        treasury_delta = government.government_treasury["USD"]

        assert remainder + treasury_delta == pytest.approx(
            total_estate_value, abs=_CONSERVATION_TOLERANCE
        )


class TestApplyEstateTaxZeroRate:
    """Pre-industrial eras: `estate_tax_rate` 0.0 -- feudal dues are
    modelled separately in the economy layer, not as an estate tax here."""

    @pytest.mark.django_db
    def test_zero_rate_routes_nothing_and_returns_full_value(self, sim_with_government):
        sim, zone, government = sim_with_government
        total_estate_value = 5_000.0

        remainder = apply_estate_tax(total_estate_value, 0.0, government, "USD")

        assert remainder == pytest.approx(total_estate_value)

        government.refresh_from_db()
        # "Unchanged or absent": whether the implementation skips the
        # add_to_treasury call entirely for a zero delta, or calls it with
        # amount=0.0, the effective treasury value for this currency is 0.0
        # either way -- .get(..., 0.0) covers both outcomes.
        assert government.government_treasury.get("USD", 0.0) == pytest.approx(0.0)


class TestApplyEstateTaxCurrencyIsolation:
    """Crediting one currency code leaves other currency codes already
    present in the treasury untouched."""

    @pytest.mark.django_db
    def test_crediting_one_currency_leaves_others_untouched(self, sim_with_government):
        sim, zone, government = sim_with_government
        government.government_treasury = {"EUR": 250.0, "gold_solidus": 12.0}
        government.save(update_fields=["government_treasury"])

        apply_estate_tax(1_000.0, 0.40, government, "USD")

        government.refresh_from_db()
        assert government.government_treasury["EUR"] == pytest.approx(250.0)
        assert government.government_treasury["gold_solidus"] == pytest.approx(12.0)
        assert government.government_treasury["USD"] == pytest.approx(400.0)


class TestApplyEstateTaxDegenerateInputs:
    """Out-of-range rate is clamped, not raised; a non-positive estate
    value never produces a negative treasury credit."""

    @pytest.mark.django_db
    def test_rate_above_one_is_clamped_to_one(self, sim_with_government):
        sim, zone, government = sim_with_government
        total_estate_value = 1_000.0

        remainder = apply_estate_tax(total_estate_value, 1.5, government, "USD")

        assert remainder == pytest.approx(0.0)
        government.refresh_from_db()
        assert government.government_treasury["USD"] == pytest.approx(total_estate_value)

    @pytest.mark.django_db
    def test_negative_rate_is_clamped_to_zero(self, sim_with_government):
        sim, zone, government = sim_with_government
        total_estate_value = 1_000.0

        remainder = apply_estate_tax(total_estate_value, -0.2, government, "USD")

        assert remainder == pytest.approx(total_estate_value)
        government.refresh_from_db()
        assert government.government_treasury.get("USD", 0.0) == pytest.approx(0.0)

    @pytest.mark.django_db
    def test_negative_estate_value_does_not_produce_negative_treasury_credit(
        self, sim_with_government
    ):
        sim, zone, government = sim_with_government

        apply_estate_tax(-500.0, 0.40, government, "USD")

        government.refresh_from_db()
        credited = government.government_treasury.get("USD", 0.0)
        assert credited >= 0.0

    @pytest.mark.django_db
    def test_zero_estate_value_returns_zero_and_credits_nothing(self, sim_with_government):
        sim, zone, government = sim_with_government

        remainder = apply_estate_tax(0.0, 0.40, government, "USD")

        assert remainder == pytest.approx(0.0)
        government.refresh_from_db()
        assert government.government_treasury.get("USD", 0.0) == pytest.approx(0.0)
