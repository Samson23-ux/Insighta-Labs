from uuid import uuid4
from typing import Annotated
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Request, Depends, Response, Query, Header


from app.limiter import limiter
from app.core.config import settings
from app.api.models.users import User
from app.api.schemas.users import UserResponseV1, UserV1
from app.api.services.user_service import user_service_v1
from app.api.services.auth_service import auth_service_v1
from app.dependencies import get_session, get_current_active_user
from app.core.security import hash_code_challenge, get_code_verifier
from app.core.exceptions import VersionError, InvalidParameterError, AuthorizationError
from app.api.schemas.auth import (
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
@limiter.limit("10/minute")
async def sign_in(
    request: Request,
    x_api_version: Annotated[str, Header()],
    api_client: Annotated[
        str, Query(description="Client attribute must be set to web for web clients")
    ] = None,
):
    if not x_api_version:
        raise VersionError()

    state: str = str(uuid4())
    code_verifier: str = get_code_verifier()
    code_challenge: str = await hash_code_challenge(code_verifier)

    client_data: dict = {"state": state, "code_verifier": code_verifier}

    if api_client:
        accepted_clients: list = ["web", "cli", "test"]
        if api_client.lower() not in accepted_clients:
            raise InvalidParameterError(param=api_client)
        else:
            client_data["client"] = api_client.lower()

    request.session["client_data"] = client_data

    url = (
        f"{settings.GITHUB_AUTHORIZE_URL}"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&redirect_uri={settings.GITHUB_CALLBACK_URL}"
        f"&scope=read:user user:email"
        f"&state={state}"
        f"&code_challenge={code_challenge}"
        f"&code_challenge_method=S256"
    )
    return RedirectResponse(url, 302)


@auth_router_v1.get(
    "/auth/github/callback",
    status_code=200,
    response_model=LoginResponseV1,
    description="Github callback url",
)
@limiter.limit("10/minute")
async def github_callback(
    request: Request,
    response: Response,
    x_api_version: Annotated[str, Header()],
    session: Annotated[AsyncSession, Depends(get_session)],
    # api_client: Annotated[
    #     str, Query(description="Client attribute must be set to web for web clients")
    # ] = None,
    error: str = None,
    state: str = None,
    code: str = None,
    code_verifier: str = None,
):
    saved_state = None
    github_client = None

    if not x_api_version:
        raise VersionError()

    if error:
        raise AuthorizationError()
    
    client_data: dict = request.session.get("client_data")
    api_client: str = client_data.get("client")

    if api_client == "web" or api_client == "test":
        github_client = request.app.state.github
        saved_state: str = client_data.get("state")
        code_verifier: str = client_data.get("code_verifier")

    auth_tokens, user_profile = await auth_service_v1.sign_up_with_github(
        code,
        state,
        api_client,
        saved_state,
        code_verifier,
        github_client,
        session,
    )

    if api_client == "web":
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

        return RedirectResponse(f"{settings.FRONTEND_URL}/#/dashboard")
    else:
        return LoginResponseV1(**auth_tokens, user_profile=user_profile)


@auth_router_v1.get(
    "/auth/me",
    status_code=200,
    response_model=UserResponseV1,
    description="Get current user",
)
@limiter.limit("10/minute")
async def get_user(
    request: Request,
    x_api_version: Annotated[str, Header()],
    curr_user: Annotated[User, Depends(get_current_active_user)],
):
    if not x_api_version:
        raise VersionError()

    user: UserV1 = await user_service_v1.get_user_account(curr_user)
    return UserResponseV1(data=user)


@auth_router_v1.post(
    "/auth/refresh",
    status_code=201,
    response_model=TokenResponseV1,
    description="Create a new access token using a valid refresh token",
)
@limiter.limit("10/minute")
async def create_access_token(
    request: Request,
    response: Response,
    x_api_version: Annotated[str, Header()],
    auth_token: AuthTokenRequestV1,
    session: Annotated[AsyncSession, Depends(get_session)],
    api_client: Annotated[
        str, Query(description="Client attribute must be set to web for web clients")
    ] = None,
):
    web_client: bool = False

    if not x_api_version:
        raise VersionError()

    if api_client:
        if api_client.lower() != "web":
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
@limiter.limit("10/minute")
async def log_user_out(
    request: Request,
    x_api_version: Annotated[str, Header()],
    auth_token: AuthTokenRequestV1,
    curr_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    api_client: Annotated[
        str, Query(description="Client attribute must be set to web for web clients")
    ] = None,
):
    web_client: bool = False

    if not x_api_version:
        raise VersionError()

    if api_client:
        if api_client.lower() != "web":
            raise InvalidParameterError(param="client")
        else:
            web_client: bool = True

    if web_client:
        refresh_token: str = request.cookies.get("refresh_token")
    else:
        refresh_token: str = auth_token.refresh_token

    await auth_service_v1.log_out(refresh_token, curr_user, session)
    return LogoutResponseV1(message="Log out completed sucessfully")
