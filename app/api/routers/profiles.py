from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Query, Request


from app.dependencies import get_session
from app.api.services.profile_service import profile_service_v1
from app.api.schemas.profiles import ProfileV1, ProfileResponseV1


profile_router_v1 = APIRouter()


@profile_router_v1.get(
    "/profiles",
    status_code=200,
    response_model=ProfileResponseV1,
    description="Get all profile",
)
async def get_all_profiles(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    gender: Annotated[
        str, Query(description="Filter profiles by gender (male, female)")
    ] = None,
    age_group: Annotated[
        str,
        Query(
            description="Filter profiles by age_group (child, teenager, adult, senior)"
        ),
    ] = None,
    country_id: Annotated[
        str, Query(description="Filter profiles by country code (2-letter ISO)")
    ] = None,
    min_age: Annotated[
        str, Query(description="Set a minimum age to view profiles from")
    ] = None,
    max_age: Annotated[
        str, Query(description="Set a maximum age to view profiles to")
    ] = None,
    min_gender_probability: Annotated[
        str, Query(description="Set a minimum age probability to view profiles from")
    ] = None,
    min_country_probability: Annotated[
        str,
        Query(description="Set a minimum country probability to view profiles from"),
    ] = None,
    sort_by: Annotated[
        str, Query(description="Sort by any of (age, created_at, gender_probability)")
    ] = None,
    order: Annotated[str, Query(description="Order in asc or desc")] = None,
    page: Annotated[str, Query(description="Select what page to view")] = "1",
    limit: Annotated[
        str, Query(description="Set the total profiles to return per page")
    ] = "10",
):
    version: str | None = request.headers.get("X-API-Version")
    profiles: list[ProfileV1] = await profile_service_v1.get_profiles(
        session,
        version,
        gender,
        age_group,
        country_id,
        min_age,
        max_age,
        min_gender_probability,
        min_country_probability,
        sort_by,
        order,
        page,
        limit,
    )
    return ProfileResponseV1(data=profiles, page=int(page), limit=int(limit), total=2026)


@profile_router_v1.get(
    "/profiles/search",
    status_code=200,
    response_model=ProfileResponseV1,
    description="Search for a profile using the allowed query words",
)
async def search_for_profiles(
    request: Request,
    q: Annotated[str, Query(description="Query field to search for profiles")],
    session: Annotated[AsyncSession, Depends(get_session)],
    page: Annotated[str, Query(description="Select what page to view")] = "1",
    limit: Annotated[
        str, Query(description="Set the total profiles to return per page")
    ] = "10",
):
    version: str | None = request.headers.get("X-API-Version")
    profiles: list[ProfileV1] = await profile_service_v1.search_for_profiles(
        q,
        page,
        limit,
        version,
        session,
    )
    return ProfileResponseV1(data=profiles, page=int(page), limit=int(limit), total=2026)
