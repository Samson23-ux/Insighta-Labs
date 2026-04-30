import httpx
from uuid import UUID
from typing import Annotated
from fastapi import Request, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


from app.core.config import settings
from app.api.models.users import User
from app.core.security import decode_token
from app.database.session import async_session
from app.api.services.user_service import user_service_v1
from app.core.exceptions import AuthenticationError, AuthorizationError


bearer_scheme = HTTPBearer(auto_error=False)


async def get_session():
    try:
        session: AsyncSession = async_session()
        yield session
    finally:
        await session.close()


async def get_client(request: Request, api_client: Annotated[
        str, Query(description="Client attribute must be set to web for web clients")
    ] = None
):
    if api_client:
        agify_client = request.app.state.agify
        genderize_client = request.app.state.genderize
        nationalize_client = request.app.state.nationalize
    else:
        agify_client = httpx.AsyncClient(base_url=settings.AGIFY_API_URL, timeout=10.0)
        genderize_client = httpx.AsyncClient(base_url=settings.GENDERIZE_API_URL, timeout=10.0)
        nationalize_client = httpx.AsyncClient(
            base_url=settings.NATIONALIZE_API_URL, timeout=10.0
        )

    return agify_client, genderize_client, nationalize_client


async def get_current_user(
    request: Request,
    creds: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    session: AsyncSession = Depends(get_session),
):
    token = None

    if creds:
        if creds.credentials:
            token: str = creds.credentials
    else:
        token: str = request.cookies.get("access_token")

    if not token:
        raise AuthenticationError()

    key: str = settings.ACCESS_TOKEN_SECRET_KEY
    payload: dict = await decode_token(token, key)

    if not payload:
        raise AuthenticationError()

    user_id: UUID = payload.get("sub")
    user: User = await user_service_v1.get_user_by_id(user_id, session)

    return user


async def get_current_active_user(curr_user: User = Depends(get_current_user)):
    if curr_user.is_active is False:
        raise AuthorizationError()
    return curr_user


def required_roles(roles: list[str]):
    async def role_checker(curr_user: User = Depends(get_current_active_user)):
        if curr_user.role not in roles:
            raise AuthorizationError()
        return curr_user

    return role_checker
