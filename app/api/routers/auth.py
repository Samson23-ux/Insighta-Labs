from typing import Annotated
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Request, Depends, Response


from app.core.config import settings
from app.api.models.users import User
from app.utils import get_random_string
from app.core.exceptions import VersionError
from app.core.security import hash_code_challenge
from app.api.services.auth_service import auth_service_v1
from app.dependencies import get_session, get_current_active_user
from app.api.schemas.auth import TokenResponseV1, AccessTokenCreateV1, LogoutResponseV1


auth_router_v1 = APIRouter()


@auth_router_v1.get(
    "/auth/github",
    status_code=302,
    response_class=RedirectResponse,
    description="Sign up with github",
)
async def sign_in(request: Request):
    version: str | None = request.headers.get("X-API-Version")

    if not version:
        raise VersionError()

    state: str = await get_random_string()
    code_challenge: str = await get_random_string()
    hashed_code_challenge: str = hash_code_challenge(code_challenge)

    request.session["state"] = state
    request.session["code_challenge"] = code_challenge

    return RedirectResponse(
        f"""
            {settings.GITHUB_AUTHORIZE_URL}
            ?client_id={settings.GITHUB_CLIENT_ID}
            &redirect_uri={settings.GITHUB_CALLBACK_URL}
            &scope=user&state={state}
            &code_challenge={hashed_code_challenge}
            &code_challenge_method=S256
        """,
        302,
    )


@auth_router_v1.get(
    "/auth/github/callback",
    status_code=200,
    response_model=TokenResponseV1,
    description="Github callback url",
)
async def github_callback(
    request: Request, response: Response, session: Annotated[AsyncSession, Depends(get_session)]
):
    version: str | None = request.headers.get("X-API-Version")

    if not version:
        raise VersionError()

    auth_tokens: dict = await auth_service_v1.sign_up_with_github(request, session)

    response.set_cookie(
        key="refresh_token",
        value=auth_tokens["refresh_token"],
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax"
    )
    return TokenResponseV1(**auth_tokens)


@auth_service_v1.post(
    "/auth/refresh",
    status_code=201,
    response_model=TokenResponseV1,
    description="Create a new access token using a valid refresh token",
)
async def create_access_token(
    request: Request,
    response: Response,
    refresh_token: AccessTokenCreateV1,
    session: Annotated[AsyncSession, Depends(get_session)]
):
    version: str | None = request.headers.get("X-API-Version")

    if not version:
        raise VersionError()

    auth_tokens: dict = await auth_service_v1.create_access_token(refresh_token, session)

    response.set_cookie(
        key="refresh_token",
        value=auth_tokens["refresh_token"],
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax"
    )
    return TokenResponseV1(**auth_tokens)


@auth_service_v1.post(
    "/auth/logout",
    status_code=201,
    response_model=LogoutResponseV1,
    description="Log out account",
)
async def log_user_out(
    request: Request,
    curr_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_session)]
):
    refresh_token: str = request.cookies.get("refresh_token")
    version: str | None = request.headers.get("X-API-Version")

    if not version:
        raise VersionError()

    await auth_service_v1.log_out(refresh_token, curr_user, session)
    return LogoutResponseV1(message="Log out completed sucessfully")
