"""Unit tests for epocha/apps/demography/couple.py.

Covers:
- _ordered_pair: canonical ordering, error cases
- form_couple: creates a Couple satisfying the DB constraint
- is_in_active_couple / active_couple_for: pre- and post-dissolution
- homogamy_score: qualitative sign checks
- stable_matching: symmetric 3x3 produces 3 stable pairs, asymmetric 3x2 produces 2
- resolve_pair_bond_intents: mutual consent, implicit consent (monkeypatch), skip on
  already-coupled, arranged marriage payload
- resolve_separate_intents: divorce_enabled=True dissolves, divorce_enabled=False is no-op
- dissolve_on_death: name snapshot captured, FK nulled, correct dissolution metadata
- dissolve_on_death: both partners dying in the same tick capture both snapshots
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent, DecisionLog
from epocha.apps.demography.couple import (
    _ordered_pair,
    active_couple_for,
    dissolve_on_death,
    form_couple,
    homogamy_score,
    is_in_active_couple,
    resolve_pair_bond_intents,
    resolve_separate_intents,
    stable_matching,
)
from epocha.apps.demography.models import Couple
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World, Zone

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sim_with_zone(db):
    """Minimal scaffolding: user, simulation, world, zone."""
    user = User.objects.create_user(
        email="couple@epocha.dev",
        username="coupleuser",
        password="pass1234",
    )
    sim = Simulation.objects.create(
        name="CoupleTest",
        seed=42,
        owner=user,
        current_tick=5,
    )
    world = World.objects.create(simulation=sim, stability_index=0.7)
    zone = Zone.objects.create(
        world=world,
        name="CoupleZone",
        zone_type="commercial",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    return sim, zone


# Ticks in a year on the default 24-hour world, at the acceleration of 1.0
# every shipped era declares.
TICKS_PER_YEAR = 365


def _make_agent(sim, zone, name, **kwargs):
    """Helper: create an Agent with sensible defaults.

    `birth_tick` is derived from `age` unless given, so the two agree. They
    used to disagree -- `birth_tick=0` against `age=25` on a simulation at
    tick 5 -- which made every agent here five days old by `age_in_years`,
    the canonical reading, and would have made any age rule in the resolver
    untestable from this file.
    """
    defaults = dict(
        role="farmer",
        location=Point(50, 50),
        health=1.0,
        wealth=100.0,
        age=25,
        mood=0.5,
        education_level=0.5,
        social_class="working",
        gender=Agent.Gender.FEMALE,
    )
    defaults.update(kwargs)
    defaults.setdefault("birth_tick", sim.current_tick - defaults["age"] * TICKS_PER_YEAR)
    return Agent.objects.create(simulation=sim, name=name, zone=zone, **defaults)


def _decision_log(sim, agent, tick, action, target=None, **extra):
    """Create a DecisionLog row with output_decision as a JSON blob."""
    payload = {"action": action, "reason": "test"}
    if target is not None:
        payload["target"] = target
    payload.update(extra)
    return DecisionLog.objects.create(
        simulation=sim,
        agent=agent,
        tick=tick,
        input_context="{}",
        output_decision=json.dumps(payload),
        llm_model="test-model",
        cost_tokens=0,
    )


# ---------------------------------------------------------------------------
# _ordered_pair
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ordered_pair_lower_id_first(sim_with_zone):
    """_ordered_pair must return (lower_pk_agent, higher_pk_agent)."""
    sim, zone = sim_with_zone
    # Create in order so a.pk < b.pk is guaranteed by insertion sequence
    a = _make_agent(sim, zone, "Alice")
    b = _make_agent(sim, zone, "Bob")
    assert a.pk < b.pk

    first, second = _ordered_pair(a, b)
    assert first.pk < second.pk
    assert first.pk == a.pk

    # Reversed input must still yield the same canonical order
    first2, second2 = _ordered_pair(b, a)
    assert first2.pk == a.pk
    assert second2.pk == b.pk


@pytest.mark.django_db
def test_ordered_pair_raises_on_same_agent(sim_with_zone):
    """_ordered_pair must raise ValueError when both arguments are the same agent."""
    sim, zone = sim_with_zone
    a = _make_agent(sim, zone, "Solo")
    with pytest.raises(ValueError, match="itself"):
        _ordered_pair(a, a)


def test_ordered_pair_raises_on_unsaved_agents():
    """_ordered_pair must raise ValueError when either agent has no PK."""
    # Build unsaved Agent instances (no .save() called)
    a = Agent(name="Unsaved1")
    b = Agent(name="Unsaved2")
    with pytest.raises(ValueError, match="primary key"):
        _ordered_pair(a, b)


# ---------------------------------------------------------------------------
# form_couple
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_form_couple_canonical_ordering(sim_with_zone):
    """form_couple must persist agent_a.pk < agent_b.pk regardless of call order."""
    sim, zone = sim_with_zone
    a = _make_agent(sim, zone, "Cara")
    b = _make_agent(sim, zone, "Dario")
    assert a.pk < b.pk

    # Pass agents in reverse order — form_couple must still canonicalize
    couple = form_couple(b, a, formed_at_tick=5)
    couple.refresh_from_db()
    assert couple.agent_a_id == a.pk
    assert couple.agent_b_id == b.pk


@pytest.mark.django_db
def test_form_couple_default_type(sim_with_zone):
    """form_couple without explicit couple_type defaults to 'monogamous'."""
    sim, zone = sim_with_zone
    a = _make_agent(sim, zone, "Eva")
    b = _make_agent(sim, zone, "Fabio")
    couple = form_couple(a, b, formed_at_tick=3)
    assert couple.couple_type == Couple.CoupleType.MONOGAMOUS


# ---------------------------------------------------------------------------
# is_in_active_couple / active_couple_for
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_is_in_active_couple_pre_dissolution(sim_with_zone):
    """Both partners must be reported as in an active couple after creation."""
    sim, zone = sim_with_zone
    a = _make_agent(sim, zone, "Gia")
    b = _make_agent(sim, zone, "Hugo")
    form_couple(a, b, formed_at_tick=1)
    assert is_in_active_couple(a) is True
    assert is_in_active_couple(b) is True


@pytest.mark.django_db
def test_is_in_active_couple_post_dissolution(sim_with_zone):
    """After dissolution, neither partner must be reported as in an active couple."""
    sim, zone = sim_with_zone
    a = _make_agent(sim, zone, "Irina")
    b = _make_agent(sim, zone, "James")
    couple = form_couple(a, b, formed_at_tick=1)
    couple.dissolved_at_tick = 10
    couple.dissolution_reason = Couple.DissolutionReason.SEPARATE
    couple.save(update_fields=["dissolved_at_tick", "dissolution_reason"])

    assert is_in_active_couple(a) is False
    assert is_in_active_couple(b) is False


@pytest.mark.django_db
def test_active_couple_for_returns_correct_object(sim_with_zone):
    """active_couple_for must return the right Couple instance for each partner."""
    sim, zone = sim_with_zone
    a = _make_agent(sim, zone, "Kenji")
    b = _make_agent(sim, zone, "Luna")
    couple = form_couple(a, b, formed_at_tick=2)

    assert active_couple_for(a).pk == couple.pk
    assert active_couple_for(b).pk == couple.pk


@pytest.mark.django_db
def test_active_couple_for_returns_none_when_dissolved(sim_with_zone):
    """active_couple_for must return None after dissolution."""
    sim, zone = sim_with_zone
    a = _make_agent(sim, zone, "Marco")
    b = _make_agent(sim, zone, "Nadia")
    couple = form_couple(a, b, formed_at_tick=1)
    couple.dissolved_at_tick = 3
    couple.dissolution_reason = Couple.DissolutionReason.DEATH
    couple.save(update_fields=["dissolved_at_tick", "dissolution_reason"])

    assert active_couple_for(a) is None


# ---------------------------------------------------------------------------
# homogamy_score
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_homogamy_score_higher_for_similar_pair(sim_with_zone):
    """A same-class, similar-age, similar-education pair must score higher than
    a pair differing on all three dimensions (Kalmijn 1998 prediction)."""
    sim, zone = sim_with_zone
    # Similar pair: same social class, close age and education
    a1 = _make_agent(sim, zone, "Similar1", age=25, education_level=0.5, social_class="working")
    a2 = _make_agent(sim, zone, "Similar2", age=26, education_level=0.5, social_class="working")
    # Disparate pair: different social class, large age gap, different education
    b1 = _make_agent(sim, zone, "Disparate1", age=25, education_level=0.1, social_class="working")
    b2 = _make_agent(sim, zone, "Disparate2", age=50, education_level=0.9, social_class="elite")

    weights = {"w_class": 0.4, "w_edu": 0.25, "w_age": 0.20, "w_relationship": 0.15}
    score_similar = homogamy_score(a1, a2, weights)
    score_disparate = homogamy_score(b1, b2, weights)

    assert score_similar > score_disparate, (
        f"Similar score {score_similar:.3f} should exceed disparate {score_disparate:.3f}"
    )


# ---------------------------------------------------------------------------
# stable_matching
# ---------------------------------------------------------------------------


def test_stable_matching_3x3_produces_3_pairs():
    """Gale-Shapley with equal-sized sides must produce a complete matching (3 pairs)."""
    # Use simple integers as stand-ins for agents; score_fn returns a fixed table
    # P = proposers, R = respondents; scores are arbitrary but distinct
    score_table = {
        (0, "A"): 0.9,
        (0, "B"): 0.6,
        (0, "C"): 0.3,
        (1, "A"): 0.5,
        (1, "B"): 0.8,
        (1, "C"): 0.4,
        (2, "A"): 0.3,
        (2, "B"): 0.4,
        (2, "C"): 0.9,
    }
    pairs = stable_matching(
        proposers=[0, 1, 2],
        respondents=["A", "B", "C"],
        score_fn=lambda p, r: score_table[(p, r)],
    )
    assert len(pairs) == 3
    proposers_matched = {p for p, _ in pairs}
    respondents_matched = {r for _, r in pairs}
    assert proposers_matched == {0, 1, 2}
    assert respondents_matched == {"A", "B", "C"}


def test_stable_matching_3x3_is_stable():
    """The Gale-Shapley output must be stable: no (p, r) pair both prefer each other
    over their matched partners (Gale & Shapley 1962 Theorem 1)."""
    score_table = {
        (0, "A"): 0.9,
        (0, "B"): 0.6,
        (0, "C"): 0.3,
        (1, "A"): 0.5,
        (1, "B"): 0.8,
        (1, "C"): 0.4,
        (2, "A"): 0.3,
        (2, "B"): 0.4,
        (2, "C"): 0.9,
    }
    pairs = stable_matching(
        proposers=[0, 1, 2],
        respondents=["A", "B", "C"],
        score_fn=lambda p, r: score_table[(p, r)],
    )
    matched = dict(pairs)  # p -> r
    matched_rev = {r: p for p, r in pairs}  # r -> p

    for p in [0, 1, 2]:
        for r in ["A", "B", "C"]:
            if matched.get(p) == r:
                continue
            # Check: does p prefer r over matched[p]?
            p_prefers_r = score_table[(p, r)] > score_table[(p, matched[p])]
            # Does r prefer p over matched_rev[r]?
            r_prefers_p = score_table[(p, r)] > score_table[(matched_rev[r], r)]
            assert not (p_prefers_r and r_prefers_p), (
                f"Blocking pair found: proposer {p} and respondent {r} prefer each other "
                f"over their current matches — matching is not stable"
            )


def test_stable_matching_asymmetric_3_proposers_2_respondents():
    """With 3 proposers and 2 respondents, exactly 2 matches must be produced."""
    score_table = {
        (0, "X"): 0.8,
        (0, "Y"): 0.5,
        (1, "X"): 0.6,
        (1, "Y"): 0.9,
        (2, "X"): 0.4,
        (2, "Y"): 0.4,
    }
    pairs = stable_matching(
        proposers=[0, 1, 2],
        respondents=["X", "Y"],
        score_fn=lambda p, r: score_table[(p, r)],
    )
    assert len(pairs) == 2
    respondents_matched = {r for _, r in pairs}
    assert respondents_matched == {"X", "Y"}


# ---------------------------------------------------------------------------
# resolve_pair_bond_intents — mutual consent (all agents propose each other)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_resolve_pair_bond_mutual_consent_forms_couple(sim_with_zone):
    """Two agents who both pair_bond each other must get coupled.

    Uses pre_industrial_christian (implicit_mutual_consent=True) so the mutual
    branch is exercised regardless; the key check is that the couple is formed
    with the correct agent ordering.
    """
    sim, zone = sim_with_zone
    sim.config = {"demography_template": "pre_industrial_christian"}
    sim.save()
    sim.current_tick = 5
    sim.save()

    a = _make_agent(sim, zone, "Amelia")
    b = _make_agent(sim, zone, "Bruno", gender=Agent.Gender.MALE)

    # Both agents pair_bond each other at tick 4 (current tick is 5, resolver reads tick-1)
    _decision_log(sim, a, tick=4, action="pair_bond", target=b.name)
    _decision_log(sim, b, tick=4, action="pair_bond", target=a.name)

    import random

    formed = resolve_pair_bond_intents(sim, tick=5, rng=random.Random(42))

    assert len(formed) == 1
    couple = formed[0]
    assert couple.agent_a_id == min(a.pk, b.pk)
    assert couple.agent_b_id == max(a.pk, b.pk)


@pytest.mark.django_db
def test_resolve_pair_bond_implicit_consent_forms_couple(sim_with_zone):
    """With implicit_mutual_consent=True a one-sided proposal must form a couple.

    All existing templates have implicit_mutual_consent=True. We monkeypatch
    load_template to verify the implicit branch is active, then verify the
    couple is formed even though only one side proposed.
    """
    sim, zone = sim_with_zone
    sim.config = {"demography_template": "mock_implicit"}
    sim.save()
    sim.current_tick = 5
    sim.save()

    a = _make_agent(sim, zone, "Chiara")
    b = _make_agent(sim, zone, "Damiano", gender=Agent.Gender.MALE)

    # Only a proposes to b (no entry from b)
    _decision_log(sim, a, tick=4, action="pair_bond", target=b.name)

    implicit_template = {
        "couple": {
            "implicit_mutual_consent": True,
            "default_type": "monogamous",
            "divorce_enabled": False,
            "min_marriage_age_male": 16,
            "min_marriage_age_female": 14,
        }
    }

    import random

    with patch(
        "epocha.apps.demography.template_loader.load_template", return_value=implicit_template
    ):
        formed = resolve_pair_bond_intents(sim, tick=5, rng=random.Random(1))

    assert len(formed) == 1


@pytest.mark.django_db
def test_resolve_pair_bond_explicit_consent_requires_both(sim_with_zone):
    """With implicit_mutual_consent=False a one-sided proposal must NOT form a couple.

    No existing template has implicit_mutual_consent=False, so we monkeypatch
    load_template to force the explicit-consent path and verify it is respected.
    """
    sim, zone = sim_with_zone
    sim.config = {"demography_template": "mock_explicit"}
    sim.save()
    sim.current_tick = 5
    sim.save()

    a = _make_agent(sim, zone, "Elena")
    b = _make_agent(sim, zone, "Filippo", gender=Agent.Gender.MALE)

    # Only a proposes to b (no entry from b)
    _decision_log(sim, a, tick=4, action="pair_bond", target=b.name)

    explicit_template = {
        "couple": {
            "implicit_mutual_consent": False,
            "default_type": "monogamous",
            "divorce_enabled": False,
            "min_marriage_age_male": 16,
            "min_marriage_age_female": 14,
        }
    }

    import random

    with patch(
        "epocha.apps.demography.template_loader.load_template", return_value=explicit_template
    ):
        formed = resolve_pair_bond_intents(sim, tick=5, rng=random.Random(2))

    assert len(formed) == 0


@pytest.mark.django_db
def test_resolve_pair_bond_skips_already_coupled_agents(sim_with_zone):
    """resolve_pair_bond_intents must skip any agent that already has an active Couple."""
    sim, zone = sim_with_zone
    sim.config = {"demography_template": "pre_industrial_christian"}
    sim.save()
    sim.current_tick = 5
    sim.save()

    a = _make_agent(sim, zone, "Giovanna")
    b = _make_agent(sim, zone, "Hector", gender=Agent.Gender.MALE)
    c = _make_agent(sim, zone, "Iris")

    # a is already coupled to c
    form_couple(a, c, formed_at_tick=1)

    # b tries to pair_bond with a
    _decision_log(sim, b, tick=4, action="pair_bond", target=a.name)

    import random

    formed = resolve_pair_bond_intents(sim, tick=5, rng=random.Random(7))

    assert len(formed) == 0


@pytest.mark.django_db
def test_resolve_pair_bond_arranged_marriage_payload(sim_with_zone):
    """A parent proposing pair_bond with for_child payload must bond the named child.

    Goode (1963) §7: arranged marriages are initiated by a parent on behalf of
    a child. The resolver reattributes the intent from parent to child.
    """
    sim, zone = sim_with_zone
    sim.config = {"demography_template": "pre_industrial_christian"}
    sim.save()
    sim.current_tick = 5
    sim.save()

    parent = _make_agent(sim, zone, "Parent", age=50)
    child = _make_agent(sim, zone, "ChildAgent", age=20)
    match = _make_agent(sim, zone, "MatchAgent", age=22, gender=Agent.Gender.MALE)

    # Parent proposes on behalf of child toward match
    _decision_log(
        sim,
        parent,
        tick=4,
        action="pair_bond",
        target={"for_child": child.name, "match": match.name},
    )

    import random

    formed = resolve_pair_bond_intents(sim, tick=5, rng=random.Random(3))

    assert len(formed) == 1
    couple = formed[0]
    # child and match must be the actual partners
    partner_ids = {couple.agent_a_id, couple.agent_b_id}
    assert child.pk in partner_ids
    assert match.pk in partner_ids
    # parent must not be in the couple
    assert parent.pk not in partner_ids


# ---------------------------------------------------------------------------
# resolve_separate_intents
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_resolve_separate_divorce_enabled_dissolves_couple(sim_with_zone):
    """With divorce_enabled=True, a separate intent must dissolve the active couple.

    Uses modern_democracy template which has divorce_enabled=True.
    """
    sim, zone = sim_with_zone
    sim.config = {"demography_template": "modern_democracy"}
    sim.save()
    sim.current_tick = 10
    sim.save()

    a = _make_agent(sim, zone, "Jasmine")
    b = _make_agent(sim, zone, "Karl", gender=Agent.Gender.MALE)
    couple = form_couple(a, b, formed_at_tick=1)

    # a issues a separate intent at tick 9 (resolver reads tick-1 from current tick 10)
    _decision_log(sim, a, tick=9, action="separate")

    dissolved = resolve_separate_intents(sim, tick=10)

    assert len(dissolved) == 1
    couple.refresh_from_db()
    assert couple.dissolved_at_tick == 10
    assert couple.dissolution_reason == Couple.DissolutionReason.SEPARATE


@pytest.mark.django_db
def test_resolve_separate_divorce_disabled_is_noop(sim_with_zone):
    """With divorce_enabled=False, a separate intent must be silently ignored.

    Uses pre_industrial_christian template which has divorce_enabled=False.
    """
    sim, zone = sim_with_zone
    sim.config = {"demography_template": "pre_industrial_christian"}
    sim.save()
    sim.current_tick = 10
    sim.save()

    a = _make_agent(sim, zone, "Leila")
    b = _make_agent(sim, zone, "Matteo", gender=Agent.Gender.MALE)
    couple = form_couple(a, b, formed_at_tick=1)

    _decision_log(sim, a, tick=9, action="separate")

    dissolved = resolve_separate_intents(sim, tick=10)

    assert len(dissolved) == 0
    couple.refresh_from_db()
    assert couple.dissolved_at_tick is None


# ---------------------------------------------------------------------------
# dissolve_on_death
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dissolve_on_death_captures_snapshot_and_nulls_fk(sim_with_zone):
    """dissolve_on_death must capture the deceased's name snapshot, null the FK,
    and set the dissolution metadata correctly."""
    sim, zone = sim_with_zone
    a = _make_agent(sim, zone, "Nora")
    b = _make_agent(sim, zone, "Oscar", gender=Agent.Gender.MALE)
    form_couple(a, b, formed_at_tick=1)

    # a (agent_a, lower PK) dies at tick 7
    result = dissolve_on_death(a, tick=7)

    assert result is not None
    result.refresh_from_db()

    assert result.agent_a is None
    assert result.agent_a_name_snapshot == "Nora"
    assert result.agent_b_id == b.pk  # surviving partner FK preserved
    assert result.dissolved_at_tick == 7
    assert result.dissolution_reason == Couple.DissolutionReason.DEATH


@pytest.mark.django_db
def test_dissolve_on_death_when_agent_b_dies(sim_with_zone):
    """dissolve_on_death must capture agent_b's snapshot when the higher-PK partner dies."""
    sim, zone = sim_with_zone
    a = _make_agent(sim, zone, "Petra")
    b = _make_agent(sim, zone, "Quentin", gender=Agent.Gender.MALE)
    form_couple(a, b, formed_at_tick=2)

    result = dissolve_on_death(b, tick=9)

    assert result is not None
    result.refresh_from_db()

    assert result.agent_b is None
    assert result.agent_b_name_snapshot == "Quentin"
    assert result.agent_a_id == a.pk  # surviving partner FK preserved
    assert result.dissolved_at_tick == 9
    assert result.dissolution_reason == Couple.DissolutionReason.DEATH


