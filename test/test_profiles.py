import pytest
from httpx import AsyncClient, Response


@pytest.mark.asyncio
async def test_get_profiles(async_client: AsyncClient):
    res: Response = await async_client.get("/profiles")
    json_res = res.json()
    print(res.url)

    assert len(json_res["data"]) >= 1


@pytest.mark.asyncio
async def test_get_profiles_not_found(async_client: AsyncClient):
    res: Response = await async_client.get("/profiles")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_search_profile(async_client: AsyncClient):
    search_query: str = "young male"

    res: Response = await async_client.get(f"/profiles/search?q={search_query}")
    json_res = res.json()

    assert res.status_code == 200
    len(json_res["data"]) >= 1


@pytest.mark.asyncio
async def test_invalid_query(async_client: AsyncClient):
    search_query: str = "boy with name samson"

    res: Response = await async_client.get(f"/profiles/search?q={search_query}")

    assert res.status_code == 400
