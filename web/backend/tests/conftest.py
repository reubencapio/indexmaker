"""
Pytest fixtures for testing.

Provides database sessions, test client, and authentication fixtures.
"""

import asyncio
import os
from collections.abc import AsyncGenerator, Generator
from urllib.parse import urlparse, urlunparse

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.db.session import Base, get_db
from app.main import create_application
from app.models.user import User, UserRole, UserTier
from app.services.market_data_service import MarketDataService


def _resolve_test_database_url() -> str:
    """
    Resolve the database URL used by the test suite.

    The suite creates and drops every table it touches, so it must never point
    at a development or production database. An explicit TEST_DATABASE_URL wins
    (CI provides one); otherwise we derive a dedicated `<db>_test` database from
    the configured URL rather than reusing the configured database itself.
    """
    explicit = os.environ.get("TEST_DATABASE_URL")
    if explicit:
        return explicit

    parsed = urlparse(str(settings.DATABASE_URL))
    db_name = parsed.path.lstrip("/") or "indexforge"
    if not db_name.endswith("_test"):
        db_name = f"{db_name}_test"
    return urlunparse(parsed._replace(path=f"/{db_name}"))


TEST_DATABASE_URL = _resolve_test_database_url()


async def _ensure_test_database_exists(url: str) -> None:
    """Create the test database if it is not there yet (no-op if it exists)."""
    import asyncpg

    parsed = urlparse(url)
    db_name = parsed.path.lstrip("/")
    admin_dsn = urlunparse(
        parsed._replace(scheme="postgresql", path="/postgres", query="", fragment="")
    )

    conn = await asyncpg.connect(admin_dsn)
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", db_name)
        if not exists:
            # asyncpg cannot parameterise an identifier here; the name is derived
            # from local configuration, not from user input.
            await conn.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await conn.close()


async def _reset_schema(drop_only: bool = False) -> None:
    """Drop (and optionally recreate) every table on a short-lived engine."""
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            if not drop_only:
                await conn.run_sync(Base.metadata.create_all)
    finally:
        await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def prepared_database() -> Generator[None, None, None]:
    """
    Create the test database and its schema once per session.

    This is a sync fixture driving its own event loop on purpose. pytest-asyncio
    runs each test in a fresh loop, so a session-scoped *async* fixture would
    hand out connections bound to a loop the tests never run on -- which is what
    previously produced "attached to a different loop" errors across the suite.
    """

    async def setup() -> None:
        await _ensure_test_database_exists(TEST_DATABASE_URL)
        await _reset_schema()

    asyncio.run(setup())
    yield
    asyncio.run(_reset_schema(drop_only=True))


@pytest_asyncio.fixture
async def test_engine(prepared_database):
    """Per-test engine, so every connection belongs to this test's event loop."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a session wrapped in a transaction that is always rolled back.

    The session joins the outer transaction via a savepoint, so application code
    (and fixtures) can call `commit()` normally while every write is still
    discarded at the end of the test. Without this, state leaked between tests
    and reruns failed on rows left behind by earlier runs.
    """
    async with test_engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
            autoflush=False,
        )
        try:
            yield session
        finally:
            await session.close()
            if transaction.is_active:
                await transaction.rollback()


@pytest.fixture(autouse=True)
def stub_market_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Keep the suite off the network.

    Creating an index without explicit components auto-populates them, which
    calls Yahoo Finance once per candidate ticker. Left unstubbed the suite is
    slow, flaky, and fails wherever there is no outbound network. Tests that
    need real market data should patch these methods themselves.
    """

    async def no_info(self: MarketDataService, ticker: str) -> None:
        return None

    async def no_history(self: MarketDataService, *args: object, **kwargs: object) -> list:
        return []

    async def no_prices(self: MarketDataService, *args: object, **kwargs: object) -> dict:
        return {}

    async def no_search(self: MarketDataService, *args: object, **kwargs: object) -> list:
        return []

    monkeypatch.setattr(MarketDataService, "get_security_info", no_info)
    monkeypatch.setattr(MarketDataService, "get_price_history", no_history)
    monkeypatch.setattr(MarketDataService, "get_prices_for_tickers", no_prices)
    monkeypatch.setattr(MarketDataService, "search_securities", no_search)


@pytest_asyncio.fixture
async def app(db_session: AsyncSession) -> FastAPI:
    """Create a test application with overridden dependencies."""
    app = create_application()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword"),
        full_name="Test User",
        role=UserRole.USER.value,
        tier=UserTier.FREE.value,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create a test admin user."""
    user = User(
        email="admin@example.com",
        hashed_password=get_password_hash("adminpassword"),
        full_name="Admin User",
        role=UserRole.ADMIN.value,
        tier=UserTier.ENTERPRISE.value,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict[str, str]:
    """Create authentication headers for test user."""
    token = create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(admin_user: User) -> dict[str, str]:
    """Create authentication headers for admin user."""
    token = create_access_token(admin_user.id)
    return {"Authorization": f"Bearer {token}"}