@pytest.mark.django_db
def test_dissolve_on_death_returns_none_when_no_couple(sim_with_zone):
    """dissolve_on_death must return None when the agent has no active Couple."""
    sim, zone = sim_with_zone
    lone = _make_agent(sim, zone, "Roberta")
    result = dissolve_on_death(lone, tick=5)
    assert result is None


@pytest.mark.django_db
def test_dissolve_on_death_both_partners_same_tick(sim_with_zone):
    """dissolve_on_death must capture BOTH snapshots when both partners die in the
    same tick and dissolve_on_death is called once per partner.

    active_couple_for filters dissolved_at_tick__isnull=True, so once the first
    call sets dissolved_at_tick, the couple is no longer "active": the second
    call finds no active couple for the second partner and returns None. This
    is the same-tick double-death bug this test documents.
    """
    sim, zone = sim_with_zone
    a = _make_agent(sim, zone, "Sylvia")
    b = _make_agent(sim, zone, "Tobias", gender=Agent.Gender.MALE)
    couple = form_couple(a, b, formed_at_tick=1)

    dissolve_on_death(a, tick=7)
    dissolve_on_death(b, tick=7)

    couple = Couple.objects.get(pk=couple.pk)

    assert couple.agent_a is None
    assert couple.agent_b is None
    assert couple.agent_a_name_snapshot == "Sylvia"
    assert couple.agent_b_name_snapshot == "Tobias"
    assert couple.dissolved_at_tick == 7
    assert couple.dissolution_reason == Couple.DissolutionReason.DEATH


