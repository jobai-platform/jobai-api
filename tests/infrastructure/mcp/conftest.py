import pytest_asyncio


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_test_schema():
    yield
