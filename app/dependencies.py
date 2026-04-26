from uuid import UUID
from fastapi import Request, Security, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


from app.core.config import settings
from app.api.models.users import User
from app.core.security import decode_token
from app.database.session import async_session
from app.api.services.user_service import user_service_v1
from app.core.exceptions import AuthenticationError, AuthorizationError


bearer_scheme = HTTPBearer()


async def get_session():
    try:
        session: AsyncSession = async_session()
        yield session
    finally:
        await session.close()


async def get_client(request: Request):
    agify_client = request.app.state.agify
    genderize_client = request.app.state.genderize
    nationalize_client = request.app.state.nationalize

    return agify_client, genderize_client, nationalize_client


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: AsyncSession = Depends(get_session),
):
    token: str = creds.credentials
    key: str = settings.ACCESS_TOKEN_SECRET_KEY
    payload: dict = await decode_token(token, key)

    if not payload:
        raise AuthenticationError()

    user_id: UUID = payload.get("sub")

    user: User = await user_service_v1.get_user_by_id(user_id, db)

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