@pytest.mark.django_db
def test_resolve_pair_bond_refuses_an_ambiguous_name(sim_with_zone, caplog):
    """Two living agents share a name: bind neither, and say so.

    Found by round 9 of the demography Plan 4 phase-6 gate. The resolver used
    `filter(name=...).first()`, so on a collision the lowest id won in
    silence and an agent was bound to somebody it never named. Before Plan 4
    nothing in production created agents after world generation; Plan 4 makes
    newborns, and `pick_newborn_name` draws from an era pool of TWELVE names
    per sex with no uniqueness check, so a collision stops being unlikely and
    becomes certain at the thirteenth birth of a sex.

    Refusing is the ratified fix: it does not remove the ambiguity, it stops
    the wrong marriage and leaves a record. Resolving by id instead of by
    name would remove it, and is a separate work item because it changes the
    action schema the decision loop hands the model.
    """
    import logging
    import random

    sim, zone = sim_with_zone
    sim.config = {"demography_template": "pre_industrial_christian"}
    sim.current_tick = 5
    sim.save()

    suitor = _make_agent(sim, zone, "Bruno", gender=Agent.Gender.MALE)
    first_amelia = _make_agent(sim, zone, "Amelia")
    second_amelia = _make_agent(sim, zone, "Amelia")

    # ONLY the ambiguous intent is filed. Under this era's implicit mutual
    # consent a single intent suffices to form a couple, so if the second
    # Amelia also named Bruno the pair would form from HER unambiguous side
    # and this test would pass while proving nothing about the resolver.
    _decision_log(sim, suitor, tick=4, action="pair_bond", target="Amelia")

    with caplog.at_level(logging.WARNING, logger="epocha.apps.demography.couple"):
        formed = resolve_pair_bond_intents(sim, tick=5, rng=random.Random(42))

    assert formed == [], (
        "an ambiguous name was resolved: one of the two Amelias was married "
        "off without ever being named"
    )
    assert not Couple.objects.filter(simulation=sim).exists()
    assert any("Amelia" in record.message for record in caplog.records), (
        "an ambiguous match must leave a record, or the intent vanishes with "
        "no explanation in any log"
    )
    assert second_amelia.id != first_amelia.id


