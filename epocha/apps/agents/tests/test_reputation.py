"""Tests for the reputation system (Castelfranchi-Conte-Paolucci model)."""
import pytest

from epocha.apps.agents.models import Agent, ReputationScore
from epocha.apps.agents.reputation import (
    extract_action_sentiment,
    get_combined_score,
    update_image,
    update_reputation,
)
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World


@pytest.fixture
def user(db):
    return User.objects.create_user(email="rep@epocha.dev", username="reptest", password="pass123")

@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="RepTest", seed=42, owner=user)

@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation)

@pytest.fixture
def marco(simulation):
    return Agent.objects.create(simulation=simulation, name="Marco", role="blacksmith", personality={"openness": 0.5})

@pytest.fixture
def elena(simulation):
    return Agent.objects.create(simulation=simulation, name="Elena", role="farmer", personality={"openness": 0.5})


@pytest.mark.django_db
class TestUpdateImage:
    def test_help_increases_image(self, marco, elena):
        update_image(holder=elena, target=marco, action_type="help", tick=5)
        score = ReputationScore.objects.get(holder=elena, target=marco)
        assert score.image > 0.0

    def test_betray_decreases_image(self, marco, elena):
        update_image(holder=elena, target=marco, action_type="betray", tick=5)
        score = ReputationScore.objects.get(holder=elena, target=marco)
        assert score.image < 0.0

    def test_image_clamped_to_range(self, marco, elena):
        for _ in range(20):
            update_image(holder=elena, target=marco, action_type="help", tick=5)
        score = ReputationScore.objects.get(holder=elena, target=marco)
        assert score.image <= 1.0

    def test_image_accumulates(self, marco, elena):
        update_image(holder=elena, target=marco, action_type="help", tick=5)
        update_image(holder=elena, target=marco, action_type="help", tick=6)
        score = ReputationScore.objects.get(holder=elena, target=marco)
        assert score.image > 0.15


@pytest.mark.django_db
class TestUpdateReputation:
    def test_positive_hearsay_increases_reputation(self, marco, elena):
        update_reputation(holder=elena, target=marco, action_sentiment=1.0, reliability=0.7, tick=5)
        score = ReputationScore.objects.get(holder=elena, target=marco)
        assert score.reputation > 0.0

    def test_negative_hearsay_decreases_reputation(self, marco, elena):
        update_reputation(holder=elena, target=marco, action_sentiment=-1.0, reliability=0.7, tick=5)
        score = ReputationScore.objects.get(holder=elena, target=marco)
        assert score.reputation < 0.0

    def test_low_reliability_has_less_impact(self, marco, elena):
        update_reputation(holder=elena, target=marco, action_sentiment=-1.0, reliability=0.1, tick=5)
        score_low_rep = ReputationScore.objects.get(holder=elena, target=marco).reputation
        ReputationScore.objects.filter(holder=elena, target=marco).delete()
        update_reputation(holder=elena, target=marco, action_sentiment=-1.0, reliability=0.9, tick=5)
        score_high_rep = ReputationScore.objects.get(holder=elena, target=marco).reputation
        assert abs(score_high_rep) > abs(score_low_rep)

    def test_reputation_does_not_change_image(self, marco, elena):
        update_reputation(holder=elena, target=marco, action_sentiment=-1.0, reliability=0.7, tick=5)
        score = ReputationScore.objects.get(holder=elena, target=marco)
        assert score.image == 0.0


@pytest.mark.django_db
class TestGetCombinedScore:
    def test_combines_image_and_reputation(self, marco, elena):
        ReputationScore.objects.create(holder=elena, target=marco, image=0.5, reputation=-0.5)
        combined = get_combined_score(elena, marco)
        assert abs(combined - 0.1) < 0.01  # 0.5*0.6 + (-0.5)*0.4

    def test_no_score_returns_zero(self, marco, elena):
        assert get_combined_score(elena, marco) == 0.0

    def test_range_is_valid(self, marco, elena):
        ReputationScore.objects.create(holder=elena, target=marco, image=1.0, reputation=1.0)
        assert -1.0 <= get_combined_score(elena, marco) <= 1.0


class TestExtractActionSentiment:
    def test_helped_is_positive(self):
        assert extract_action_sentiment("I decided to help. saved the village") > 0

    def test_betrayed_is_negative(self):
        assert extract_action_sentiment("I decided to betray. power grab") < 0

    def test_neutral_returns_zero(self):
        assert extract_action_sentiment("I decided to rest. tired") == 0.0

    def test_argued_is_mildly_negative(self):
        s = extract_action_sentiment("I decided to argue. angry")
        assert -1.0 < s < 0.0
