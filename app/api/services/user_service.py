from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession


from app.api.models.users import User
from app.api.repo.user_repo import user_repo_v1
from app.core.exceptions import UserNotFoundError
from app.api.schemas.users import UserV1 as UserSchemaV1


class UserServiceV1:
    async def get_user_by_id(self, user_id: UUID, session: AsyncSession) -> User:
        user: User | None = await user_repo_v1.get_user_by_id(user_id, session)

        if not user:
            raise UserNotFoundError(user_id=user_id)

        return user

    async def get_user_by_email(self, user_email: str, session: AsyncSession) -> User:
        user: User | None = await user_repo_v1.get_user_by_email(user_email, session)
        return user

    async def get_user_account(self, curr_user: User):
        user_out: UserSchemaV1 = UserSchemaV1.model_validate(curr_user)
        return user_out

    async def create_user(self, user: User, session: AsyncSession):
        await user_repo_v1.add_user_to_db(user, session)

    async def update_user(self, user: User, session: AsyncSession):
        await user_repo_v1.add_user_to_db(user, session)


user_service_v1 = UserServiceV1()