# ---------------------------------------------------------------------------
# The era's minimum marriage age, on the intent path
# ---------------------------------------------------------------------------
#
# Found by round 9 of the demography Plan 4 phase-6 gate: `min_marriage_age_*`
# was read only by `initialization.form_initial_couples`, so the founding
# pairing respected the era's threshold while every couple formed afterwards
# by intent did not. One rule, applied on one of the two paths that form
# couples -- the class of defect the gate had found seven times. The default
# era, `pre_industrial_christian`, sets the thresholds at 16 for men and 14
# for women, which is what the boundaries below sit on.


def _pair_bond_both_ways(sim, a, b):
    _decision_log(sim, a, tick=4, action="pair_bond", target=b.name)
    _decision_log(sim, b, tick=4, action="pair_bond", target=a.name)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("minor_gender", "minor_age", "adult_gender"),
    [
        (Agent.Gender.FEMALE, 13, Agent.Gender.MALE),
        (Agent.Gender.MALE, 15, Agent.Gender.FEMALE),
    ],
)
def test_an_intent_one_year_below_the_era_threshold_is_refused(
    sim_with_zone, caplog, minor_gender, minor_age, adult_gender
):
    """One year under the threshold of the minor's own sex: no couple, a record.

    Both sides pair-bond each other, so the only thing that can stop the
    couple is the age rule -- and the minor is the TARGET of one intent and
    the PROPOSER of the other, which is why a rule applied to one role only
    still fails this test.
    """
    import logging
    import random

    sim, zone = sim_with_zone
    sim.config = {"demography_template": "pre_industrial_christian"}
    sim.save()

    minor = _make_agent(sim, zone, "Minore", age=minor_age, gender=minor_gender)
    adult = _make_agent(sim, zone, "Adulto", age=30, gender=adult_gender)
    _pair_bond_both_ways(sim, minor, adult)

    with caplog.at_level(logging.WARNING, logger="epocha.apps.demography.couple"):
        formed = resolve_pair_bond_intents(sim, tick=5, rng=random.Random(42))

    assert formed == [], f"a {minor_age}-year-old was married under the era's threshold"
    assert not Couple.objects.filter(simulation=sim).exists()
    assert any("Minore" in record.message for record in caplog.records), (
        "a refused intent must leave a record, as an ambiguous one does"
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("proposer_gender", "proposer_age", "target_gender", "target_age"),
    [
        # Each side exactly at its own threshold, in both roles.
        (Agent.Gender.FEMALE, 14, Agent.Gender.MALE, 16),
        (Agent.Gender.MALE, 16, Agent.Gender.FEMALE, 14),
    ],
)
def test_an_intent_exactly_at_the_era_threshold_is_accepted(
    sim_with_zone, proposer_gender, proposer_age, target_gender, target_age
):
    """The other side of the boundary: the threshold is a minimum, inclusive.

    One-sided on purpose -- the era's implicit mutual consent forms the couple
    from a single intent -- so the proposer and the target are two distinct
    roles and each is exercised at its own threshold.
    """
    import random

    sim, zone = sim_with_zone
    sim.config = {"demography_template": "pre_industrial_christian"}
    sim.save()

    proposer = _make_agent(sim, zone, "Proponente", age=proposer_age, gender=proposer_gender)
    target = _make_agent(sim, zone, "Bersaglio", age=target_age, gender=target_gender)
    _decision_log(sim, proposer, tick=4, action="pair_bond", target=target.name)

    formed = resolve_pair_bond_intents(sim, tick=5, rng=random.Random(42))

    assert len(formed) == 1, (
        f"a {proposer_age}-year-old {proposer_gender} and a {target_age}-year-old "
        f"{target_gender}, each exactly at the era's threshold, were refused"
    )


