from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession


from app.api.models.users import User


class UserRepoV1:
    async def get_user_by_id(self, user_id: UUID, session: AsyncSession) -> User | None:
        stmt = select(User).where(and_(User.id == user_id, User.is_active.is_(True)))
        res = await session.execute(stmt)
        user: User | None = res.scalar()
        return user

    async def get_user_by_email(
        self, user_email: UUID, session: AsyncSession
    ) -> User | None:
        stmt = select(User).where(and_(User.email == user_email))
        res = await session.execute(stmt)
        user: User | None = res.scalar()
        return user
    
    async def add_user_to_db(self, user: User, session: AsyncSession):
        session.add(user)
        await session.flush()
        await session.refresh(user)


user_repo_v1 = UserRepoV1()
