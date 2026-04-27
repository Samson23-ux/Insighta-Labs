import pytest
from uuid import UUID
from uuid6 import uuid7
from httpx import AsyncClient, Response


@pytest.mark.asyncio
async def test_sign_in_with_github(sign_in: Response):
    assert sign_in.status_code == 200
    assert "access_token" in sign_in.json()


@pytest.mark.asyncio
async def test_create_access_token(async_client: AsyncClient, sign_in: Response):
    json_res = sign_in.json()
    refresh_token: str = json_res["refresh_token"]

    res = await async_client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
        headers={
            "X-API-Version": 1,
            "env": "testing",
        },
    )

    assert res.status_code == 201
    assert "access_token" in res.json()


@pytest.mark.asyncio
async def test_logout(async_client: AsyncClient, sign_in: Response):
    json_res = sign_in.json()
    access_token: str = json_res["access_token"]
    refresh_token: str = json_res["refresh_token"]

    res = await async_client.post(
        "/auth/logout",
        json={"refresh_token": refresh_token},
        headers={
            "Authorization": f"Bearer {access_token}",
            "env": "testing",
            "X-API-Version": 1,
        },
    )

    assert res.status_code == 201
