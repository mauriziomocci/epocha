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
"""

from __future__ import annotations

import random

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent
from epocha.apps.demography.inheritance import (
    DEFAULT_ERA_MEAN,
    DEFAULT_ERA_SD,
    apply_trait_inheritance,
    evaluate_derived_formula,
    inherit_trait,
)
from epocha.apps.demography.rng import get_seeded_rng
from epocha.apps.demography.template_loader import load_template
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World, Zone


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
