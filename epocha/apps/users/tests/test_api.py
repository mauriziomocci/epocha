"""Tests for user registration, login, and simulation ownership."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from epocha.apps.users.models import User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="test@epocha.dev", username="testuser", password="testpass123")


@pytest.mark.django_db
class TestUserRegistration:
    def test_register_new_user(self, api_client):
        response = api_client.post("/api/v1/users/register/", {
            "email": "newuser@epocha.dev",
            "username": "newuser",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        }, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert "email" in response.data
        assert "password" not in response.data

    def test_register_duplicate_email_fails(self, api_client, user):
        response = api_client.post("/api/v1/users/register/", {
            "email": "test@epocha.dev",
            "username": "another",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        }, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_password_mismatch_fails(self, api_client):
        response = api_client.post("/api/v1/users/register/", {
            "email": "new@epocha.dev",
            "username": "newuser",
            "password": "StrongPass123!",
            "password_confirm": "DifferentPass!",
        }, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_short_password_fails(self, api_client):
        response = api_client.post("/api/v1/users/register/", {
            "email": "new@epocha.dev",
            "username": "newuser",
            "password": "short",
            "password_confirm": "short",
        }, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestUserLogin:
    def test_login_returns_tokens(self, api_client, user):
        response = api_client.post("/api/v1/users/token/", {
            "email": "test@epocha.dev",
            "password": "testpass123",
        }, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_login_wrong_password_fails(self, api_client, user):
        response = api_client.post("/api/v1/users/token/", {
            "email": "test@epocha.dev",
            "password": "wrongpassword",
        }, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
