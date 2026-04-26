from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession


from app.api.models.users import User
from app.api.repo.user_repo import user_repo_v1
from app.core.exceptions import UserNotFoundError


class UserServiceV1:
    async def get_user_by_id(self, user_id: UUID, session: AsyncSession) -> User:
        user: User | None = await user_repo_v1.get_user_by_id(user_id, session)

        if not user:
            raise UserNotFoundError()

        return user


user_service_v1 = UserServiceV1()
