from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_


from app.api.models.users import User

class UserRepoV1:
    async def get_user_by_id(self, user_id: UUID, session: AsyncSession) -> User | None:
        stmt = select(User).where(and_(User.id == user_id, User.is_active.is_(True)))
        res = await session.execute(stmt)
        user: User | None = res.scalar()
        return user

user_repo_v1 = UserRepoV1()
