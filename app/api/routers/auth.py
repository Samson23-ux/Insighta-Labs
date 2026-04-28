from uuid import uuid4
from typing import Annotated
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Request, Depends, Response, Query


from app.core.config import settings
from app.api.models.users import User
from app.core.security import hash_code_challenge
from app.api.services.auth_service import auth_service_v1
from app.dependencies import get_session, get_current_active_user
from app.core.exceptions import VersionError, InvalidParameterError, AuthorizationError
from app.api.schemas.auth import (
    APIClientV1,
    LoginResponseV1,
    TokenResponseV1,
    LogoutResponseV1,
    AuthTokenRequestV1,
)


auth_router_v1 = APIRouter()


@auth_router_v1.get(
    "/auth/github",
    status_code=302,
    response_class=RedirectResponse,
    description="Sign up with github",
)
async def sign_in(
    request: Request,
    api_client: Annotated[
        str, Query(description="Client attribute must be set to web for web clients")
    ] = None,
):
    version: str | None = request.headers.get("X-API-Version")

    if not version:
        raise VersionError()

    state: str = str(uuid4())
    code_challenge: str = str(uuid4())
    hashed_code_challenge: str = await hash_code_challenge(code_challenge)

    client_data: dict = {"state": state, "code_challenge": code_challenge}

    if api_client:
        if api_client.lower() != "web":
            raise InvalidParameterError(param="client")
        else:
            client_data["client"] = api_client.lower()

    request.session["client_data"] = client_data

    url = (
        f"{settings.GITHUB_AUTHORIZE_URL}"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&redirect_uri={settings.GITHUB_CALLBACK_URL}"
        f"&scope=user&state={state}"
        f"&code_challenge={hashed_code_challenge}"
        f"&code_challenge_method=S256"
    )
    return RedirectResponse(url, 302)


@auth_router_v1.get(
    "/auth/github/callback",
    status_code=200,
    response_model=LoginResponseV1,
    description="Github callback url",
)
async def github_callback(
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    error: str = None,
    state: str = None,
    code: str = None,
    code_verifier: str = None,
):
    version: str | None = request.headers.get("X-API-Version")

    if not version:
        raise VersionError()

    if error:
        raise AuthorizationError()

    github_client = request.app.state.github

    client_data: dict = request.session.get("client_data")

    client: str = client_data.get("client")
    saved_state: str = client_data.get("state")
    code_verifier: str = client_data.get("code_challenge")

    auth_tokens, user_profile = await auth_service_v1.sign_up_with_github(
        request.url, code, saved_state, state, code_verifier, github_client, session
    )

    if client:
        response.set_cookie(
            key="access_token",
            value=auth_tokens["access_token"],
            httponly=True,
            secure=settings.ENVIRONMENT == "production",
            samesite="lax",
            max_age=180,
        )

        response.set_cookie(
            key="refresh_token",
            value=auth_tokens["refresh_token"],
            httponly=True,
            secure=settings.ENVIRONMENT == "production",
            samesite="lax",
            max_age=300,
        )
    return LoginResponseV1(**auth_tokens, user_profile=user_profile)


@auth_router_v1.post(
    "/auth/refresh",
    status_code=201,
    response_model=TokenResponseV1,
    description="Create a new access token using a valid refresh token",
)
async def create_access_token(
    request: Request,
    response: Response,
    api_client: APIClientV1,
    auth_token: AuthTokenRequestV1,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    web_client: bool = False
    version: str | None = request.headers.get("X-API-Version")

    if not version:
        raise VersionError()

    if api_client.client:
        if api_client.client.lower() != "web":
            raise InvalidParameterError(param="client")
        else:
            web_client: bool = True

    if web_client:
        refresh_token: str = request.cookies.get("refresh_token")
    else:
        refresh_token: str = auth_token.refresh_token

    auth_tokens: dict = await auth_service_v1.create_access_token(
        refresh_token, session
    )

    if web_client:
        response.set_cookie(
            key="access_token",
            value=auth_tokens["access_token"],
            httponly=True,
            secure=settings.ENVIRONMENT == "production",
            samesite="lax",
            max_age=180,
        )

        response.set_cookie(
            key="refresh_token",
            value=auth_tokens["refresh_token"],
            httponly=True,
            secure=settings.ENVIRONMENT == "production",
            samesite="lax",
            max_age=300,
        )
    return TokenResponseV1(**auth_tokens)


@auth_router_v1.post(
    "/auth/logout",
    status_code=201,
    response_model=LogoutResponseV1,
    description="Log out account",
)
async def log_user_out(
    request: Request,
    api_client: APIClientV1,
    auth_token: AuthTokenRequestV1,
    curr_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    web_client: bool = False
    version: str | None = request.headers.get("X-API-Version")

    if not version:
        raise VersionError()

    if api_client.client:
        if api_client.client.lower() != "web":
            raise InvalidParameterError(param="client")
        else:
            web_client: bool = True

    if web_client:
        refresh_token: str = request.cookies.get("refresh_token")
    else:
        refresh_token: str = auth_token.refresh_token

    await auth_service_v1.log_out(refresh_token, curr_user, session)
    return LogoutResponseV1(message="Log out completed sucessfully")
