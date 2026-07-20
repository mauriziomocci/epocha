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

Also covers `distribute_estate` (Plan 3, T020/T021, user story 2): the five
per-era succession rules that decide HOW the inheritable remainder is split
among `resolve_heirs`'s resolved heirs -- `primogeniture` (Blackstone, W.
(1765), "Commentaries on the Laws of England"), `equal_split` (Napoleonic
Code, 1804), `shari'a` (Powers, D.S. (1986), "Studies in Qur'an and Hadith:
The Formation of the Islamic Law of Inheritance"), `matrilineal` (Schneider,
D.M. & Gough, K. (1961), "Matrilineal Kinship"), and `nationalized` (Nove,
A. (1969), "An Economic History of the USSR").

Also covers `assign_orphan_caretaker` (Plan 3, T024/T025, user story 3 --
orphan caretaker assignment): the two-stage priority ladder (same zone,
then any zone, each walked sibling > grandparent > aunt/uncle), the
deterministic birth_tick/id tiebreak within a kinship rung, the state-ward
fallback (conditions flag) when no living relative exists anywhere, the
module-wide no-persistence contract, and fix MISS-1 -- the orphan keeps
direct ownership of its inheritance, the caretaker only administers
(design spec Sezione 5, "Gestione orfani (fix MISS-1)").

Also covers `generate_mourning_memories` (Plan 3, T026/T027, user story 3
-- death leaves a mark): surviving spouse, surviving children, and strong
ties (`Relationship.strength > 0.6`, either direction) each receive one
`Memory` with `emotional_weight = 0.9`, deduplicated when an agent
qualifies under more than one category. Trap 2: the filter is
`Relationship.strength`, NOT `Agent.strength` (an inherited physical
trait, h^2 = 0.55) -- filtering on the wrong field would send grief
memories to muscular agents instead of close friends (design spec Sezione
5, "Cascata di memoria del lutto").

