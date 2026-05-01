import json
import ijson
import base64
import aiofiles
import itsdangerous
import pytest_asyncio
from uuid6 import uuid7
from pathlib import Path
from sqlalchemy.pool import NullPool
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock, Mock
from httpx import AsyncClient, ASGITransport, Response
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
from app.api.models.users import User
from app.dependencies import get_session
from app.api.models.profiles import Profile
from app.api.models.auth import RefreshToken
from app.api.services.user_service import user_service_v1
from app.api.services.profile_service import profile_service_v1


BASE_PATH: str = "app.api.services.auth_service"


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
        join_transaction_mode="create_savepoint",
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


@pytest_asyncio.fixture
async def seed_database(async_session: AsyncSession):
    file_path: Path = (
        Path(__file__).parent.parent / "app" / "scripts" / "seed_profiles.json"
    )

    profiles: list[dict] = []
    async with aiofiles.open(file_path, "rb") as json_file:
        i = 0
        async for v in ijson.items_async(json_file, "profiles.item"):
            if i >= 500:
                break

            v["id"] = uuid7()
            v["created_at"] = datetime.now(timezone.utc)
            profiles.append(v)
            i += 1

    await profile_service_v1.create_profiles(profiles, async_session)


@pytest_asyncio.fixture(autouse=True)
async def create_admin(async_session: AsyncSession):
    admin_user: User = User(
        id=uuid7(),
        github_id="fake_github_id",
        username="fake_admin_username",
        email="fakeadmin@example.com",
        avatar_url="fake_avatar_url",
        role="admin",
        last_login_at=datetime.now(timezone.utc)
    )
    await user_service_v1.create_user(admin_user, async_session)


@pytest_asyncio.fixture
async def sign_in(async_client: AsyncClient):
    sign_in_res: Response = await async_client.get(
        "/auth/github?api_client=test",
        follow_redirects=False,
        headers={
            "X-API-Version": "1",
            "env": "testing",
        },
    )

    assert sign_in_res.status_code == 302

    session_cookie = sign_in_res.cookies.get("session")

    signer = itsdangerous.TimestampSigner(settings.SESSION_SECRET_KEY)
    data = signer.unsign(session_cookie)
    client_data: dict = json.loads(base64.b64decode(data))["client_data"]

    state: str = client_data.get("state")
    # api_client: str = client_data.get("client")

    fake_github_token: dict = {"access_token": "fakeaccesstoken"}
    user_profile: dict = {
        "id": "fakerandomid",
        "avatar_url": "fake_avatar_url",
        "login": "fake_username",
        "email": "fakeadmin@example.com",
        "github_id": "fake_github_id",
        "created_at": datetime.now(timezone.utc)
    }

    mock_client = AsyncMock()

    mock_response = Mock()
    mock_response.json.return_value = fake_github_token

    mock_client.post.return_value = mock_response

    app.state.github = mock_client

    profile_patch: AsyncMock = patch(
        f"{BASE_PATH}.auth_service_v1.get_user_profile", new_callable=AsyncMock
    ).start()

    profile_patch.return_value = user_profile

    callback_res: Response = await async_client.get(
        f"/auth/github/callback?code=fakegithubcode&state={state}",
        headers={
            "X-API-Version": "1",
            "env": "testing",
        },
    )

    await profile_patch.stop()

    return callback_res


@pytest_asyncio.fixture
async def set_state(async_client: AsyncClient):
    app.state.agify = AsyncClient(base_url=settings.AGIFY_API_URL, timeout=10.0)
    app.state.genderize = AsyncClient(base_url=settings.GENDERIZE_API_URL, timeout=10.0)
    app.state.nationalize = AsyncClient(
        base_url=settings.NATIONALIZE_API_URL, timeout=10.0
    )

    yield

    await app.state.agify.aclose()
    await app.state.genderize.aclose()
    await app.state.nationalize.aclose()
