from collections.abc import AsyncGenerator
import os
from typing import Any
import uuid

from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.constants.general import DB_SCHEMA
from app.core.dependency import get_billing_gateway
from app.infrastructure.config.database import Base, get_async_session
from app.infrastructure.persistence.models.billing_price import BillingPriceModel
from app.infrastructure.persistence.models.user import UserModel
from app.infrastructure.security.jwt_service import JWTService
from app.main import app
from tests.fakes.billing.fake_billing_gateway import FakeBillingGateway


DB_DEPENDENT_FIXTURES = frozenset(
    {
        "async_engine",
        "create_test_schema",
        "db_session",
        "client",
        "ai_client",
        "create_user_in_db",
        "freemium_price_in_db",
    }
)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    integration_marker = pytest.mark.integration
    for item in items:
        if DB_DEPENDENT_FIXTURES.intersection(item.fixturenames):
            item.add_marker(integration_marker)


def _test_db_url() -> str:
    url = os.getenv("DATABASE_URL_TEST") or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL_TEST or DATABASE_URL must be set for tests")

    if "@db:" in url and not os.getenv("RUNNING_IN_DOCKER"):
        url = url.replace("@db:", "@localhost:")

    return url


@pytest_asyncio.fixture(scope="session")
async def async_engine():
    engine = create_async_engine(_test_db_url(), future=True, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def create_test_schema(async_engine):
    """
    Create tables once per test session (faster + less flaky).
    Rollback isolation is handled by db_session fixture per test.
    """
    async with async_engine.begin() as conn:
        if DB_SCHEMA:
            await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{DB_SCHEMA}"'))
        # Drop all with CASCADE to handle FK dependencies, then recreate
        await conn.execute(text(f'DROP SCHEMA IF EXISTS "{DB_SCHEMA}" CASCADE'))
        await conn.execute(text(f'CREATE SCHEMA "{DB_SCHEMA}"'))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    yield


@pytest_asyncio.fixture()
async def db_session(async_engine, create_test_schema) -> AsyncGenerator[AsyncSession | Any, Any]:
    session_factory = async_sessionmaker(
        bind=async_engine,
        expire_on_commit=False,
        autoflush=False,
        class_=AsyncSession,
    )

    async with async_engine.connect() as conn:
        trans = await conn.begin()
        session = session_factory(bind=conn)

        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()


@pytest_asyncio.fixture()
async def client(db_session: AsyncSession):
    async def _override_get_async_session():
        yield db_session

    app.dependency_overrides[get_async_session] = _override_get_async_session
    app.dependency_overrides[get_billing_gateway] = FakeBillingGateway

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="https://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def create_user_in_db(db_session: AsyncSession):
    async def _create_user(
        email: str,
        password: str | None = None,
        role: str = "user",
        is_active: bool = True,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        stripe_customer_id: str | None = None,
    ) -> UserModel:
        user = UserModel(
            email=email.strip().lower(),
            username=username,
            first_name=first_name,
            last_name=last_name,
            hashed_password=(f"fakehashed-{password}" if password else None),
            role=role,
            is_active=is_active,
            stripe_customer_id=stripe_customer_id,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    return _create_user


@pytest_asyncio.fixture()
async def freemium_price_in_db(db_session: AsyncSession) -> BillingPriceModel:
    price = BillingPriceModel(
        id=uuid.uuid4(),
        plan="freemium",
        stripe_price_id="price_test_freemium",
        stripe_product_id="prod_test_freemium",
        currency="usd",
        amount=0,
        interval="month",
        active=True,
    )
    db_session.add(price)
    await db_session.commit()
    await db_session.refresh(price)
    return price


@pytest.fixture()
def jwt_service():
    return JWTService()
