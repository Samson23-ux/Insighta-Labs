from uuid import UUID
from uuid6 import uuid7
from fastapi import Request
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient, ConnectError, ConnectTimeout, Response


from app.core.config import settings
from app.api.models.users import User
from app.api.models.auth import RefreshToken
from app.api.repo.auth_repo import auth_repo_v1
from app.api.services.user_service import user_service_v1
from app.core.security import prepare_tokens, decode_token
from app.api.schemas.auth import TokenDataV1, TokenStatusV1
from app.core.exceptions import (
    ServerError,
    CheckTimeoutError,
    AuthorizationError,
    AuthenticationError,
    UnverifiedEmailError,
)


class AuthServiceV1:
    async def get_user_profile(
        self, github_client: AsyncClient, access_token: str
    ) -> dict:
        curr_retries: int = 0
        total_retries: int = 5
        status: str = "failure"

        while curr_retries < total_retries and status == "failure":
            try:
                res: Response = await github_client.get(
                    settings.GITHUB_USER_URL,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json",
                    },
                )

                status: str = "success"
            except (ConnectError, ConnectTimeout):
                curr_retries += 1

        json_res = res.json()
        return json_res

    async def get_user_emails(
        self, github_client: AsyncClient, access_token: str
    ) -> list[dict]:
        curr_retries: int = 0
        total_retries: int = 5
        status: str = "failure"

        while curr_retries < total_retries and status == "failure":
            try:
                res: Response = await github_client.get(
                    settings.GITHUB_EMAIL_URL,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json",
                    },
                )

                status: str = "success"
            except (ConnectError, ConnectTimeout):
                curr_retries += 1

        json_res = res.json()
        return json_res

    async def sign_up_with_github(
        self, request: Request, session: AsyncSession
    ) -> dict:
        client_data: dict = request.session.get("client_data")

        state: str = client_data.get("state")
        code_verifier: str = client_data.get("code_challenge")

        code: str = request.query_params.get("code")
        url_state: str = request.query_params.get("state")

        if state != url_state:
            raise AuthorizationError()

        curr_retries: int = 0
        total_retries: int = 5
        status: str = "failure"

        github_client: AsyncClient = request.app.state.github

        while curr_retries < total_retries and status == "failure":
            try:
                data: dict = {
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": request.url,
                    "code_verifier": code_verifier,
                }
                header: dict = {"Accept": "application/json"}
                res: Response = await github_client.post(
                    settings.GITHUB_ACCESS_TOKEN_URL, data=data, headers=header
                )

                status: str = "success"
                res.raise_for_status()
            except (ConnectError, ConnectTimeout):
                curr_retries += 1

        if status == "failure":
            raise CheckTimeoutError()

        json_res = res.json()

        if "error" in json_res:
            raise AuthorizationError()

        access_token: str = json_res["access_token"]

        user_profile: dict = await self.get_user_profile(github_client, access_token)

        if "email" not in user_profile:
            user_emails: list[dict] = await self.get_user_emails(
                github_client, access_token
            )
            user_email: dict = next(e for e in user_emails if e["primary"])

        if not user_email["verified"]:
            raise UnverifiedEmailError()

        user_profile["email"] = user_email["email"]

        user: User = await user_service_v1.get_user_by_email(user_email, session)
        if not user:
            user: User = User(
                id=uuid7(),
                github_id=user_profile["id"],
                username="",
                email=user_profile["email"],
                avatar_url="",
                role="analyst",
                last_login_at=datetime.now(timezone.utc),
            )

            try:
                await user_service_v1.create_user(user, session)
                await session.commit()
            except Exception as e:
                await session.rollback()
                raise ServerError() from e

        token_data: TokenDataV1 = TokenDataV1(id=user.id)
        auth_tokens: dict = await prepare_tokens(user.id, token_data)

        refresh_token_db = auth_tokens.pop("refresh_token_db")
        await auth_repo_v1.add_token_to_db(refresh_token_db, session)

        return auth_tokens

    async def create_access_token(self, refresh_token: str, session: AsyncSession) -> dict:
        payload: dict = await decode_token(
            refresh_token, settings.REFRESH_TOKEN_SECRET_KEY
        )

        if not payload:
            raise AuthenticationError()

        token_id: UUID = payload["jti"]
        refresh_token_db: RefreshToken | None = await auth_repo_v1.get_refresh_token(
            token_id, session
        )

        if not refresh_token_db:
            raise AuthenticationError()

        refresh_token_db.status = TokenStatusV1.USED
        refresh_token_db.used_at = datetime.now(timezone.utc)
        await auth_repo_v1.add_token_to_db(refresh_token_db, session)

        user_id: UUID = refresh_token_db.user.id
        token_data: TokenDataV1 = TokenDataV1(id=user_id)
        auth_tokens: dict = await prepare_tokens(user_id, token_data)

        refresh_token_db = auth_tokens.pop("refresh_token_db")
        await auth_repo_v1.add_token_to_db(refresh_token_db, session)

        return auth_tokens

    async def log_out(self, refresh_token: str, curr_user: User, session: AsyncSession):
        payload: dict = await decode_token(
            refresh_token, settings.REFRESH_TOKEN_SECRET_KEY
        )

        if not payload:
            raise AuthenticationError()

        token_id: UUID = payload["jti"]
        refresh_token_db: RefreshToken | None = await auth_repo_v1.get_refresh_token(
            token_id, session
        )

        refresh_token_db.status = TokenStatusV1.REVOKED
        refresh_token_db.revoked_at = datetime.now(timezone.utc)
        await auth_repo_v1.add_token_to_db(refresh_token_db, session)

        curr_user.is_active = False
        await user_service_v1.update_user(curr_user, session)


auth_service_v1 = AuthServiceV1()

