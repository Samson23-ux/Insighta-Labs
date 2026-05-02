from uuid import UUID
from uuid6 import uuid7
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
        self,
        code: str,
        url_state: str,
        api_client: str,
        saved_state: str,
        code_verifier: str,
        client: AsyncClient,
        session: AsyncSession,
    ) -> tuple:
        if saved_state and url_state:
            if saved_state != url_state:
                raise AuthorizationError()

        curr_retries: int = 0
        total_retries: int = 5
        status: str = "failure"

        while curr_retries < total_retries and status == "failure":
            try:
                data: dict = {
                    "code": code,
                    "code_verifier": code_verifier,
                }
                header: dict = {"Accept": "application/json"}

                if api_client == "web" or api_client == "test":
                    data["client_id"] = settings.GITHUB_CLIENT_ID
                    data["client_secret"] = settings.GITHUB_CLIENT_SECRET
                    data["redirect_uri"] = settings.GITHUB_CALLBACK_URL

                    res: Response = await client.post(
                        settings.GITHUB_ACCESS_TOKEN_URL, data=data, headers=header
                    )
                else:
                    data["client_id"] = settings.GITHUB_CLI_CLIENT_ID
                    data["client_secret"] = settings.GITHUB_CLI_CLIENT_SECRET
                    data["redirect_uri"] = settings.REDIRECT_CLI_URI

                    client = AsyncClient(base_url=settings.AGIFY_API_URL, timeout=10.0)
                    res: Response = await client.post(
                        settings.GITHUB_ACCESS_TOKEN_URL, data=data, headers=header
                    )

                status: str = "success"
            except (ConnectError, ConnectTimeout):
                curr_retries += 1

        if status == "failure":
            raise CheckTimeoutError()

        json_res = res.json()

        if "error" in json_res:
            raise AuthorizationError()

        access_token: str = json_res["access_token"]

        user_profile: dict = await self.get_user_profile(client, access_token)

        user_email: str = user_profile.get("email")

        if not user_email:
            user_emails: list[dict] = await self.get_user_emails(client, access_token)
            user_email: dict = next(e for e in user_emails if e["primary"])

            if not user_email["verified"]:
                raise UnverifiedEmailError()

            user_profile["email"] = user_email["email"]

        user: User = await user_service_v1.get_user_by_email(user_email, session)

        try:
            if user:
                if user.role == "admin":
                    copied_user: dict = user_profile.copy()
                    copied_user["github_id"] = str(copied_user["id"])
                    copied_user["username"] = copied_user["login"]

                    copied_user.pop("id")
                    copied_user.pop("login")
                    copied_user.pop("created_at")

                    for k, v in copied_user.items():
                        setattr(user, k, v)

                    await user_service_v1.update_user(user, session)
            else:
                user: User = User(
                    id=uuid7(),
                    github_id=str(user_profile["id"]),
                    username=user_profile["login"],
                    email=user_profile["email"],
                    avatar_url=user_profile["avatar_url"],
                    role="analyst",
                    last_login_at=datetime.now(timezone.utc),
                )

                await user_service_v1.create_user(user, session)
            user_id = user.id

            token_data: TokenDataV1 = TokenDataV1(id=user_id)
            auth_tokens: dict = await prepare_tokens(user_id, token_data)

            refresh_token_db = auth_tokens.pop("refresh_token_db")
            await auth_repo_v1.add_token_to_db(refresh_token_db, session)

            if not api_client:
                await client.aclose()
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise ServerError() from e

        user_profile_out: dict = {
            "id": user_profile["id"],
            "username": user_profile["login"],
            "email": user_profile["email"],
            "avatar_url": user_profile["avatar_url"],
        }

        return auth_tokens, user_profile_out

    async def create_access_token(
        self, refresh_token: str, session: AsyncSession
    ) -> dict:
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
