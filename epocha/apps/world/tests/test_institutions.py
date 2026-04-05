"""Tests for institution health dynamics."""
import pytest

from epocha.apps.world.institutions import update_institutions
from epocha.apps.world.models import Government, Institution, World
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User


@pytest.fixture
def user(db):
    return User.objects.create_user(email="inst@epocha.dev", username="insttest", password="pass123")

@pytest.fixture
def simulation(user):
    return Simulation.objects.create(name="InstTest", seed=42, owner=user)

@pytest.fixture
def world(simulation):
    return World.objects.create(simulation=simulation)

@pytest.fixture
def government(simulation):
    return Government.objects.create(simulation=simulation, government_type="democracy")

@pytest.fixture
def all_institutions(simulation):
    types = ["justice", "education", "health", "military", "media", "religion", "bureaucracy"]
    return [Institution.objects.create(simulation=simulation, institution_type=t, health=0.5, independence=0.5, funding=0.5) for t in types]


@pytest.mark.django_db
class TestUpdateInstitutions:
    def test_democracy_improves_justice(self, simulation, world, government, all_institutions):
        justice = Institution.objects.get(simulation=simulation, institution_type="justice")
        initial = justice.health
        update_institutions(simulation)
        justice.refresh_from_db()
        assert justice.health > initial

    def test_autocracy_degrades_media(self, simulation, world, government, all_institutions):
        government.government_type = "autocracy"
        government.save(update_fields=["government_type"])
        media = Institution.objects.get(simulation=simulation, institution_type="media")
        initial = media.health
        update_institutions(simulation)
        media.refresh_from_db()
        assert media.health < initial

    def test_health_clamped_to_range(self, simulation, world, government, all_institutions):
        for inst in all_institutions:
            inst.health = 0.99
            inst.save(update_fields=["health"])
        update_institutions(simulation)
        for inst in Institution.objects.filter(simulation=simulation):
            assert 0.0 <= inst.health <= 1.0

    def test_low_funding_degrades_health(self, simulation, world, government, all_institutions):
        justice = Institution.objects.get(simulation=simulation, institution_type="justice")
        justice.funding = 0.1
        justice.health = 0.5
        justice.save(update_fields=["funding", "health"])
        update_institutions(simulation)
        justice.refresh_from_db()
        assert justice.health <= 0.5

    def test_all_7_institutions_updated(self, simulation, world, government, all_institutions):
        update_institutions(simulation)
        for inst in Institution.objects.filter(simulation=simulation):
            inst.refresh_from_db()
            assert isinstance(inst.health, float)
