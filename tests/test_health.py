"""
Smoke tests — verify the API starts and responds.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Test that the health endpoint returns 200."""
    response = await client.get("/health")
    assert response.status_code == 200
