import pytest
from httpx import AsyncClient, Response


@pytest.mark.asyncio
async def test_sign_in_with_github(sign_in: Response):
    print(sign_in.json)
    assert sign_in.status_code == 200
    assert "access_token" in sign_in.json()


@pytest.mark.asyncio
async def test_get_user(async_client: AsyncClient, sign_in: Response):
    json_res = sign_in.json()
    access_token: str = json_res["access_token"]

    res = await async_client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
            "X-API-Version": "1",
            "env": "testing",
        },
    )

    json_res = res.json()

    assert res.status_code == 200
    assert "admin" == json_res["data"]["role"]


@pytest.mark.asyncio
async def test_create_access_token(async_client: AsyncClient, sign_in: Response):
    json_res = sign_in.json()
    refresh_token: str = json_res["refresh_token"]

    auth_token: dict = {"refresh_token": refresh_token}

    res = await async_client.post(
        "/auth/refresh",
        json=auth_token,
        headers={
            "X-API-Version": "1",
            "env": "testing",
        },
    )
    print(res.json())

    assert res.status_code == 201
    assert "access_token" in res.json()


@pytest.mark.asyncio
async def test_logout(async_client: AsyncClient, sign_in: Response):
    json_res = sign_in.json()
    access_token: str = json_res["access_token"]
    refresh_token: str = json_res["refresh_token"]

    auth_token: dict = {"refresh_token": refresh_token}

    res = await async_client.post(
        "/auth/logout",
        json=auth_token,
        headers={
            "Authorization": f"Bearer {access_token}",
            "env": "testing",
            "X-API-Version": "1",
        },
    )

    assert res.status_code == 201
