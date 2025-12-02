"""
Pytest configuration and fixtures.
"""

import asyncio
from typing import AsyncGenerator, Generator
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.main import app
from app.models.user import User


# Test database URL (use SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database session override."""
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User",
        business_name="Test Business",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def auth_client(
    client: AsyncClient,
    test_user: User,
) -> AsyncClient:
    """Create authenticated test client."""
    # Login to get token
    response = await client.post(
        "/api/v1/auth/login/json",
        json={
            "email": "test@example.com",
            "password": "testpassword123",
        },
    )
    tokens = response.json()
    
    # Set authorization header
    client.headers["Authorization"] = f"Bearer {tokens['access_token']}"
    
    return client

