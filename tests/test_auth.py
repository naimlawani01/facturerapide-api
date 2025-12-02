"""
Authentication endpoint tests.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """Test user registration."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "password123",
            "full_name": "New User",
            "business_name": "New Business",
        },
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["full_name"] == "New User"
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_user):
    """Test registration with duplicate email."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",  # Same as test_user
            "password": "password123",
            "full_name": "Another User",
        },
    )
    
    assert response.status_code == 400
    assert "existe déjà" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user):
    """Test successful login."""
    response = await client.post(
        "/api/v1/auth/login/json",
        json={
            "email": "test@example.com",
            "password": "testpassword123",
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user):
    """Test login with wrong password."""
    response = await client.post(
        "/api/v1/auth/login/json",
        json={
            "email": "test@example.com",
            "password": "wrongpassword",
        },
    )
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(auth_client: AsyncClient):
    """Test getting current user profile."""
    response = await auth_client.get("/api/v1/auth/me")
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_protected_route_without_token(client: AsyncClient):
    """Test accessing protected route without token."""
    response = await client.get("/api/v1/auth/me")
    
    assert response.status_code == 401

