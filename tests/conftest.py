"""Global pytest fixtures."""
import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """DRF API test client."""
    return APIClient()


@pytest.fixture
def user(db, django_user_model):
    """Create a test user."""
    return django_user_model.objects.create_user(
        email="test@epocha.dev",
        username="testuser",
        password="testpass123",
    )


@pytest.fixture
def authenticated_client(api_client, user):
    """API client authenticated with test user."""
    api_client.force_authenticate(user=user)
    return api_client
