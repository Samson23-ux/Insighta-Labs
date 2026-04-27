from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession


from app.api.models.auth import RefreshToken
from app.api.schemas.auth import TokenStatusV1


class AuthRepoV1:
    async def get_refresh_token(self, token_id: UUID, session: AsyncSession):
        stmt = select(RefreshToken).where(
            and_(
                RefreshToken.id == token_id, RefreshToken.status == TokenStatusV1.VALID
            )
        )

        res = await session.execute(stmt)
        token: RefreshToken | None = res.scalar()
        return token

    async def add_token_to_db(self, refresh_token: RefreshToken, session: AsyncSession):
        await session.add(refresh_token)
        await session.flush()
        await session.refresh(refresh_token)


auth_repo_v1 = AuthRepoV1()
