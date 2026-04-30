from uuid import UUID
from pathlib import Path
from typing import Annotated
from datetime import datetime, timezone
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Query, Request


from app.api.models.users import User
from app.core.exceptions import VersionError
from app.api.services.profile_service import profile_service_v1
from app.dependencies import get_session, get_client, required_roles
from app.api.schemas.profiles import (
    ProfileV1,
    ProfileExistV1,
    ProfileCreateV1,
    ProfileResponseV1,
    PaginatedResponseV1,
)


profile_router_v1 = APIRouter()


@profile_router_v1.get(
    "/profiles",
    status_code=200,
    response_model=PaginatedResponseV1,
    description="Get all profile",
)
async def get_all_profiles(
    request: Request,
    _: Annotated[User, Depends(required_roles(["analyst", "admin"]))],
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

    if not version:
        raise VersionError()

    data: dict = await profile_service_v1.get_profiles(
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

    links: dict = data.get("links")
    profiles: list[ProfileV1] = data.get("profiles")
    return PaginatedResponseV1(
        data=profiles, page=int(page), limit=int(limit), links=links
    )


@profile_router_v1.get(
    "/profiles/search",
    status_code=200,
    response_model=PaginatedResponseV1,
    description="Search for a profile using the allowed query words",
)
async def search_for_profiles(
    request: Request,
    _: Annotated[User, Depends(required_roles(["analyst", "admin"]))],
    session: Annotated[AsyncSession, Depends(get_session)],
    q: Annotated[str, Query(description="Query field to search for profiles")],
    page: Annotated[str, Query(description="Select what page to view")] = "1",
    limit: Annotated[
        str, Query(description="Set the total profiles to return per page")
    ] = "10",
):
    version: str | None = request.headers.get("X-API-Version")
    if not version:
        raise VersionError()

    data: dict = await profile_service_v1.search_for_profiles(
        q,
        page,
        limit,
        session,
    )

    links: dict = data.get("links")
    profiles: list[ProfileV1] = data.get("profiles")
    return PaginatedResponseV1(
        data=profiles, page=int(page), limit=int(limit), links=links
    )


@profile_router_v1.get(
    "/profiles/export",
    status_code=200,
    response_class=FileResponse,
    description="Get profiles as a csv file",
)
async def export_csv(
    request: Request,
    format: Annotated[
        str, Query(description="Export format. Only csv format is supported")
    ],
    _: Annotated[User, Depends(required_roles(["analyst", "admin"]))],
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

    if not version:
        raise VersionError()

    export_path: Path = await profile_service_v1.export_csv(
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

    filename: str = f"profiles_{datetime.now(timezone.utc).isoformat()}"
    return FileResponse(
        path=export_path,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@profile_router_v1.get(
    "/profiles/{profile_id}",
    status_code=200,
    response_model=ProfileResponseV1,
    description="Get a profile",
)
async def get_profile_by_id(
    request: Request,
    profile_id: UUID,
    _: Annotated[User, Depends(required_roles(["analyst", "admin"]))],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    version: str | None = request.headers.get("X-API-Version")

    if not version:
        raise VersionError()

    profile: ProfileV1 = await profile_service_v1.get_profile(profile_id, session)
    return ProfileResponseV1(data=profile)


@profile_router_v1.post(
    "/profiles",
    status_code=201,
    response_model=ProfileExistV1 | ProfileResponseV1,
    description="Create a profile",
)
async def create_profile(
    request: Request,
    profile_create: ProfileCreateV1,
    _: Annotated[User, Depends(required_roles(["admin"]))],
    client: Annotated[tuple, Depends(get_client)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    version: str | None = request.headers.get("X-API-Version")

    if not version:
        raise VersionError()

    profile_data: dict = await profile_service_v1.create_profile(
        profile_create, client, session
    )
    exists: bool = profile_data.get("exists")
    user_profile: ProfileV1 = profile_data.get("data")

    return (
        ProfileExistV1(data=user_profile)
        if exists
        else ProfileResponseV1(data=user_profile)
    )


@profile_router_v1.delete(
    "/profiles/{profile_id}", status_code=204, description="Delete a profile"
)
async def delete_profile(
    request: Request,
    profile_id: UUID,
    _: Annotated[User, Depends(required_roles(["admin"]))],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    version: str | None = request.headers.get("X-API-Version")

    if not version:
        raise VersionError()

    await profile_service_v1.delete_profile(profile_id, session)