@pytest.mark.django_db
def test_an_arranged_marriage_of_a_child_below_the_threshold_is_refused(sim_with_zone):
    """Goode's arranged marriage is the path a minor is most likely to take.

    A parent proposing on behalf of a twelve-year-old daughter: the intent is
    re-attributed to the child, and the child is under the era's threshold.
    """
    import random

    sim, zone = sim_with_zone
    sim.config = {"demography_template": "pre_industrial_christian"}
    sim.save()

    parent = _make_agent(sim, zone, "Genitore", age=45)
    child = _make_agent(sim, zone, "Figlia", age=12)
    match = _make_agent(sim, zone, "Promesso", age=25, gender=Agent.Gender.MALE)
    _decision_log(
        sim,
        parent,
        tick=4,
        action="pair_bond",
        target={"for_child": child.name, "match": match.name},
    )

    formed = resolve_pair_bond_intents(sim, tick=5, rng=random.Random(3))

    assert formed == [], "an arranged marriage bound a child under the era's threshold"


@pytest.mark.django_db
@pytest.mark.parametrize(("age", "expected_couples"), [(15, 0), (16, 1)])
def test_a_non_binary_agent_meets_the_higher_of_the_two_thresholds(
    sim_with_zone, age, expected_couples
):
    """The templates carry a male and a female threshold and nothing else.

    The higher of the two applies, declared as the conservative choice: 15
    clears the female 14 of the default era and must still be refused, 16
    clears both.
    """
    import random

    sim, zone = sim_with_zone
    sim.config = {"demography_template": "pre_industrial_christian"}
    sim.save()

    agent = _make_agent(sim, zone, "Nonbinario", age=age, gender=Agent.Gender.NON_BINARY)
    partner = _make_agent(sim, zone, "Partner", age=30)
    _pair_bond_both_ways(sim, agent, partner)

    formed = resolve_pair_bond_intents(sim, tick=5, rng=random.Random(5))

    assert len(formed) == expected_couples


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("column_age", "years_since_birth", "expected_couples"),
    [(30, 13, 0), (10, 20, 1)],
)
def test_the_age_is_read_from_the_birth_tick_not_the_frozen_column(
    sim_with_zone, column_age, years_since_birth, expected_couples
):
    """`birth_tick` is the canonical age; the `age` column is a cache of it.

    The two are driven apart in both directions, so a rule that reads the
    column -- which is what the founding pairing did -- fails one of the two.
    """
    import random

    sim, zone = sim_with_zone
    sim.config = {"demography_template": "pre_industrial_christian"}
    sim.save()

    agent = _make_agent(
        sim,
        zone,
        "Colonna",
        age=column_age,
        birth_tick=sim.current_tick - years_since_birth * TICKS_PER_YEAR,
    )
    partner = _make_agent(sim, zone, "Partner", age=30, gender=Agent.Gender.MALE)
    _pair_bond_both_ways(sim, agent, partner)

    formed = resolve_pair_bond_intents(sim, tick=5, rng=random.Random(9))

    assert len(formed) == expected_couples


