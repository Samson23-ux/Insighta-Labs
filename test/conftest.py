import ijson
import aiofiles
import pytest_asyncio
from uuid6 import uuid7
from pathlib import Path
from sqlalchemy.pool import NullPool
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    AsyncConnection,
    AsyncTransaction,
)


from app.main import app
from app.database.base import Base
from app.core.config import settings
from app.dependencies import get_session
from app.api.models.profiles import Profile
from app.api.services.profile_service import profile_service


@pytest_asyncio.fixture(scope="session")
async def async_engine():
    async_db_engine: AsyncEngine = create_async_engine(
        url=settings.ASYNC_TEST_DB_URL, poolclass=NullPool
    )

    async with async_db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield async_db_engine

    async with async_db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await async_db_engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine: AsyncEngine):
    async_connection: AsyncConnection = await async_engine.connect()
    async_transaction: AsyncTransaction = await async_connection.begin()

    session = async_sessionmaker(
        bind=async_connection,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint"
    )

    async_session: AsyncSession = session()
    yield async_session

    await async_session.close()
    await async_transaction.rollback()
    await async_connection.close()


@pytest_asyncio.fixture
async def async_client(async_session: AsyncSession):
    async def get_test_session():
        return async_session

    app.dependency_overrides[get_session] = get_test_session

    async with AsyncClient(
        transport=ASGITransport(app), base_url="http://localhost/api"
    ) as client:
        yield client


@pytest_asyncio.fixture(autouse=True)
async def seed_database(async_session: AsyncSession):
    file_path: Path = Path(__file__).parent.parent / "app" / "scripts" / "seed_profiles.json"

    profiles: list[dict] = []
    async with aiofiles.open(file_path, "r", encoding="utf-8") as json_file:
        i = 0
        async for v in ijson.items_async(json_file, "profiles.item"):
            if i >= 500:
                break

            v["id"] = uuid7()
            v["created_at"] = datetime.now(timezone.utc)
            profiles.append(v)
            i += 1

    await profile_service.create_profiles(profiles, async_session)
