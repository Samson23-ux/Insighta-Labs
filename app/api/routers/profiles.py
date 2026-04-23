from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession


from app.dependencies import get_session
from app.api.services.profile_service import profile_service
from app.api.schemas.profiles import Profile, ProfileResponse


profile_router = APIRouter()


@profile_router.get(
    "/profiles",
    status_code=200,
    response_model=ProfileResponse,
    description="Get all profile",
)
async def get_all_profiles(
    session: Annotated[AsyncSession, Depends(get_session)],
    gender: Annotated[str, Query(description="Filter profiles by gender (male, female)")] = None,
    age_group: Annotated[str, Query(description="Filter profiles by age_group (child, teenager, adult, senior)")] = None,
    country_id: Annotated[str, Query(description="Filter profiles by country code (2-letter ISO)")] = None,
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
        str, Query(description="Sort by age, created_at, gender_probability")
    ] = None,
    order: Annotated[str, Query(description="Order in asc or desc")] = None,
    page: Annotated[str, Query(description="Select what page to view")] = "1",
    limit: Annotated[
        str, Query(description="Set the total profiles to return per page")
    ] = "10",
):
    profiles: list[Profile] = await profile_service.get_profiles(
        session,
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
    return ProfileResponse(data=profiles)


@profile_router.get(
    "/profiles/search",
    status_code=200,
    response_model=ProfileResponse,
    description="Search for a profile using the allowed query words",
)
async def search_for_profiles(
    q: Annotated[str, Query(description="Query field to search for profiles")],
    session: Annotated[AsyncSession, Depends(get_session)],
    page: Annotated[str, Query(description="Select what page to view")] = "1",
    limit: Annotated[
        str, Query(description="Set the total profiles to return per page")
    ] = "10",
):
    profiles: list[Profile] = await profile_service.search_for_profiles(
        q,
        page,
        limit,
        session,
    )
    return ProfileResponse(data=profiles)