Also covers `process_inheritance_batch` (Plan 3, T028/T029, user story 3
-- the death-path orchestrator): multiple same-tick deaths process oldest
(by `age`) first, `id` ascending tiebreak (fix C-3); estate tax applies
exactly once per actual heir transfer, never cumulatively when the same
living heir inherits from two different same-tick decedents; a dead
intermediate (same tick or an earlier one) is never a bequest conduit,
because every resolver already filters `is_alive=True` (fix MISS-5); one
`DemographyEvent` of type `INHERITANCE_TRANSFER` per actual transfer; the
batch composes `dissolve_on_death`, the estate chain
(`resolve_heirs`/`apply_estate_tax`/`distribute_estate`),
`transfer_loans_as_lender`, `assign_orphan_caretaker`, and
`generate_mourning_memories`, including the MISS-4 case where both
partners of one couple die in the same batch. PRECONDITION, load-bearing
throughout this section: every agent passed in `deceased_agents` already
has `is_alive=False` BEFORE the call -- the caller (Plan 4's mortality
step) sets it, not this function.
"""

from __future__ import annotations

import logging
import random

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent, Memory, Relationship
from epocha.apps.demography.couple import form_couple
from epocha.apps.demography.inheritance import (
    DEFAULT_ERA_MEAN,
    DEFAULT_ERA_MEAN_EDUCATION,
    DEFAULT_ERA_SD,
    apply_estate_tax,
    apply_inheritance_at_birth,
    apply_social_inheritance,
    apply_trait_inheritance,
    assign_orphan_caretaker,
    distribute_estate,
    evaluate_derived_formula,
    generate_mourning_memories,
    inherit_trait,
    process_inheritance_batch,
    resolve_birth_attributes,
    resolve_heirs,
    transfer_loans_as_lender,
)
from epocha.apps.demography.models import Couple, DemographyEvent
from epocha.apps.demography.rng import get_seeded_rng
from epocha.apps.demography.template_loader import load_template
from epocha.apps.economy.models import Loan
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.government import add_to_treasury
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


# ---------------------------------------------------------------------------
# distribute_estate (Plan 3, T020/T021, user story 2 -- estate/succession).
# The five per-era succession rules that decide HOW the inheritable
# remainder from apply_estate_tax is split among resolve_heirs's resolved
# heirs (design spec Sezione 5): primogeniture (Blackstone 1765),
# equal_split (Napoleonic Code 1804), shari'a (Powers 1986), matrilineal
# (Schneider & Gough 1961), nationalized (Nove 1969). Reuses sim_with_zone /
# _make_agent / _heir_template / _CONSERVATION_TOLERANCE already defined
# above for resolve_heirs and apply_estate_tax.
#
# distribute_estate is a PURE function -- no .save(), no heir mutation --
# so every test below asserts on the returned allocation mapping alone,
# never touching the database beyond the read-only resolve_heirs call that
# builds its `heirs` argument.
# ---------------------------------------------------------------------------


class TestDistributeEstatePrimogeniture:
    """100% to a single heir, cascading children -> spouse -> siblings
    (Blackstone 1765); non-binary heirs ordered together with the female
    heirs at every tier.
    """

    @pytest.mark.django_db
    def test_eldest_son_takes_all_even_if_a_daughter_is_chronologically_older(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        _make_agent(
            sim,
            zone,
            "Daughter",
            parent_agent=deceased,
            birth_tick=1,
            gender=Agent.Gender.FEMALE,
        )
        younger_son = _make_agent(
            sim,
            zone,
            "YoungerSon",
            parent_agent=deceased,
            birth_tick=5,
            gender=Agent.Gender.MALE,
        )
        older_son = _make_agent(
            sim,
            zone,
            "OlderSon",
            parent_agent=deceased,
            birth_tick=3,
            gender=Agent.Gender.MALE,
        )

        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "primogeniture", 10_000.0)

        assert allocation == {older_son.id: 10_000.0}
        assert younger_son.id not in allocation

    @pytest.mark.django_db
    def test_daughters_only_eldest_daughter_takes_all(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        younger_daughter = _make_agent(
            sim,
            zone,
            "YoungerDaughter",
            parent_agent=deceased,
            birth_tick=10,
            gender=Agent.Gender.FEMALE,
        )
        older_daughter = _make_agent(
            sim,
            zone,
            "OlderDaughter",
            parent_agent=deceased,
            birth_tick=2,
            gender=Agent.Gender.FEMALE,
        )

        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "primogeniture", 8_000.0)

        assert allocation == {older_daughter.id: 8_000.0}
        assert younger_daughter.id not in allocation

    @pytest.mark.django_db
    def test_non_binary_child_ordered_with_daughters_by_birth_order(self, sim_with_zone):
        """No sons: the eldest of (daughters + non-binary children) wins,
        purely by birth order. Here the non-binary child is older than the
        daughter and inherits -- proof the two pools are merged, not that
        one categorically outranks the other.
        """
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        daughter = _make_agent(
            sim,
            zone,
            "Daughter",
            parent_agent=deceased,
            birth_tick=10,
            gender=Agent.Gender.FEMALE,
        )
        elder_non_binary = _make_agent(
            sim,
            zone,
            "ElderNonBinary",
            parent_agent=deceased,
            birth_tick=1,
            gender=Agent.Gender.NON_BINARY,
        )

        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "primogeniture", 5_000.0)

        assert allocation == {elder_non_binary.id: 5_000.0}
        assert daughter.id not in allocation

    @pytest.mark.django_db
    def test_no_children_cascades_to_spouse(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        partner = _make_agent(sim, zone, "Partner")
        form_couple(deceased, partner, formed_at_tick=1)

        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "primogeniture", 6_000.0)

        assert allocation == {partner.id: 6_000.0}

    @pytest.mark.django_db
    def test_no_children_no_spouse_cascades_to_eldest_brother(self, sim_with_zone):
        sim, zone = sim_with_zone
        common_parent = _make_agent(sim, zone, "CommonParent")
        deceased = _make_agent(sim, zone, "Deceased", parent_agent=common_parent, birth_tick=10)
        sister = _make_agent(
            sim,
            zone,
            "Sister",
            parent_agent=common_parent,
            birth_tick=2,
            gender=Agent.Gender.FEMALE,
        )
        brother = _make_agent(
            sim,
            zone,
            "Brother",
            parent_agent=common_parent,
            birth_tick=5,
            gender=Agent.Gender.MALE,
        )

        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "primogeniture", 3_000.0)

        assert allocation == {brother.id: 3_000.0}
        assert sister.id not in allocation

    @pytest.mark.django_db
    def test_no_heirs_at_all_yields_empty_allocation(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Isolated")

        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "primogeniture", 1_000.0)

        assert allocation == {}


class TestDistributeEstateEqualSplit:
    """Cash divided equally among children, with the spouse receiving a
    share equal to one child's (Napoleonic Code 1804): N children + spouse
    = N+1 equal shares.
    """

    @pytest.mark.django_db
    def test_three_children_and_spouse_yield_four_equal_shares(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        partner = _make_agent(sim, zone, "Partner")
        form_couple(deceased, partner, formed_at_tick=1)
        child_a = _make_agent(sim, zone, "ChildA", parent_agent=deceased, birth_tick=1)
        child_b = _make_agent(sim, zone, "ChildB", parent_agent=deceased, birth_tick=2)
        child_c = _make_agent(sim, zone, "ChildC", parent_agent=deceased, birth_tick=3)

        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "equal_split", 8_000.0)

        expected_share = 2_000.0
        for heir_id in (child_a.id, child_b.id, child_c.id, partner.id):
            assert allocation[heir_id] == pytest.approx(expected_share, abs=_CONSERVATION_TOLERANCE)
        assert sum(allocation.values()) == pytest.approx(8_000.0, abs=_CONSERVATION_TOLERANCE)


class TestDistributeEstateSharia:
    """Spouse takes 1/8 with children present, else 1/4; sons receive
    exactly twice a daughter's share (Powers 1986).
    """

    @pytest.mark.django_db
    def test_spouse_takes_one_eighth_with_children_and_son_takes_double_daughter(
        self, sim_with_zone
    ):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        partner = _make_agent(sim, zone, "Partner")
        form_couple(deceased, partner, formed_at_tick=1)
        son = _make_agent(
            sim, zone, "Son", parent_agent=deceased, birth_tick=1, gender=Agent.Gender.MALE
        )
        daughter = _make_agent(
            sim,
            zone,
            "Daughter",
            parent_agent=deceased,
            birth_tick=2,
            gender=Agent.Gender.FEMALE,
        )

        inheritable = 8_000.0
        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "shari'a", inheritable)

        assert allocation[partner.id] == pytest.approx(1_000.0, abs=_CONSERVATION_TOLERANCE)
        assert allocation[son.id] == pytest.approx(
            2 * allocation[daughter.id], abs=_CONSERVATION_TOLERANCE
        )
        assert sum(allocation.values()) == pytest.approx(inheritable, abs=_CONSERVATION_TOLERANCE)

    @pytest.mark.django_db
    def test_spouse_takes_one_quarter_without_children(self, sim_with_zone):
        """No children: the spouse's fixed share drops to 1/4; the
        residual cascades to the deceased's siblings -- the documented
        simplification of the classical residuary hierarchy described on
        `_distribute_sharia`.
        """
        sim, zone = sim_with_zone
        common_parent = _make_agent(sim, zone, "CommonParent")
        deceased = _make_agent(sim, zone, "Deceased", parent_agent=common_parent, birth_tick=10)
        partner = _make_agent(sim, zone, "Partner", birth_tick=8)
        form_couple(deceased, partner, formed_at_tick=1)
        _make_agent(sim, zone, "Sibling", parent_agent=common_parent, birth_tick=5)

        inheritable = 4_000.0
        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "shari'a", inheritable)

        assert allocation[partner.id] == pytest.approx(1_000.0, abs=_CONSERVATION_TOLERANCE)
        assert sum(allocation.values()) == pytest.approx(inheritable, abs=_CONSERVATION_TOLERANCE)


class TestDistributeEstateMatrilineal:
    """Estate passes to the children of the deceased's SISTERS (Schneider
    & Gough 1961); the deceased's own children never receive anything
    under this rule.
    """

    @pytest.mark.django_db
    def test_sisters_children_inherit_not_the_deceaseds_own_children(self, sim_with_zone):
        sim, zone = sim_with_zone
        common_parent = _make_agent(sim, zone, "CommonParent")
        deceased = _make_agent(sim, zone, "Deceased", parent_agent=common_parent, birth_tick=10)
        sister = _make_agent(
            sim,
            zone,
            "Sister",
            parent_agent=common_parent,
            birth_tick=5,
            gender=Agent.Gender.FEMALE,
        )
        niece = _make_agent(sim, zone, "Niece", parent_agent=sister, birth_tick=20)
        nephew = _make_agent(sim, zone, "Nephew", parent_agent=sister, birth_tick=25)
        own_child = _make_agent(sim, zone, "OwnChild", parent_agent=deceased, birth_tick=30)

        inheritable = 6_000.0
        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "matrilineal", inheritable)

        assert set(allocation.keys()) == {niece.id, nephew.id}
        assert own_child.id not in allocation
        assert allocation[niece.id] == pytest.approx(3_000.0, abs=_CONSERVATION_TOLERANCE)
        assert sum(allocation.values()) == pytest.approx(inheritable, abs=_CONSERVATION_TOLERANCE)

    @pytest.mark.django_db
    def test_no_sisters_yields_empty_allocation(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")

        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "matrilineal", 2_000.0)

        assert allocation == {}


class TestDistributeEstateNationalized:
    """100% to the state (Nove 1969, Soviet-style expropriation): the
    allocation is always empty, regardless of which heirs survive --
    "empty" here means the whole amount routes to the treasury, not that
    no heirs were found.
    """

    @pytest.mark.django_db
    def test_allocation_is_always_empty_even_with_surviving_heirs(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        partner = _make_agent(sim, zone, "Partner")
        form_couple(deceased, partner, formed_at_tick=1)
        _make_agent(sim, zone, "Child", parent_agent=deceased, birth_tick=1)

        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "nationalized", 9_000.0)

        assert allocation == {}


class TestDistributeEstateUnknownRule:
    """An unrecognized rule falls back to equal_split with a WARNING log,
    matching this module's established never-crash-on-template-data
    posture.
    """

    @pytest.mark.django_db
    def test_unknown_rule_falls_back_to_equal_split_with_warning(self, sim_with_zone, caplog):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        child_a = _make_agent(sim, zone, "ChildA", parent_agent=deceased, birth_tick=1)
        child_b = _make_agent(sim, zone, "ChildB", parent_agent=deceased, birth_tick=2)

        heirs = resolve_heirs(deceased, _heir_template())
        with caplog.at_level(logging.WARNING):
            allocation = distribute_estate(deceased, heirs, "not_a_real_rule", 4_000.0)

        assert allocation[child_a.id] == pytest.approx(2_000.0, abs=_CONSERVATION_TOLERANCE)
        assert allocation[child_b.id] == pytest.approx(2_000.0, abs=_CONSERVATION_TOLERANCE)
        assert any("not_a_real_rule" in message for message in caplog.messages)


class TestDistributeEstateConservation:
    """Sum of the allocation equals `inheritable` exactly, up to
    floating-point representation, for every rule that resolves at least
    one heir -- the load-bearing invariant for whitepaper Sezione 4.2/4.8's
    accounting (see `_allocate_with_exact_remainder`'s docstring for the
    remainder-absorption technique). `inheritable` is deliberately
    10_000.33 -- an amount that does NOT divide evenly across two or three
    heirs -- so these tests stress the remainder-absorption path rather
    than accidentally passing on inputs that happen to divide exactly.
    """

    @pytest.mark.django_db
    def test_primogeniture_conserves(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        _make_agent(sim, zone, "Son", parent_agent=deceased, birth_tick=1, gender=Agent.Gender.MALE)

        inheritable = 10_000.33
        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "primogeniture", inheritable)

        assert sum(allocation.values()) == pytest.approx(inheritable, abs=_CONSERVATION_TOLERANCE)

    @pytest.mark.django_db
    def test_equal_split_conserves_with_three_children_and_spouse(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        partner = _make_agent(sim, zone, "Partner")
        form_couple(deceased, partner, formed_at_tick=1)
        _make_agent(sim, zone, "ChildA", parent_agent=deceased, birth_tick=1)
        _make_agent(sim, zone, "ChildB", parent_agent=deceased, birth_tick=2)
        _make_agent(sim, zone, "ChildC", parent_agent=deceased, birth_tick=3)

        inheritable = 10_000.33
        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "equal_split", inheritable)

        assert sum(allocation.values()) == pytest.approx(inheritable, abs=_CONSERVATION_TOLERANCE)

    @pytest.mark.django_db
    def test_sharia_conserves_with_children(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        partner = _make_agent(sim, zone, "Partner")
        form_couple(deceased, partner, formed_at_tick=1)
        _make_agent(sim, zone, "Son", parent_agent=deceased, birth_tick=1, gender=Agent.Gender.MALE)
        _make_agent(
            sim,
            zone,
            "Daughter",
            parent_agent=deceased,
            birth_tick=2,
            gender=Agent.Gender.FEMALE,
        )
        _make_agent(
            sim,
            zone,
            "NonBinaryChild",
            parent_agent=deceased,
            birth_tick=3,
            gender=Agent.Gender.NON_BINARY,
        )

        inheritable = 10_000.33
        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "shari'a", inheritable)

        assert sum(allocation.values()) == pytest.approx(inheritable, abs=_CONSERVATION_TOLERANCE)

    @pytest.mark.django_db
    def test_sharia_conserves_without_children_via_sibling_cascade(self, sim_with_zone):
        sim, zone = sim_with_zone
        common_parent = _make_agent(sim, zone, "CommonParent")
        deceased = _make_agent(sim, zone, "Deceased", parent_agent=common_parent, birth_tick=10)
        partner = _make_agent(sim, zone, "Partner", birth_tick=8)
        form_couple(deceased, partner, formed_at_tick=1)
        _make_agent(
            sim,
            zone,
            "Brother",
            parent_agent=common_parent,
            birth_tick=5,
            gender=Agent.Gender.MALE,
        )
        _make_agent(
            sim,
            zone,
            "Sister",
            parent_agent=common_parent,
            birth_tick=6,
            gender=Agent.Gender.FEMALE,
        )

        inheritable = 10_000.33
        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "shari'a", inheritable)

        assert sum(allocation.values()) == pytest.approx(inheritable, abs=_CONSERVATION_TOLERANCE)

    @pytest.mark.django_db
    def test_matrilineal_conserves_with_three_nieces_and_nephews(self, sim_with_zone):
        sim, zone = sim_with_zone
        common_parent = _make_agent(sim, zone, "CommonParent")
        deceased = _make_agent(sim, zone, "Deceased", parent_agent=common_parent, birth_tick=10)
        sister = _make_agent(
            sim,
            zone,
            "Sister",
            parent_agent=common_parent,
            birth_tick=5,
            gender=Agent.Gender.FEMALE,
        )
        _make_agent(sim, zone, "Niece", parent_agent=sister, birth_tick=20)
        _make_agent(sim, zone, "Nephew", parent_agent=sister, birth_tick=25)
        _make_agent(sim, zone, "SecondNephew", parent_agent=sister, birth_tick=27)

        inheritable = 10_000.33
        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "matrilineal", inheritable)

        assert sum(allocation.values()) == pytest.approx(inheritable, abs=_CONSERVATION_TOLERANCE)


# ---------------------------------------------------------------------------
# T022 (Plan 3, user story 2 -- estate/succession, SC-002): end-to-end
# conservation across the FULL chain estate -> apply_estate_tax ->
# distribute_estate, for every one of the five per-era succession rules.
#
# The tests above (TestApplyEstateTaxConservation, TestDistributeEstate
# Conservation) each already prove conservation for one leg of the chain in
# isolation: apply_estate_tax's own remainder + treasury delta, and
# distribute_estate's own allocation sum. Neither, alone, proves the two
# legs compose correctly end to end. This class is the guard for that
# composition -- the actual invariant whitepaper Sezione 4.2 ("Economia
# comportamentale") and Sezione 4.8 ("Economia -- livello base") both state
# and both of which are already CONVERGED: no value is created or destroyed
# when an estate is settled, whichever succession rule the era template
# selects.
#
# The treasury side of the equation is read back from the DATABASE (via
# government.refresh_from_db()), never from apply_estate_tax's own return
# value or from add_to_treasury's in-memory mutation -- this is what proves
# the money actually landed in a persisted row, not merely that the
# arithmetic leading up to the write was correct.
# ---------------------------------------------------------------------------


def _build_deceased_for_primogeniture(sim, zone):
    """A single son: primogeniture's cascade resolves him as sole heir."""
    deceased = _make_agent(sim, zone, "Deceased")
    _make_agent(sim, zone, "Son", parent_agent=deceased, birth_tick=1, gender=Agent.Gender.MALE)
    return deceased


def _build_deceased_for_equal_split(sim, zone):
    """Spouse + two children: three equal shares, none of which divides
    total_estate_value evenly -- exercises the remainder-absorption path.
    """
    deceased = _make_agent(sim, zone, "Deceased")
    partner = _make_agent(sim, zone, "Partner")
    form_couple(deceased, partner, formed_at_tick=1)
    _make_agent(sim, zone, "ChildA", parent_agent=deceased, birth_tick=1)
    _make_agent(sim, zone, "ChildB", parent_agent=deceased, birth_tick=2)
    return deceased


