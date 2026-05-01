import pytest
from uuid import UUID
from uuid6 import uuid7
from httpx import AsyncClient, Response


@pytest.mark.asyncio
async def test_create_profile(async_client: AsyncClient, set_state, sign_in: Response):
    payload: dict = {"name": "sergio"}
    access_token: str = sign_in.json()["access_token"]

    res: Response = await async_client.post(
        "/profiles",
        json=payload,
        headers={
            "Authorization": f"Bearer {access_token}",
            "env": "testing",
            "X-API-Version": "1",
        },
    )
    json_res = res.json()

    assert res.status_code == 201
    assert json_res["data"]["name"] == payload.get("name")


@pytest.mark.asyncio
async def test_profile_exists(async_client: AsyncClient, set_state, sign_in: Response):
    payload: dict = {"name": "sergio"}
    access_token: str = sign_in.json()["access_token"]

    await async_client.post(
        "/profiles",
        json=payload,
        headers={
            "Authorization": f"Bearer {access_token}",
            "env": "testing",
            "X-API-Version": "1",
        },
    )

    res: Response = await async_client.post(
        "/profiles",
        json=payload,
        headers={
            "Authorization": f"Bearer {access_token}",
            "env": "testing",
            "X-API-Version": "1",
        },
    )
    json_res = res.json()

    assert res.status_code == 201
    assert json_res["data"]["name"] == payload.get("name")


@pytest.mark.asyncio
async def test_wrong_name_type(async_client: AsyncClient, set_state, sign_in: Response):
    payload: dict = {"name": 2}
    access_token: str = sign_in.json()["access_token"]

    res: Response = await async_client.post(
        "/profiles",
        json=payload,
        headers={
            "Authorization": f"Bearer {access_token}",
            "env": "testing",
            "X-API-Version": "1",
        },
    )

    assert res.status_code == 422


@pytest.mark.asyncio
async def test_invalid_name(async_client: AsyncClient, set_state, sign_in: Response):
    payload: dict = {"name": "not342a6665name"}
    access_token: str = sign_in.json()["access_token"]

    res: Response = await async_client.post(
        "/profiles",
        json=payload,
        headers={
            "Authorization": f"Bearer {access_token}",
            "env": "testing",
            "X-API-Version": "1",
        },
    )

    assert res.status_code == 502


@pytest.mark.asyncio
async def test_get_profiles(
    seed_database, async_client: AsyncClient, set_state, sign_in: Response
):
    access_token: str = sign_in.json()["access_token"]

    res: Response = await async_client.get(
        "/profiles",
        headers={
            "Authorization": f"Bearer {access_token}",
            "env": "testing",
            "X-API-Version": "1",
        },
    )
    json_res = res.json()

    assert len(json_res["data"]) >= 1


@pytest.mark.asyncio
async def test_get_profiles_not_found(
    async_client: AsyncClient, set_state, sign_in: Response
):
    access_token: str = sign_in.json()["access_token"]
    res: Response = await async_client.get(
        "/profiles",
        headers={
            "Authorization": f"Bearer {access_token}",
            "env": "testing",
            "X-API-Version": "1",
        },
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_get_stats(
    async_client: AsyncClient, seed_database, set_state, sign_in: Response
):
    access_token: str = sign_in.json()["access_token"]

    res: Response = await async_client.get(
        "/profiles/stats",
        headers={
            "Authorization": f"Bearer {access_token}",
            "env": "testing",
            "X-API-Version": "1",
        },
    )

    json_res = res.json()

    assert res.status_code == 200
    assert "total_profiles" in json_res["data"]


@pytest.mark.asyncio
async def test_export_csv(async_client: AsyncClient, seed_database, set_state, sign_in: Response):
    access_token: str = sign_in.json()["access_token"]
    res: Response = await async_client.get(
        "/profiles/export?format=csv",
        headers={
            "Authorization": f"Bearer {access_token}",
            "env": "testing",
            "X-API-Version": "1",
        },
    )

    assert res.status_code == 200
    assert "Content-Disposition" in res.headers


@pytest.mark.asyncio
async def test_get_profile(async_client: AsyncClient, set_state, sign_in: Response):
    payload: dict = {"name": "sergio"}
    access_token: str = sign_in.json()["access_token"]

    profile_res: Response = await async_client.post(
        "/profiles",
        json=payload,
        headers={
            "Authorization": f"Bearer {access_token}",
            "env": "testing",
            "X-API-Version": "1",
        },
    )

    profile_id: str = profile_res.json()["data"]["id"]

    res = await async_client.get(
        f"/profiles/{profile_id}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "env": "testing",
            "X-API-Version": "1",
        },
    )
    json_res = res.json()

    assert json_res["data"]["name"] == payload.get("name")


@pytest.mark.asyncio
async def test_unauthorized_get_profile(
    async_client: AsyncClient,
    set_state,
):
    payload: dict = {"name": "sergio"}

    res: Response = await async_client.post(
        "/profiles",
        json=payload,
    )

    assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_profile_not_found(
    async_client: AsyncClient, set_state, sign_in: Response
):
    profile_id: UUID = uuid7()
    access_token: str = sign_in.json()["access_token"]

    res = await async_client.get(
        f"/profiles/{profile_id}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "env": "testing",
            "X-API-Version": "1",
        },
    )

    assert res.status_code == 404


@pytest.mark.asyncio
async def test_search_profile(
    seed_database, async_client: AsyncClient, set_state, sign_in: Response
):
    search_query: str = "young male"
    access_token: str = sign_in.json()["access_token"]

    res: Response = await async_client.get(
        f"/profiles/search?q={search_query}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "env": "testing",
            "X-API-Version": "1",
        },
    )
    json_res = res.json()

    assert res.status_code == 200
    len(json_res["data"]) >= 1


@pytest.mark.asyncio
async def test_invalid_query(
    seed_database, async_client: AsyncClient, set_state, sign_in: Response
):
    search_query: str = "boy with name samson"
    access_token: str = sign_in.json()["access_token"]

    res: Response = await async_client.get(
        f"/profiles/search?q={search_query}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "env": "testing",
            "X-API-Version": "1",
        },
    )

    assert res.status_code == 400


@pytest.mark.asyncio
async def test_delete_profile(async_client: AsyncClient, set_state, sign_in: Response):
    payload: dict = {"name": "sergio"}
    access_token: str = sign_in.json()["access_token"]

    profile_res: Response = await async_client.post(
        "/profiles",
        json=payload,
        headers={
            "Authorization": f"Bearer {access_token}",
            "env": "testing",
            "X-API-Version": "1",
        },
    )

    profile_id: str = profile_res.json()["data"]["id"]
    res = await async_client.delete(
        f"/profiles/{profile_id}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "env": "testing",
            "X-API-Version": "1",
        },
    )

    assert res.status_code == 204