@pytest.mark.django_db
def test_the_age_carries_the_eras_acceleration(sim_with_zone):
    """Seven calendar years at acceleration 2.0 are fourteen years of age.

    `age_in_years` multiplies by the era's factor; an age rule that computed
    its own years would reproduce the two-clocks defect round 9 found in the
    backfill.
    """
    import copy
    import random

    from epocha.apps.demography.template_loader import load_template

    sim, zone = sim_with_zone
    sim.config = {"demography_template": "pre_industrial_christian"}
    sim.save()

    template = copy.deepcopy(load_template("pre_industrial_christian"))
    template["acceleration"] = 2.0
    bride = _make_agent(sim, zone, "Sposa", birth_tick=sim.current_tick - 7 * TICKS_PER_YEAR)
    groom = _make_agent(sim, zone, "Sposo", age=30, gender=Agent.Gender.MALE)
    _pair_bond_both_ways(sim, bride, groom)

    with patch("epocha.apps.demography.template_loader.load_template", return_value=template):
        formed = resolve_pair_bond_intents(sim, tick=5, rng=random.Random(11))

    assert len(formed) == 1, (
        "fourteen years of age at acceleration 2.0 were read as seven: the "
        "age rule is not on the orchestrator's clock"
    )


@pytest.mark.django_db
def test_a_refused_target_does_not_end_the_proposers_other_intents(sim_with_zone):
    """The rule refuses a PAIRING, not a proposer.

    An adult who filed two intents, the first toward a minor and the second
    toward an adult, must still marry the second. Round 10 of the phase-6
    gate measured that turning the refusal's `continue` into a `break` left
    every test green, because no fixture gave a proposer a second target.
    The minor is created first so her intent is read first.
    """
    import random

    sim, zone = sim_with_zone
    sim.config = {"demography_template": "pre_industrial_christian"}
    sim.save()

    minor = _make_agent(sim, zone, "Tredicenne", age=13)
    adult = _make_agent(sim, zone, "Adulta", age=24)
    suitor = _make_agent(sim, zone, "Pretendente", age=30, gender=Agent.Gender.MALE)
    _decision_log(sim, suitor, tick=4, action="pair_bond", target=minor.name)
    _decision_log(sim, suitor, tick=4, action="pair_bond", target=adult.name)

    formed = resolve_pair_bond_intents(sim, tick=5, rng=random.Random(13))

    assert [{c.agent_a_id, c.agent_b_id} for c in formed] == [{suitor.id, adult.id}], (
        "refusing the minor ended the suitor's turn before his valid second intent"
    )