def _build_deceased_for_sharia(sim, zone):
    """Spouse + son + daughter: exercises both the spouse's fixed fraction
    and the 2:1 male:female residuary split in the same allocation.
    """
    deceased = _make_agent(sim, zone, "Deceased")
    partner = _make_agent(sim, zone, "Partner")
    form_couple(deceased, partner, formed_at_tick=1)
    _make_agent(sim, zone, "Son", parent_agent=deceased, birth_tick=1, gender=Agent.Gender.MALE)
    _make_agent(
        sim, zone, "Daughter", parent_agent=deceased, birth_tick=2, gender=Agent.Gender.FEMALE
    )
    return deceased


def _build_deceased_for_matrilineal(sim, zone):
    """A sister with two living children: matrilineal never reads the
    deceased's own children or spouse, only descendants of sisters.
    """
    common_parent = _make_agent(sim, zone, "CommonParent")
    deceased = _make_agent(sim, zone, "Deceased", parent_agent=common_parent, birth_tick=10)
    sister = _make_agent(
        sim, zone, "Sister", parent_agent=common_parent, birth_tick=5, gender=Agent.Gender.FEMALE
    )
    _make_agent(sim, zone, "Niece", parent_agent=sister, birth_tick=20)
    _make_agent(sim, zone, "Nephew", parent_agent=sister, birth_tick=25)
    return deceased


def _build_deceased_for_nationalized(sim, zone):
    """Spouse + child present and living: proves the empty allocation is
    "nationalized by design", not "nobody was found" (see
    TestDistributeEstateNationalized above).
    """
    deceased = _make_agent(sim, zone, "Deceased")
    partner = _make_agent(sim, zone, "Partner")
    form_couple(deceased, partner, formed_at_tick=1)
    _make_agent(sim, zone, "Child", parent_agent=deceased, birth_tick=1)
    return deceased


class TestFullEstateChainConservation:
    """SC-002: sum(distribute_estate(...).values()) + (treasury delta from
    apply_estate_tax, read from the database) == the deceased's total
    estate, exactly within `_CONSERVATION_TOLERANCE`, for every one of the
    five succession rules, under a non-zero tax rate (0.40, the
    modern_democracy rate -- see TestApplyEstateTaxModernRate).

    `total_estate_value` is deliberately 12_345.67 (matching
    TestApplyEstateTaxConservation) rather than a round number, so the
    conservation assertion is not accidentally satisfied by inputs that
    happen to divide evenly at every step of the chain.
    """

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "rule, build_deceased",
        [
            ("primogeniture", _build_deceased_for_primogeniture),
            ("equal_split", _build_deceased_for_equal_split),
            ("shari'a", _build_deceased_for_sharia),
            ("matrilineal", _build_deceased_for_matrilineal),
            ("nationalized", _build_deceased_for_nationalized),
        ],
    )
    def test_full_chain_conserves_total_estate(self, sim_with_government, rule, build_deceased):
        sim, zone, government = sim_with_government
        deceased = build_deceased(sim, zone)

        total_estate_value = 12_345.67
        rate = 0.40

        heirs = resolve_heirs(deceased, _heir_template())
        inheritable = apply_estate_tax(total_estate_value, rate, government, "USD")

        government.refresh_from_db()
        tax_treasury_delta = government.government_treasury["USD"]

        allocation = distribute_estate(deceased, heirs, rule, inheritable)

        if rule == "nationalized":
            # nationalized (Nove 1969): distribute_estate's allocation is
            # empty BY DESIGN -- the entire post-tax remainder is state
            # property, not an unclaimed leftover (see the EMPTY
            # ALLOCATION SHAPE note in distribute_estate's own docstring).
            # distribute_estate is a pure function that only ever returns
            # an id-keyed allocation mapping; crediting the nationalized
            # remainder to the treasury is explicitly the CALLER's
            # responsibility (a later task, T029's
            # process_inheritance_batch), not distribute_estate's own. This
            # test simulates that caller step directly via add_to_treasury
            # -- the same primitive apply_estate_tax itself already used
            # for the tax leg -- so the chain closes end to end, then
            # re-reads the treasury from the database a second time to
            # prove the nationalized remainder, and not merely the tax,
            # actually landed.
            assert allocation == {}
            add_to_treasury(government, "USD", inheritable)
            government.refresh_from_db()
            total_treasury_delta = government.government_treasury["USD"]
            assert total_treasury_delta == pytest.approx(
                total_estate_value, abs=_CONSERVATION_TOLERANCE
            )
        else:
            allocation_total = sum(allocation.values())
            assert allocation_total + tax_treasury_delta == pytest.approx(
                total_estate_value, abs=_CONSERVATION_TOLERANCE
            )


# ---------------------------------------------------------------------------
# transfer_loans_as_lender (Plan 3, T023, user story 2 -- estate/succession).
# Reassigns the deceased's outstanding CREDITS (active loans where the
# deceased was the LENDER) to a living heir, or to the banking system when
# no living heir exists, so an agent's death never evaporates money someone
# else owes them -- the same conservation posture as apply_estate_tax /
# distribute_estate above, applied to the deceased's loan book rather than
# their cash/property estate.
# ---------------------------------------------------------------------------


def _make_loan(sim, borrower, lender=None, lender_type="agent", status="active", **kwargs):
    """Helper: create a Loan with sensible defaults (mirrors the pattern in
    epocha/apps/economy/tests/test_credit.py).
    """
    defaults = dict(
        principal=1_000.0,
        interest_rate=0.05,
        remaining_balance=1_000.0,
        issued_at_tick=0,
        due_at_tick=None,
    )
    defaults.update(kwargs)
    return Loan.objects.create(
        simulation=sim,
        borrower=borrower,
        lender=lender,
        lender_type=lender_type,
        status=status,
        **defaults,
    )


