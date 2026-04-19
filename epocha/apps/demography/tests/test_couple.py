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
        email="couple@epocha.dev", username="coupleuser", password="pass1234",
    )
    sim = Simulation.objects.create(
        name="CoupleTest", seed=42, owner=user, current_tick=5,
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


def _make_agent(sim, zone, name, **kwargs):
    """Helper: create an Agent with sensible defaults."""
    defaults = dict(
        role="farmer",
        location=Point(50, 50),
        health=1.0,
        wealth=100.0,
        age=25,
        birth_tick=0,
        mood=0.5,
        education_level=0.5,
        social_class="working",
        gender=Agent.Gender.FEMALE,
    )
    defaults.update(kwargs)
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
        (0, "A"): 0.9, (0, "B"): 0.6, (0, "C"): 0.3,
        (1, "A"): 0.5, (1, "B"): 0.8, (1, "C"): 0.4,
        (2, "A"): 0.3, (2, "B"): 0.4, (2, "C"): 0.9,
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
        (0, "A"): 0.9, (0, "B"): 0.6, (0, "C"): 0.3,
        (1, "A"): 0.5, (1, "B"): 0.8, (1, "C"): 0.4,
        (2, "A"): 0.3, (2, "B"): 0.4, (2, "C"): 0.9,
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
        (0, "X"): 0.8, (0, "Y"): 0.5,
        (1, "X"): 0.6, (1, "Y"): 0.9,
        (2, "X"): 0.4, (2, "Y"): 0.4,
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
        }
    }

    import random
    with patch("epocha.apps.demography.template_loader.load_template", return_value=implicit_template):
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
        }
    }

    import random
    with patch("epocha.apps.demography.template_loader.load_template", return_value=explicit_template):
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
        sim, parent, tick=4, action="pair_bond",
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
    couple = form_couple(a, b, formed_at_tick=1)

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
    couple = form_couple(a, b, formed_at_tick=2)

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
