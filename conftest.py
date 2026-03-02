import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def sample_user(db):
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='TestPass123!',
        full_name='Test User',
        is_verified=True,
    )
    return user


@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(
        username='adminuser',
        email='admin@example.com',
        password='AdminPass123!',
        full_name='Admin User',
        role='admin',
        is_verified=True,
        is_staff=True,
    )
    return user


@pytest.fixture
def authenticated_client(api_client, sample_user):
    api_client.force_authenticate(user=sample_user)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client