class TestTransferLoansAsLenderToLivingHeir:
    """An active loan where the deceased was the lender moves to a living
    heir, drawn from the heirs dict resolve_heirs already resolved.
    """

    @pytest.mark.django_db
    def test_active_loan_reassigned_to_sole_living_heir(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        heir = _make_agent(sim, zone, "Heir", parent_agent=deceased, birth_tick=1)
        borrower = _make_agent(sim, zone, "Borrower")
        loan = _make_loan(sim, borrower, lender=deceased)

        transfer_loans_as_lender(deceased, {"children": [heir]})

        loan.refresh_from_db()
        assert loan.lender_id == heir.id
        assert loan.lender_type == "agent"
        assert loan.status == "active"

    @pytest.mark.django_db
    def test_multiple_active_loans_round_robin_across_heirs_in_priority_order(self, sim_with_zone):
        """Round-robin over the flattened heir list, in the same
        spouse-first / children-oldest-first priority order the estate
        distribution rules use -- every heir must receive at least one
        loan when loans outnumber heirs, and no loan is dropped.
        """
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        spouse = _make_agent(sim, zone, "Spouse")
        form_couple(deceased, spouse, formed_at_tick=1)
        child = _make_agent(sim, zone, "Child", parent_agent=deceased, birth_tick=1)
        borrower = _make_agent(sim, zone, "Borrower")
        loans = [_make_loan(sim, borrower, lender=deceased) for _ in range(3)]

        heirs = resolve_heirs(deceased, _heir_template())
        assert [agent.id for agent in heirs["spouse"]] == [spouse.id]
        assert [agent.id for agent in heirs["children"]] == [child.id]

        transfer_loans_as_lender(deceased, heirs)

        for loan in loans:
            loan.refresh_from_db()
        new_lender_ids = {loan.lender_id for loan in loans}
        # Both heirs receive at least one loan (3 loans, 2 heirs,
        # round-robin) -- no heir is skipped and no loan is dropped.
        assert new_lender_ids == {spouse.id, child.id}
        assert loans[0].lender_id == spouse.id
        assert loans[1].lender_id == child.id
        assert loans[2].lender_id == spouse.id


class TestTransferLoansAsLenderNoLivingHeir:
    """No living heir at all: the loan transfers to the banking system
    (lender=None, lender_type="banking") and KEEPS being serviced -- the
    conserving resolution of the spec's self-contradiction (see
    transfer_loans_as_lender's own docstring for the full account).
    """

    @pytest.mark.django_db
    def test_no_heirs_transfers_to_banking_system_and_stays_active(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        borrower = _make_agent(sim, zone, "Borrower")
        loan = _make_loan(sim, borrower, lender=deceased)

        transfer_loans_as_lender(deceased, {"spouse": [], "children": [], "siblings": []})

        loan.refresh_from_db()
        assert loan.lender_id is None
        assert loan.lender_type == "banking"
        assert loan.status == "active"


class TestTransferLoansAsLenderScopeGuards:
    """Non-active loans and borrower-side loans are never touched."""

    @pytest.mark.django_db
    @pytest.mark.parametrize("status", ["repaid", "defaulted"])
    def test_non_active_loan_is_untouched(self, sim_with_zone, status):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        heir = _make_agent(sim, zone, "Heir", parent_agent=deceased, birth_tick=1)
        borrower = _make_agent(sim, zone, "Borrower")
        loan = _make_loan(sim, borrower, lender=deceased, status=status)

        transfer_loans_as_lender(deceased, {"children": [heir]})

        loan.refresh_from_db()
        assert loan.lender_id == deceased.id
        assert loan.lender_type == "agent"
        assert loan.status == status

    @pytest.mark.django_db
    def test_loan_where_deceased_is_borrower_is_untouched(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        heir = _make_agent(sim, zone, "Heir", parent_agent=deceased, birth_tick=1)
        other_lender = _make_agent(sim, zone, "OtherLender")
        loan = _make_loan(sim, deceased, lender=other_lender)

        transfer_loans_as_lender(deceased, {"children": [heir]})

        loan.refresh_from_db()
        assert loan.lender_id == other_lender.id
        assert loan.borrower_id == deceased.id
        assert loan.status == "active"

    @pytest.mark.django_db
    def test_banking_lender_type_loan_with_null_lender_is_untouched(self, sim_with_zone):
        """A loan already carried by the banking system (lender=None) has
        no bearing on the deceased's own lender-side loan book and must
        never be touched, even though its lender FK happens to be null
        like a freshly-transferred heirless loan would be.
        """
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        heir = _make_agent(sim, zone, "Heir", parent_agent=deceased, birth_tick=1)
        borrower = _make_agent(sim, zone, "Borrower")
        loan = _make_loan(sim, borrower, lender=None, lender_type="banking")

        transfer_loans_as_lender(deceased, {"children": [heir]})

        loan.refresh_from_db()
        assert loan.lender_id is None
        assert loan.lender_type == "banking"


class TestTransferLoansAsLenderQueryBudget:
    """Efficiency requirement: Plan 4 will call this once per death, every
    tick -- the write path must not become N+1 as the deceased's loan book
    grows (see this module's established query-budget convention, e.g.
    TestResolveHeirsQueryBudget above).
    """

    @pytest.mark.django_db
    def test_write_count_is_bounded_independent_of_loan_count(
        self, sim_with_zone, django_assert_num_queries
    ):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        spouse = _make_agent(sim, zone, "Spouse")
        form_couple(deceased, spouse, formed_at_tick=1)
        child = _make_agent(sim, zone, "Child", parent_agent=deceased, birth_tick=1)
        borrower = _make_agent(sim, zone, "Borrower")
        for _ in range(5):
            _make_loan(sim, borrower, lender=deceased)

        heirs = {"spouse": [spouse], "children": [child]}

        # 1 query to fetch the deceased's active lender-side loans, plus 1
        # bulk_update UPDATE for the reassignment -- 2 queries regardless
        # of loan count, never N+1 individual .save() calls.
        with django_assert_num_queries(2):
            transfer_loans_as_lender(deceased, heirs)


# ---------------------------------------------------------------------------
# assign_orphan_caretaker (Plan 3, T024/T025, user story 3 -- orphan
# caretaker assignment, fix MISS-1)
# ---------------------------------------------------------------------------
#
# Design spec Sezione 5, "Gestione orfani (fix MISS-1)": "Quando entrambi i
# genitori biologici di un minorenne (age < adulthood_age) sono morti, il
# minore viene assegnato un caretaker_agent secondo la priorità seguente:
# parente vivente più vicino nella stessa zona (fratello, nonno, zio/zia),
# poi qualsiasi parente vivente ovunque, poi None (pupillo dello stato). Un
# orfano con caretaker_agent = None viene flaggato e
# Government.government_treasury copre la sua sussistenza (modellando il
# wardship statale). L'orfano riceve comunque la sua eredità direttamente;
# il caretaker amministra ma non possiede gli asset."
#
# The treasury-subsistence flow itself is Plan 4's per-tick orchestrator
# job and is NOT asserted here -- only the state-ward flag this function is
# responsible for (a "state_ward" entry appended to Agent.conditions) is.
#
# `assign_orphan_caretaker` does not exist yet (implemented in T025); the
# import above therefore fails at collection time with "cannot import name
# 'assign_orphan_caretaker'", this file's established RED-first signal for
# a not-yet-implemented function (see e.g. T016/T018/T020/T023's own RED
# commits).
#
# The caller (the future Plan 4 death orchestrator) guarantees `minor` is
# an orphaned minor before calling this function -- no test here exercises
# adulthood, aliveness, or "still has a living parent" guards on `minor`
# itself; those are explicitly out of scope for T024 per the task
# description.


def _make_other_zone(world, name="OtherZone"):
    """A second `Zone` on the same `World`, for the cross-zone caretaker-
    priority tests below (design spec Sezione 5, Gestione orfani, fix
    MISS-1: stage 1 of the ladder is scoped to "la stessa zona" of the
    minor, so distinguishing same-zone from other-zone candidates is
    load-bearing here). Mirrors the `Zone` creation kwargs used by the
    `sim_with_zone` fixture above, with a disjoint bounding box so the two
    zones are geometrically distinct.
    """
    return Zone.objects.create(
        world=world,
        name=name,
        zone_type="residential",
        boundary=Polygon.from_bbox((200, 200, 300, 300)),
        center=Point(250, 250),
    )


class TestAssignOrphanCaretakerSameZoneKinshipPriority:
    """Stage 1 of the ladder (same zone as the minor) walks the kinship
    rungs in order: sibling > grandparent > aunt/uncle.
    """

    @pytest.mark.django_db
    def test_same_zone_sibling_beats_same_zone_grandparent_and_aunt_uncle(self, sim_with_zone):
        sim, zone = sim_with_zone
        grandparent = _make_agent(sim, zone, "Grandparent", birth_tick=-100)
        mother = _make_agent(
            sim, zone, "Mother", parent_agent=grandparent, is_alive=False, birth_tick=-60
        )
        _make_agent(sim, zone, "Aunt", parent_agent=grandparent, birth_tick=-58)
        sibling = _make_agent(sim, zone, "Sibling", parent_agent=mother, birth_tick=5)
        minor = _make_agent(sim, zone, "Minor", parent_agent=mother, age=10, birth_tick=10)

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker == sibling

    @pytest.mark.django_db
    def test_same_zone_grandparent_beats_same_zone_aunt_uncle_when_no_sibling(self, sim_with_zone):
        sim, zone = sim_with_zone
        grandparent = _make_agent(sim, zone, "Grandparent", birth_tick=-100)
        mother = _make_agent(
            sim, zone, "Mother", parent_agent=grandparent, is_alive=False, birth_tick=-60
        )
        _make_agent(sim, zone, "Aunt", parent_agent=grandparent, birth_tick=-58)
        minor = _make_agent(sim, zone, "Minor", parent_agent=mother, age=10, birth_tick=10)

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker == grandparent

    @pytest.mark.django_db
    def test_same_zone_aunt_uncle_is_picked_when_no_sibling_or_grandparent_are_same_zone(
        self, sim_with_zone
    ):
        """The grandparent itself lives in a different zone (so it is not a
        stage-1 candidate), but its child -- the minor's aunt -- lives in
        the minor's own zone and is found through the grandparent lineage.
        """
        sim, zone = sim_with_zone
        other_zone = _make_other_zone(zone.world)
        grandparent = _make_agent(sim, other_zone, "Grandparent", birth_tick=-100)
        mother = _make_agent(
            sim, zone, "Mother", parent_agent=grandparent, is_alive=False, birth_tick=-60
        )
        aunt = _make_agent(sim, zone, "Aunt", parent_agent=grandparent, birth_tick=-58)
        minor = _make_agent(sim, zone, "Minor", parent_agent=mother, age=10, birth_tick=10)

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker == aunt


class TestAssignOrphanCaretakerStageOneBeatsStageTwo:
    """A same-zone relative at a LOWER-priority kinship rung still outranks
    a HIGHER-priority kinship rung relative in a different zone -- stage 1
    (same zone) is exhausted in full before stage 2 (any zone) is even
    considered.
    """

    @pytest.mark.django_db
    def test_same_zone_grandparent_beats_other_zone_sibling(self, sim_with_zone):
        sim, zone = sim_with_zone
        other_zone = _make_other_zone(zone.world)
        grandparent = _make_agent(sim, zone, "Grandparent", birth_tick=-100)
        mother = _make_agent(
            sim, zone, "Mother", parent_agent=grandparent, is_alive=False, birth_tick=-60
        )
        _make_agent(sim, other_zone, "Sibling", parent_agent=mother, birth_tick=5)
        minor = _make_agent(sim, zone, "Minor", parent_agent=mother, age=10, birth_tick=10)

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker == grandparent

    @pytest.mark.django_db
    def test_same_zone_aunt_uncle_beats_other_zone_sibling(self, sim_with_zone):
        """The grandparent itself lives in a different zone (so it is not a
        stage-1 candidate and cannot out-rank the aunt on the grandparent
        rung) -- only the aunt qualifies for stage 1, and she must still
        beat the other-zone sibling.
        """
        sim, zone = sim_with_zone
        other_zone = _make_other_zone(zone.world)
        grandparent = _make_agent(sim, other_zone, "Grandparent", birth_tick=-100)
        mother = _make_agent(
            sim, zone, "Mother", parent_agent=grandparent, is_alive=False, birth_tick=-60
        )
        aunt = _make_agent(sim, zone, "Aunt", parent_agent=grandparent, birth_tick=-58)
        _make_agent(sim, other_zone, "Sibling", parent_agent=mother, birth_tick=5)
        minor = _make_agent(sim, zone, "Minor", parent_agent=mother, age=10, birth_tick=10)

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker == aunt


class TestAssignOrphanCaretakerStageTwoAnyZonePriority:
    """When stage 1 (same zone) finds nobody, stage 2 walks the same
    kinship ladder across every zone.
    """

    @pytest.mark.django_db
    def test_other_zone_sibling_beats_other_zone_grandparent(self, sim_with_zone):
        sim, zone = sim_with_zone
        other_zone = _make_other_zone(zone.world)
        grandparent = _make_agent(sim, other_zone, "Grandparent", birth_tick=-100)
        mother = _make_agent(
            sim, other_zone, "Mother", parent_agent=grandparent, is_alive=False, birth_tick=-60
        )
        sibling = _make_agent(sim, other_zone, "Sibling", parent_agent=mother, birth_tick=5)
        minor = _make_agent(sim, zone, "Minor", parent_agent=mother, age=10, birth_tick=10)

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker == sibling

    @pytest.mark.django_db
    def test_single_other_zone_relative_is_assigned_when_no_same_zone_candidate(
        self, sim_with_zone
    ):
        sim, zone = sim_with_zone
        other_zone = _make_other_zone(zone.world)
        grandparent = _make_agent(sim, other_zone, "Grandparent", birth_tick=-100)
        mother = _make_agent(
            sim, other_zone, "Mother", parent_agent=grandparent, is_alive=False, birth_tick=-60
        )
        minor = _make_agent(sim, zone, "Minor", parent_agent=mother, age=10, birth_tick=10)

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker == grandparent


class TestAssignOrphanCaretakerNoLivingRelativeStateWard:
    """No living relative anywhere (neither zone): returns None,
    `caretaker_agent` stays None, and "state_ward" is appended to
    `Agent.conditions` -- the flag mechanism the design spec calls
    "flaggato" ahead of the treasury covering subsistence (Plan 4's
    per-tick job, not asserted here).
    """

    @pytest.mark.django_db
    def test_no_living_relative_returns_none_and_flags_state_ward(self, sim_with_zone):
        sim, zone = sim_with_zone
        mother = _make_agent(sim, zone, "Mother", is_alive=False, birth_tick=-60)
        father = _make_agent(sim, zone, "Father", is_alive=False, birth_tick=-60)
        minor = _make_agent(
            sim,
            zone,
            "Minor",
            parent_agent=mother,
            other_parent_agent=father,
            age=10,
            birth_tick=10,
        )

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker is None
        assert minor.caretaker_agent is None
        assert "state_ward" in minor.conditions

    @pytest.mark.django_db
    def test_state_ward_flag_is_appended_not_overwriting_existing_conditions(self, sim_with_zone):
        sim, zone = sim_with_zone
        mother = _make_agent(sim, zone, "Mother", is_alive=False, birth_tick=-60)
        minor = _make_agent(
            sim,
            zone,
            "Minor",
            parent_agent=mother,
            age=10,
            birth_tick=10,
            conditions=["chronic_illness"],
        )

        assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert minor.conditions == ["chronic_illness", "state_ward"]


class TestAssignOrphanCaretakerDeterministicTiebreak:
    """Within a kinship rung, ties break by `birth_tick` ascending (oldest
    first), then `id` ascending -- the same convention as
    `_resolve_sibling_heirs` above.
    """

    @pytest.mark.django_db
    def test_lower_birth_tick_sibling_wins_regardless_of_creation_order(self, sim_with_zone):
        sim, zone = sim_with_zone
        mother = _make_agent(sim, zone, "Mother", is_alive=False, birth_tick=-60)
        # Created in reverse birth_tick order: the younger sibling gets the
        # LOWER id, so a naive "first created" or "lowest id" selection
        # would wrongly pick it instead of the older (lower birth_tick)
        # sibling.
        younger_sibling = _make_agent(
            sim, zone, "YoungerSibling", parent_agent=mother, birth_tick=20
        )
        older_sibling = _make_agent(sim, zone, "OlderSibling", parent_agent=mother, birth_tick=5)
        minor = _make_agent(sim, zone, "Minor", parent_agent=mother, age=10, birth_tick=10)

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker == older_sibling
        # Self-check: id order is the opposite of birth_tick order, so this
        # result cannot be explained by an accidental id-only tiebreak.
        assert older_sibling.id > younger_sibling.id

    @pytest.mark.django_db
    def test_equal_birth_tick_lower_id_wins(self, sim_with_zone):
        sim, zone = sim_with_zone
        mother = _make_agent(sim, zone, "Mother", is_alive=False, birth_tick=-60)
        first_sibling = _make_agent(sim, zone, "FirstSibling", parent_agent=mother, birth_tick=5)
        second_sibling = _make_agent(sim, zone, "SecondSibling", parent_agent=mother, birth_tick=5)
        minor = _make_agent(sim, zone, "Minor", parent_agent=mother, age=10, birth_tick=10)

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker == first_sibling
        assert first_sibling.id < second_sibling.id  # self-check


class TestAssignOrphanCaretakerDeadRelativesSkipped:
    """Dead relatives (`is_alive=False`) never qualify as a caretaker, at
    any kinship rung and in either stage of the ladder.
    """

    @pytest.mark.django_db
    def test_dead_same_zone_sibling_is_skipped_in_favor_of_same_zone_grandparent(
        self, sim_with_zone
    ):
        sim, zone = sim_with_zone
        grandparent = _make_agent(sim, zone, "Grandparent", birth_tick=-100)
        mother = _make_agent(
            sim, zone, "Mother", parent_agent=grandparent, is_alive=False, birth_tick=-60
        )
        _make_agent(sim, zone, "DeadSibling", parent_agent=mother, birth_tick=5, is_alive=False)
        minor = _make_agent(sim, zone, "Minor", parent_agent=mother, age=10, birth_tick=10)

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker == grandparent

    @pytest.mark.django_db
    def test_only_relative_anywhere_is_dead_yields_none_and_flags_state_ward(self, sim_with_zone):
        sim, zone = sim_with_zone
        other_zone = _make_other_zone(zone.world)
        mother = _make_agent(sim, zone, "Mother", is_alive=False, birth_tick=-60)
        _make_agent(
            sim, other_zone, "DeadSibling", parent_agent=mother, birth_tick=5, is_alive=False
        )
        minor = _make_agent(sim, zone, "Minor", parent_agent=mother, age=10, birth_tick=10)

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker is None
        assert "state_ward" in minor.conditions


class TestAssignOrphanCaretakerNoPersistence:
    """No-persistence contract (module-wide, settled): the function
    mutates the passed `minor` instance but NEVER calls `.save()` --
    consistent with `distribute_estate`'s own "WITHOUT persisting"
    contract (T021), leaving the write to the caller (the Plan 4
    orchestrator).
    """

    @pytest.mark.django_db
    def test_successful_assignment_is_not_persisted_to_database(self, sim_with_zone):
        sim, zone = sim_with_zone
        mother = _make_agent(sim, zone, "Mother", is_alive=False, birth_tick=-60)
        sibling = _make_agent(sim, zone, "Sibling", parent_agent=mother, birth_tick=5)
        minor = _make_agent(sim, zone, "Minor", parent_agent=mother, age=10, birth_tick=10)

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker == sibling
        # The in-memory instance IS mutated by the call...
        assert minor.caretaker_agent_id == sibling.id

        # ...but nothing was ever written to the database.
        persisted = Agent.objects.get(id=minor.id)
        assert persisted.caretaker_agent_id is None


class TestAssignOrphanCaretakerOwnershipFixMiss1:
    """Fix MISS-1 (design spec Sezione 5, Gestione orfani): "L'orfano
    riceve comunque la sua eredità direttamente; il caretaker amministra
    ma non possiede gli asset." The caretaker assignment call must never
    move wealth between the orphan and the caretaker -- the orphan keeps
    direct ownership of whatever it inherited.
    """

    @pytest.mark.django_db
    def test_call_does_not_transfer_wealth_between_orphan_and_caretaker(self, sim_with_zone):
        sim, zone = sim_with_zone
        mother = _make_agent(sim, zone, "Mother", is_alive=False, birth_tick=-60)
        sibling = _make_agent(sim, zone, "Sibling", parent_agent=mother, birth_tick=5, wealth=100.0)
        minor = _make_agent(
            sim, zone, "Minor", parent_agent=mother, age=10, birth_tick=10, wealth=500.0
        )
        minor_wealth_before = minor.wealth
        sibling_wealth_before = sibling.wealth

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker == sibling
        assert minor.wealth == minor_wealth_before
        assert sibling.wealth == sibling_wealth_before


class TestAssignOrphanCaretakerKinshipDefinitions:
    """Kinship definitions match this module's existing conventions: the
    sibling match is broadened to either parentage FK (same as
    `_resolve_sibling_heirs` above), and the grandparent lookup walks
    through EITHER of the minor's own two parentage FKs, not just
    `parent_agent`.
    """

    @pytest.mark.django_db
    def test_half_sibling_via_other_parent_agent_counts_as_sibling(self, sim_with_zone):
        sim, zone = sim_with_zone
        father = _make_agent(sim, zone, "Father", is_alive=False, birth_tick=-60)
        half_sibling = _make_agent(
            sim, zone, "HalfSibling", other_parent_agent=father, birth_tick=5
        )
        minor = _make_agent(sim, zone, "Minor", other_parent_agent=father, age=10, birth_tick=10)

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker == half_sibling

    @pytest.mark.django_db
    def test_grandparent_via_minors_other_parent_agent_is_found(self, sim_with_zone):
        """The grandparent lookup must walk BOTH of the minor's own
        parentage FKs -- here the grandparent is reachable only through
        the minor's `other_parent_agent` (father) side, not `parent_agent`.
        """
        sim, zone = sim_with_zone
        grandparent = _make_agent(sim, zone, "Grandparent", birth_tick=-100)
        father = _make_agent(
            sim, zone, "Father", parent_agent=grandparent, is_alive=False, birth_tick=-60
        )
        minor = _make_agent(sim, zone, "Minor", other_parent_agent=father, age=10, birth_tick=10)

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker == grandparent


# ---------------------------------------------------------------------------
# generate_mourning_memories (Plan 3, T026/T027, user story 3 -- death
# leaves a mark). Design spec Sezione 5, "Cascata di memoria del lutto":
# the surviving spouse, surviving children, and every living agent tied to
# the deceased by a Relationship with strength > 0.6 (either direction)
# each receive one first-hand Memory of the death, deduplicated across
# categories. This function only creates the direct memories -- carrying
# them onward to socially-distant agents is the existing per-tick
# `propagate_information` system's job, called later, never from here.
#
# TRAP 2 (verbatim, load-bearing): the strong-tie filter is
# `Relationship.strength`, NOT `Agent.strength`. `Agent.strength` is an
# inherited PHYSICAL trait (h^2 = 0.55, Falconer & Mackay 1996 kernel --
# see `TestInheritTraitTwoParents` above) measuring how strong an agent's
# body is; `Relationship.strength` measures how strong a SOCIAL bond is.
# Filtering the grief cascade on the former would deliver memories to
# muscular strangers instead of close friends -- a category error the
# TestGenerateMourningMemoriesTrap2 class below is built to catch.
#
# `generate_mourning_memories` does not exist yet (implemented in T027);
# the import above therefore fails at collection time with "cannot import
# name 'generate_mourning_memories'", this file's established RED-first
# signal (see e.g. T016/T018/T020/T023/T024's own RED commits).


class TestGenerateMourningMemoriesSpouse:
    """The surviving partner of the deceased's active Couple receives one
    memory (design spec Sezione 5, heir-adjacent recipient list item 1).
    """

    @pytest.mark.django_db
    def test_surviving_spouse_receives_memory_with_the_module_row_shape(self, sim_with_zone):
        """Canonical row-shape check (asserted once here, not repeated per
        recipient category below): `agent`, `emotional_weight=0.9`,
        `source_type=DIRECT`, `reliability=1.0`, `tick_created=tick`,
        `origin_agent=deceased`, and a `content` sentence naming the
        deceased (wording itself is T027's freedom, not pinned here).
        """
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        partner = _make_agent(sim, zone, "Partner")
        form_couple(deceased, partner, formed_at_tick=1)

        generate_mourning_memories(deceased, tick=sim.current_tick)

        memory = Memory.objects.get(agent=partner, origin_agent=deceased)
        assert memory.emotional_weight == 0.9
        assert memory.source_type == Memory.SourceType.DIRECT
        assert memory.reliability == 1.0
        assert memory.tick_created == sim.current_tick
        assert deceased.name in memory.content

    @pytest.mark.django_db
    def test_dead_partner_in_active_couple_receives_nothing(self, sim_with_zone):
        """`active_couple_for` does not itself check the partner's own
        aliveness (see `_resolve_spouse_heirs`'s own documented edge case)
        -- this function must apply the "only if alive" qualifier itself.
        """
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        partner = _make_agent(sim, zone, "Partner", is_alive=False)
        form_couple(deceased, partner, formed_at_tick=1)

        generate_mourning_memories(deceased, tick=sim.current_tick)

        assert not Memory.objects.filter(agent=partner, origin_agent=deceased).exists()

    @pytest.mark.django_db
    def test_no_active_couple_yields_no_spousal_memory(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")

        generate_mourning_memories(deceased, tick=sim.current_tick)

        assert not Memory.objects.filter(origin_agent=deceased).exists()


class TestGenerateMourningMemoriesChildren:
    """Living children of the deceased (either parentage FK) each receive
    one memory (design spec Sezione 5, recipient list item 2).
    """

    @pytest.mark.django_db
    def test_surviving_children_via_both_parent_fks_receive_memory(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        child_via_mother_fk = _make_agent(
            sim, zone, "ChildViaMotherFk", parent_agent=deceased, birth_tick=5
        )
        child_via_father_fk = _make_agent(
            sim, zone, "ChildViaFatherFk", other_parent_agent=deceased, birth_tick=6
        )

        generate_mourning_memories(deceased, tick=sim.current_tick)

        assert Memory.objects.filter(agent=child_via_mother_fk, origin_agent=deceased).exists()
        assert Memory.objects.filter(agent=child_via_father_fk, origin_agent=deceased).exists()

    @pytest.mark.django_db
    def test_dead_child_receives_nothing(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        dead_child = _make_agent(
            sim, zone, "DeadChild", parent_agent=deceased, birth_tick=5, is_alive=False
        )

        generate_mourning_memories(deceased, tick=sim.current_tick)

        assert not Memory.objects.filter(agent=dead_child, origin_agent=deceased).exists()


class TestGenerateMourningMemoriesStrongTies:
    """Living agents linked to the deceased by a `Relationship` with
    `strength > 0.6`, in EITHER direction, each receive one memory (design
    spec Sezione 5, recipient list item 3).
    """

    @pytest.mark.django_db
    def test_strong_tie_with_deceased_as_agent_from_receives_memory(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        friend = _make_agent(sim, zone, "Friend")
        Relationship.objects.create(
            agent_from=deceased,
            agent_to=friend,
            relation_type=Relationship.RelationType.FRIENDSHIP,
            strength=0.8,
            since_tick=0,
        )

        generate_mourning_memories(deceased, tick=sim.current_tick)

        assert Memory.objects.filter(agent=friend, origin_agent=deceased).exists()

    @pytest.mark.django_db
    def test_strong_tie_with_deceased_as_agent_to_receives_memory(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        friend = _make_agent(sim, zone, "Friend")
        Relationship.objects.create(
            agent_from=friend,
            agent_to=deceased,
            relation_type=Relationship.RelationType.FRIENDSHIP,
            strength=0.8,
            since_tick=0,
        )

        generate_mourning_memories(deceased, tick=sim.current_tick)

        assert Memory.objects.filter(agent=friend, origin_agent=deceased).exists()

    @pytest.mark.django_db
    def test_boundary_strength_exactly_zero_point_six_receives_nothing(self, sim_with_zone):
        """Strict `>` boundary: `strength = 0.6` exactly does NOT qualify."""
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        acquaintance = _make_agent(sim, zone, "Acquaintance")
        Relationship.objects.create(
            agent_from=deceased,
            agent_to=acquaintance,
            relation_type=Relationship.RelationType.FRIENDSHIP,
            strength=0.6,
            since_tick=0,
        )

        generate_mourning_memories(deceased, tick=sim.current_tick)

        assert not Memory.objects.filter(agent=acquaintance, origin_agent=deceased).exists()

    @pytest.mark.django_db
    def test_dead_strong_tie_receives_nothing(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        dead_friend = _make_agent(sim, zone, "DeadFriend", is_alive=False)
        Relationship.objects.create(
            agent_from=deceased,
            agent_to=dead_friend,
            relation_type=Relationship.RelationType.FRIENDSHIP,
            strength=0.9,
            since_tick=0,
        )

        generate_mourning_memories(deceased, tick=sim.current_tick)

        assert not Memory.objects.filter(agent=dead_friend, origin_agent=deceased).exists()


class TestGenerateMourningMemoriesTrap2:
    """Trap 2 (mandatory, verbatim): the strong-tie filter MUST be
    `Relationship.strength`, never `Agent.strength`. Each test here is
    constructed so that filtering on the wrong field flips the assertion.
    """

    @pytest.mark.django_db
    def test_muscular_agent_with_no_relationship_receives_nothing(self, sim_with_zone):
        """High `Agent.strength` (physical trait) alone, with no
        `Relationship` row at all to the deceased, must not qualify.
        """
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        muscular_stranger = _make_agent(sim, zone, "MuscularStranger", strength=0.95)

        generate_mourning_memories(deceased, tick=sim.current_tick)

        assert not Memory.objects.filter(agent=muscular_stranger, origin_agent=deceased).exists()

    @pytest.mark.django_db
    def test_muscular_agent_with_weak_relationship_receives_nothing(self, sim_with_zone):
        """High `Agent.strength`, but the `Relationship.strength` to the
        deceased is at/under the 0.6 threshold -- still no memory.
        """
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        muscular_acquaintance = _make_agent(sim, zone, "MuscularAcquaintance", strength=0.95)
        Relationship.objects.create(
            agent_from=deceased,
            agent_to=muscular_acquaintance,
            relation_type=Relationship.RelationType.PROFESSIONAL,
            strength=0.5,
            since_tick=0,
        )

        generate_mourning_memories(deceased, tick=sim.current_tick)

        assert not Memory.objects.filter(
            agent=muscular_acquaintance, origin_agent=deceased
        ).exists()

    @pytest.mark.django_db
    def test_frail_agent_with_strong_relationship_receives_memory(self, sim_with_zone):
        """The discriminating case: LOW `Agent.strength` (0.1, frail) but
        a `Relationship.strength` of 0.8 to the deceased -- this is the
        close friend the cascade must reach. An implementation that
        mistakenly filters on `Agent.strength` instead of
        `Relationship.strength` fails this test.
        """
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        frail_close_friend = _make_agent(sim, zone, "FrailCloseFriend", strength=0.1)
        Relationship.objects.create(
            agent_from=deceased,
            agent_to=frail_close_friend,
            relation_type=Relationship.RelationType.FRIENDSHIP,
            strength=0.8,
            since_tick=0,
        )

        generate_mourning_memories(deceased, tick=sim.current_tick)

        assert Memory.objects.filter(agent=frail_close_friend, origin_agent=deceased).exists()


class TestGenerateMourningMemoriesDedup:
    """An agent qualifying under more than one recipient category gets
    exactly ONE memory, never one per category (design spec Sezione 5,
    "un ricordo per destinatario").
    """

    @pytest.mark.django_db
    def test_child_who_is_also_a_strong_tie_receives_exactly_one_memory(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        child = _make_agent(sim, zone, "Child", parent_agent=deceased, birth_tick=5)
        Relationship.objects.create(
            agent_from=deceased,
            agent_to=child,
            relation_type=Relationship.RelationType.FAMILY,
            strength=0.9,
            since_tick=0,
        )

        generate_mourning_memories(deceased, tick=sim.current_tick)

        assert Memory.objects.filter(agent=child, origin_agent=deceased).count() == 1


class TestGenerateMourningMemoriesNoPropagation:
    """This function only creates the direct, first-hand memories for its
    three recipient categories -- it does not itself carry the death to
    socially-distant agents (that is the existing per-tick
    `propagate_information` system's job, run later, not from here).
    """

    @pytest.mark.django_db
    def test_socially_distant_zone_mate_receives_nothing(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        zone_mate = _make_agent(sim, zone, "ZoneMateNoTie")

        generate_mourning_memories(deceased, tick=sim.current_tick)

        assert not Memory.objects.filter(agent=zone_mate, origin_agent=deceased).exists()


class TestGenerateMourningMemoriesNoSaveOnDeceased:
    """The function creates NEW `Memory` rows (persistence of new rows is
    this function's job -- precedent: `transfer_loans_as_lender` persists
    `Loan` updates), but it must never call `.save()` on the passed
    `deceased` instance itself.
    """

    @pytest.mark.django_db
    def test_never_saves_the_deceased_instance(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        partner = _make_agent(sim, zone, "Partner")
        form_couple(deceased, partner, formed_at_tick=1)

        # Mutated only in memory -- if the function ever called
        # deceased.save(), this would leak into the database.
        deceased.name = "MutatedInMemoryOnly"

        generate_mourning_memories(deceased, tick=sim.current_tick)

        persisted = Agent.objects.get(id=deceased.id)
        assert persisted.name == "Deceased"


# ---------------------------------------------------------------------------
# process_inheritance_batch (Plan 3, T028/T029, user story 3 -- the
# death-path orchestrator). Design spec Sezione 5: per deceased, calls
# `dissolve_on_death` (D1), settles the estate through
# `resolve_heirs` -> `apply_estate_tax` -> `distribute_estate`, credits
# heirs' wealth and zeroes the deceased's, transfers active lender-side
# loans, assigns caretakers to now-orphaned minors, generates mourning
# memories, and emits one `DemographyEvent` (`INHERITANCE_TRANSFER`) per
# actual heir transfer.
#
# PRECONDITION, load-bearing for every test below: every agent in
# `deceased_agents` is passed in ALREADY `is_alive=False` (and, where
# relevant, `death_tick` already set) -- the caller (Plan 4's mortality
# step) sets this BEFORE calling `process_inheritance_batch`, never this
# function itself. This is the resolution of the apparent MISS-5 chaining
# puzzle: since `resolve_heirs`'s every category already filters
# `is_alive=True`, a same-tick-dead intermediate is mechanically excluded
# from being anyone's heir -- no suppression flag or special-cased
# recursion is needed, and none should be invented.
#
# FAMILY-TOPOLOGY NOTE (read before extending these tests): the coordinator
# brief's illustrative "grandfather / father / grandson" chain describes
# the OBSERVABLE arithmetic (two independent, separately-taxed transfers
# landing on one living heir) rather than a literal three-generation
# lineage `resolve_heirs` could actually traverse -- `resolve_heirs`'s own
# ladder (spouse, children, siblings, extended_family) never walks down
# to a deceased's grandchildren; "extended_family" reaches the deceased's
# OWN grandparents' descendants (aunts/uncles/cousins), never descendants
# of the deceased's own children. The tests below therefore build the
# "living heir inherits from two same-tick decedents" case as a shared
# living CHILD of two decedents (one on each parentage FK), and the
# "father already dead, estate falls to the next living category" case as
# ANOTHER living child of the same decedent (the same-generation fallback
# `resolve_heirs`'s own "children" category actually provides), not as a
# literal grandchild. Flagged explicitly rather than silently invented --
# see the T028 report's Doubts section for the full reasoning.
#
# `process_inheritance_batch` does not exist yet (implemented in T029);
# the import above therefore fails at collection time with "cannot import
# name 'process_inheritance_batch'", this file's established RED-first
# signal (see e.g. T016/T018/T020/T023/T024/T026's own RED commits).


def _set_demography_template(sim, template_name: str) -> None:
    """Point `sim.config["demography_template"]` at `template_name`.

    Mirrors `apply_inheritance_at_birth`'s own
    `simulation.config.get("demography_template", ...)` lookup -- the
    established convention this module uses to resolve which era template
    a Simulation-scoped call reads. Sets it both in memory (what a
    function reading `simulation.config` directly off the passed instance
    sees immediately, no extra query) and persisted (defensive, in case a
    future implementation re-fetches `simulation` from the database).
    """
    sim.config = {"demography_template": template_name}
    sim.save(update_fields=["config"])


class TestProcessInheritanceBatchNoIntraTickChaining:
    """Fix MISS-5, same-tick case (design spec Sezione 5): a deceased's own
    child who ALSO died in this same batch is never a bequest conduit --
    `resolve_heirs`'s `is_alive=True` filter excludes them exactly like it
    would exclude anyone else already dead. PRECONDITION: both agents
    below are constructed already `is_alive=False`, as `deceased_agents`
    always arrives.
    """

    @pytest.mark.django_db
    def test_dead_child_in_batch_receives_nothing_full_estate_goes_to_treasury(
        self, sim_with_government
    ):
        sim, zone, government = sim_with_government
        _set_demography_template(sim, "industrial")
        template = load_template("industrial")
        rate = template["economic_inheritance"]["estate_tax_rate"]

        grandfather = _make_agent(
            sim, zone, "Grandfather", is_alive=False, wealth=1000.0, age=90, birth_tick=-400
        )
        father = _make_agent(
            sim,
            zone,
            "Father",
            parent_agent=grandfather,
            is_alive=False,
            wealth=0.0,
            age=60,
            birth_tick=-300,
        )

        process_inheritance_batch(sim, tick=50, deceased_agents=[grandfather, father])

        father.refresh_from_db()
        grandfather.refresh_from_db()
        assert father.wealth == pytest.approx(0.0, abs=_CONSERVATION_TOLERANCE)
        assert grandfather.wealth == pytest.approx(0.0, abs=_CONSERVATION_TOLERANCE)

        assert not DemographyEvent.objects.filter(
            simulation=sim,
            event_type=DemographyEvent.EventType.INHERITANCE_TRANSFER,
            primary_agent=grandfather,
            secondary_agent=father,
        ).exists()

        # No living heir at all (father excluded, no siblings, no extended
        # family) -- distribute_estate's own documented "empty allocation
        # -> route the entire inheritable remainder to the treasury"
        # contract means BOTH the tax leg and the remainder land in the
        # treasury, summing to the full pre-tax estate. Currency-agnostic
        # on purpose: neither the settled contract nor the codebase
        # declares a canonical currency code for this orchestrator (every
        # existing apply_estate_tax test hardcodes an illustrative "USD"),
        # so summing every currency key sidesteps guessing T029's choice.
        government.refresh_from_db()
        assert sum(government.government_treasury.values()) == pytest.approx(
            1000.0, abs=_CONSERVATION_TOLERANCE
        )
        # Self-check that the rate is genuinely non-zero, or the test
        # would not distinguish "taxed once" from "never taxed".
        assert rate > 0.0


class TestProcessInheritanceBatchTwoIndependentTransfersToOneHeir:
    """The real chain case (design spec Sezione 5): a living heir who
    qualifies as a direct heir of TWO different same-tick decedents
    receives TWO separate transfers, each taxed once against its OWN
    source estate -- never a single combined transfer taxed once against
    the sum, and never taxed twice on either leg. See the FAMILY-TOPOLOGY
    NOTE above for why the shared heir is built as a common child (one
    parentage FK per decedent) rather than a literal grandchild.
    """

    @pytest.mark.django_db
    def test_heir_receives_two_separately_taxed_transfers_summing_correctly(
        self, sim_with_government
    ):
        sim, zone, government = sim_with_government
        _set_demography_template(sim, "industrial")
        template = load_template("industrial")
        rate = template["economic_inheritance"]["estate_tax_rate"]

        grandfather = _make_agent(
            sim, zone, "Grandfather", is_alive=False, wealth=1000.0, age=90, birth_tick=-400
        )
        father = _make_agent(
            sim, zone, "Father", is_alive=False, wealth=500.0, age=60, birth_tick=-300
        )
        grandson = _make_agent(
            sim,
            zone,
            "Grandson",
            parent_agent=grandfather,
            other_parent_agent=father,
            wealth=0.0,
            birth_tick=-30,
        )

        process_inheritance_batch(sim, tick=50, deceased_agents=[grandfather, father])

        grandson.refresh_from_db()
        grandfather.refresh_from_db()
        father.refresh_from_db()
        government.refresh_from_db()

        inheritable_from_grandfather = 1000.0 * (1 - rate)
        inheritable_from_father = 500.0 * (1 - rate)
        expected_total_tax = 1000.0 * rate + 500.0 * rate

        assert grandson.wealth == pytest.approx(
            inheritable_from_grandfather + inheritable_from_father, abs=_CONSERVATION_TOLERANCE
        )
        assert grandfather.wealth == pytest.approx(0.0, abs=_CONSERVATION_TOLERANCE)
        assert father.wealth == pytest.approx(0.0, abs=_CONSERVATION_TOLERANCE)
        assert sum(government.government_treasury.values()) == pytest.approx(
            expected_total_tax, abs=_CONSERVATION_TOLERANCE
        )

        transfer_events = DemographyEvent.objects.filter(
            simulation=sim,
            event_type=DemographyEvent.EventType.INHERITANCE_TRANSFER,
            secondary_agent=grandson,
        )
        assert transfer_events.count() == 2

        event_from_grandfather = transfer_events.get(primary_agent=grandfather)
        event_from_father = transfer_events.get(primary_agent=father)
        assert event_from_grandfather.payload["assets"]["cash"] == pytest.approx(
            inheritable_from_grandfather, abs=_CONSERVATION_TOLERANCE
        )
        assert event_from_father.payload["assets"]["cash"] == pytest.approx(
            inheritable_from_father, abs=_CONSERVATION_TOLERANCE
        )


class TestProcessInheritanceBatchCrossTickMiss5:
    """Fix MISS-5, cross-tick case: a father who died in an EARLIER tick
    (already `is_alive=False`, `death_tick` before the current tick, and
    NOT included in this batch's `deceased_agents`) is never a bequest
    conduit either -- the estate falls through to the next living
    category exactly as if he had never existed. See the FAMILY-TOPOLOGY
    NOTE above: the fallback recipient here is a second living child of
    the same decedent (the same-generation category `resolve_heirs`
    actually provides), not a literal grandchild.
    """

    @pytest.mark.django_db
    def test_earlier_tick_dead_child_excluded_falls_to_next_living_child(self, sim_with_government):
        sim, zone, government = sim_with_government
        _set_demography_template(sim, "industrial")
        template = load_template("industrial")
        rate = template["economic_inheritance"]["estate_tax_rate"]

        grandfather = _make_agent(
            sim, zone, "Grandfather", is_alive=False, wealth=1000.0, age=90, birth_tick=-400
        )
        father = _make_agent(
            sim,
            zone,
            "Father",
            parent_agent=grandfather,
            is_alive=False,
            death_tick=10,
            wealth=0.0,
            age=60,
            birth_tick=-300,
        )
        second_child = _make_agent(
            sim, zone, "SecondChild", parent_agent=grandfather, wealth=0.0, birth_tick=-250
        )

        # father died at tick 10 -- strictly before this batch's tick 50 --
        # and is deliberately NOT in deceased_agents.
        process_inheritance_batch(sim, tick=50, deceased_agents=[grandfather])

        father.refresh_from_db()
        second_child.refresh_from_db()
        government.refresh_from_db()

        assert father.wealth == pytest.approx(0.0, abs=_CONSERVATION_TOLERANCE)
        expected_inheritable = 1000.0 * (1 - rate)
        assert second_child.wealth == pytest.approx(
            expected_inheritable, abs=_CONSERVATION_TOLERANCE
        )
        assert not DemographyEvent.objects.filter(
            simulation=sim,
            event_type=DemographyEvent.EventType.INHERITANCE_TRANSFER,
            primary_agent=grandfather,
            secondary_agent=father,
        ).exists()
        # Taxed exactly once (the single actual transfer to second_child),
        # never re-applied on account of father's exclusion.
        assert sum(government.government_treasury.values()) == pytest.approx(
            1000.0 * rate, abs=_CONSERVATION_TOLERANCE
        )


class TestProcessInheritanceBatchEventPayload:
    """`DemographyEvent` shape for an actual heir transfer (design spec
    Sezione 5, DemographyEvent payload schemas, `inheritance_transfer`
    row): `event_type=INHERITANCE_TRANSFER`, `simulation`, `tick`,
    `primary_agent=deceased`, `secondary_agent=heir`, and a payload
    carrying `deceased_id`, `heir_id`, `assets: {cash, property_ids,
    loans_as_lender}`, `estate_tax_applied`, `rule_used`.

    `estate_tax_applied` and `rule_used`'s exact meaning is not specified
    anywhere upstream of this task (the design spec names the keys but not
    their semantics) -- this test PINS them explicitly: `estate_tax_applied`
    is the absolute tax AMOUNT (a float) subtracted from this transfer's
    own source estate, and `rule_used` is the era template's
    `economic_inheritance.rule` string. `property_ids` / `loans_as_lender`
    are asserted only to be lists, per the settled contract leaving their
    population to T029.
    """

    @pytest.mark.django_db
    def test_event_carries_the_full_payload_shape(self, sim_with_government):
        sim, zone, government = sim_with_government
        _set_demography_template(sim, "industrial")
        template = load_template("industrial")
        rate = template["economic_inheritance"]["estate_tax_rate"]
        rule = template["economic_inheritance"]["rule"]

        deceased = _make_agent(
            sim, zone, "Deceased", is_alive=False, wealth=1000.0, age=70, birth_tick=-300
        )
        heir = _make_agent(sim, zone, "Heir", parent_agent=deceased, wealth=0.0, birth_tick=-30)

        process_inheritance_batch(sim, tick=50, deceased_agents=[deceased])

        event = DemographyEvent.objects.get(
            simulation=sim,
            event_type=DemographyEvent.EventType.INHERITANCE_TRANSFER,
            primary_agent=deceased,
            secondary_agent=heir,
        )
        assert event.tick == 50

        payload = event.payload
        assert "deceased_id" in payload
        assert "heir_id" in payload
        assert "assets" in payload
        assert "estate_tax_applied" in payload
        assert "rule_used" in payload
        assert payload["deceased_id"] == deceased.id
        assert payload["heir_id"] == heir.id
        assert payload["rule_used"] == rule

        expected_tax = 1000.0 * rate
        expected_cash = 1000.0 - expected_tax
        assert payload["estate_tax_applied"] == pytest.approx(
            expected_tax, abs=_CONSERVATION_TOLERANCE
        )

        assets = payload["assets"]
        assert "cash" in assets
        assert "property_ids" in assets
        assert "loans_as_lender" in assets
        assert assets["cash"] == pytest.approx(expected_cash, abs=_CONSERVATION_TOLERANCE)
        assert isinstance(assets["property_ids"], list)
        assert isinstance(assets["loans_as_lender"], list)


class TestProcessInheritanceBatchOrderingC3:
    """Fix C-3: the batch processes deceased agents oldest (`age`
    descending) first, `id` ascending as the deterministic tiebreak for
    equal age -- the Simultaneous Death Act convention. Observed via the
    ORDER of the emitted `DemographyEvent` rows (queried by `id`, which
    reflects creation/processing order).
    """

    @pytest.mark.django_db
    def test_events_are_emitted_oldest_first_regardless_of_input_order(self, sim_with_government):
        sim, zone, government = sim_with_government
        _set_demography_template(sim, "industrial")

        older = _make_agent(
            sim, zone, "Older", is_alive=False, wealth=100.0, age=85, birth_tick=-500
        )
        _make_agent(sim, zone, "OlderHeir", parent_agent=older, wealth=0.0, birth_tick=-100)
        younger = _make_agent(
            sim, zone, "Younger", is_alive=False, wealth=100.0, age=40, birth_tick=-200
        )
        _make_agent(sim, zone, "YoungerHeir", parent_agent=younger, wealth=0.0, birth_tick=-50)

        # Deliberately passed younger-first -- the OPPOSITE of the required
        # processing order -- so this test cannot pass by accident of
        # input order matching the expected output order.
        process_inheritance_batch(sim, tick=50, deceased_agents=[younger, older])

        events = list(
            DemographyEvent.objects.filter(
                simulation=sim, event_type=DemographyEvent.EventType.INHERITANCE_TRANSFER
            ).order_by("id")
        )
        assert [event.primary_agent_id for event in events] == [older.id, younger.id]

    @pytest.mark.django_db
    def test_equal_age_tiebreak_is_id_ascending(self, sim_with_government):
        sim, zone, government = sim_with_government
        _set_demography_template(sim, "industrial")

        first_created = _make_agent(
            sim, zone, "FirstCreated", is_alive=False, wealth=100.0, age=50, birth_tick=-200
        )
        _make_agent(sim, zone, "FirstHeir", parent_agent=first_created, wealth=0.0, birth_tick=-50)
        second_created = _make_agent(
            sim, zone, "SecondCreated", is_alive=False, wealth=100.0, age=50, birth_tick=-200
        )
        _make_agent(
            sim, zone, "SecondHeir", parent_agent=second_created, wealth=0.0, birth_tick=-50
        )
        assert first_created.id < second_created.id  # self-check

        process_inheritance_batch(sim, tick=50, deceased_agents=[second_created, first_created])

        events = list(
            DemographyEvent.objects.filter(
                simulation=sim, event_type=DemographyEvent.EventType.INHERITANCE_TRANSFER
            ).order_by("id")
        )
        assert [event.primary_agent_id for event in events] == [
            first_created.id,
            second_created.id,
        ]


class TestProcessInheritanceBatchCoupleDissolution:
    """Composition (design spec Sezione 5): the batch calls
    `dissolve_on_death` per deceased (decision D1), observable as the
    `Couple` row's own state -- including fix MISS-4, both partners of one
    couple dying in the same batch.
    """

    @pytest.mark.django_db
    def test_single_partner_death_dissolves_couple_with_death_reason(self, sim_with_government):
        sim, zone, government = sim_with_government
        _set_demography_template(sim, "industrial")

        deceased = _make_agent(
            sim, zone, "Deceased", is_alive=False, wealth=0.0, age=70, birth_tick=-300
        )
        partner = _make_agent(sim, zone, "Partner", wealth=0.0, birth_tick=-290)
        form_couple(deceased, partner, formed_at_tick=1)

        process_inheritance_batch(sim, tick=50, deceased_agents=[deceased])

        couple = Couple.objects.get(simulation=sim)
        assert couple.dissolved_at_tick == 50
        assert couple.dissolution_reason == Couple.DissolutionReason.DEATH
        if deceased.id < partner.id:
            assert couple.agent_a_id is None
            assert couple.agent_a_name_snapshot == deceased.name
            assert couple.agent_b_id == partner.id
        else:
            assert couple.agent_b_id is None
            assert couple.agent_b_name_snapshot == deceased.name
            assert couple.agent_a_id == partner.id

    @pytest.mark.django_db
    def test_miss4_both_partners_die_in_same_batch_couple_dissolved_once(self, sim_with_government):
        sim, zone, government = sim_with_government
        _set_demography_template(sim, "industrial")

        partner_one = _make_agent(
            sim, zone, "PartnerOne", is_alive=False, wealth=0.0, age=70, birth_tick=-300
        )
        partner_two = _make_agent(
            sim, zone, "PartnerTwo", is_alive=False, wealth=0.0, age=68, birth_tick=-290
        )
        form_couple(partner_one, partner_two, formed_at_tick=1)

        process_inheritance_batch(sim, tick=50, deceased_agents=[partner_one, partner_two])

        assert Couple.objects.filter(simulation=sim).count() == 1
        couple = Couple.objects.get(simulation=sim)
        assert couple.agent_a_id is None
        assert couple.agent_b_id is None
        assert couple.dissolved_at_tick == 50
        assert couple.dissolution_reason == Couple.DissolutionReason.DEATH
        assert {couple.agent_a_name_snapshot, couple.agent_b_name_snapshot} == {
            partner_one.name,
            partner_two.name,
        }


class TestProcessInheritanceBatchMourningMemories:
    """Composition: the batch calls `generate_mourning_memories` per
    deceased, observable as `Memory` rows for survivors.
    """

    @pytest.mark.django_db
    def test_batch_generates_a_mourning_memory_for_the_surviving_partner(self, sim_with_government):
        sim, zone, government = sim_with_government
        _set_demography_template(sim, "industrial")

        deceased = _make_agent(
            sim, zone, "Deceased", is_alive=False, wealth=0.0, age=70, birth_tick=-300
        )
        partner = _make_agent(sim, zone, "Partner", wealth=0.0, birth_tick=-290)
        form_couple(deceased, partner, formed_at_tick=1)

        process_inheritance_batch(sim, tick=50, deceased_agents=[deceased])

        assert Memory.objects.filter(agent=partner, origin_agent=deceased).exists()


class TestProcessInheritanceBatchOrphanCaretaker:
    """Composition: the batch calls `assign_orphan_caretaker` for a minor
    newly orphaned by this same batch, observable as the minor's
    persisted `caretaker_agent`.
    """

    @pytest.mark.django_db
    def test_batch_assigns_a_caretaker_to_a_newly_orphaned_minor(self, sim_with_government):
        sim, zone, government = sim_with_government
        _set_demography_template(sim, "industrial")

        mother = _make_agent(
            sim, zone, "Mother", is_alive=False, wealth=0.0, age=40, birth_tick=-400
        )
        father = _make_agent(
            sim, zone, "Father", is_alive=False, wealth=0.0, age=42, birth_tick=-420
        )
        sibling = _make_agent(
            sim,
            zone,
            "Sibling",
            parent_agent=mother,
            other_parent_agent=father,
            wealth=0.0,
            birth_tick=-100,
        )
        minor = _make_agent(
            sim,
            zone,
            "Minor",
            parent_agent=mother,
            other_parent_agent=father,
            age=10,
            wealth=0.0,
            birth_tick=-10,
        )

        process_inheritance_batch(sim, tick=50, deceased_agents=[mother, father])

        persisted_minor = Agent.objects.get(id=minor.id)
        assert persisted_minor.caretaker_agent_id == sibling.id


class TestProcessInheritanceBatchLoanTransfer:
    """Composition: the batch calls `transfer_loans_as_lender` per
    deceased, observable as the reassigned `Loan.lender`.
    """

    @pytest.mark.django_db
    def test_batch_transfers_an_active_lender_side_loan_to_the_living_heir(
        self, sim_with_government
    ):
        sim, zone, government = sim_with_government
        _set_demography_template(sim, "industrial")

        deceased = _make_agent(
            sim, zone, "Deceased", is_alive=False, wealth=0.0, age=70, birth_tick=-300
        )
        heir = _make_agent(sim, zone, "Heir", parent_agent=deceased, wealth=0.0, birth_tick=-30)
        borrower = _make_agent(sim, zone, "Borrower", wealth=0.0, birth_tick=-30)
        loan = _make_loan(sim, borrower, lender=deceased)

        process_inheritance_batch(sim, tick=50, deceased_agents=[deceased])

        loan.refresh_from_db()
        assert loan.lender_id == heir.id


class TestProcessInheritanceBatchPersistence:
    """Unlike this module's pure resolvers, `process_inheritance_batch` IS
    the orchestrated entry point and DOES persist: heir wealth credits and
    the deceased's zeroed wealth must survive a FRESH query (`Agent.
    objects.get`), not merely live on the in-memory instances the caller
    happens to still hold.
    """

    @pytest.mark.django_db
    def test_heir_and_deceased_wealth_are_persisted_not_only_in_memory(self, sim_with_government):
        sim, zone, government = sim_with_government
        _set_demography_template(sim, "industrial")
        template = load_template("industrial")
        rate = template["economic_inheritance"]["estate_tax_rate"]

        deceased = _make_agent(
            sim, zone, "Deceased", is_alive=False, wealth=1000.0, age=70, birth_tick=-300
        )
        heir = _make_agent(sim, zone, "Heir", parent_agent=deceased, wealth=0.0, birth_tick=-30)

        process_inheritance_batch(sim, tick=50, deceased_agents=[deceased])

        persisted_deceased = Agent.objects.get(id=deceased.id)
        persisted_heir = Agent.objects.get(id=heir.id)

        assert persisted_deceased.wealth == pytest.approx(0.0, abs=_CONSERVATION_TOLERANCE)
        assert persisted_heir.wealth == pytest.approx(
            1000.0 * (1 - rate), abs=_CONSERVATION_TOLERANCE
        )


class TestProcessInheritanceBatchEmptyBatch:
    """An empty batch is a no-op: no events, no exceptions."""

    @pytest.mark.django_db
    def test_empty_batch_creates_no_events_and_does_not_raise(self, sim_with_government):
        sim, zone, government = sim_with_government
        _set_demography_template(sim, "industrial")

        process_inheritance_batch(sim, tick=50, deceased_agents=[])

        assert not DemographyEvent.objects.filter(simulation=sim).exists()
