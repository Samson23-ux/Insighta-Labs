from uuid6 import uuid7
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession


from app.core.config import settings
from app.api.models.users import User
from app.database.session import async_session
from app.api.services.user_service import user_service_v1


async def create_admin():
    """the admin is created initially with some fake data representation
    then the admin profile is updated with the correct data on sign in"""

    session: AsyncSession = async_session()

    try:
        admin_email: str = settings.ADMIN_EMAIL
        admin_exist: User | None = await user_service_v1.get_user_by_email(
            admin_email, session
        )

        if not admin_exist:
            admin_user: User = User(
                id=uuid7(),
                github_id=str(uuid7()),
                username="fake_username",
                email=admin_email,
                avatar_url="fake_avatar_url",
                role="admin",
                last_login_at=datetime.now(timezone.utc),
            )

            await user_service_v1.create_user(admin_user, session)
            await session.commit()
    except Exception:
        await session.rollback()
    finally:
        await session.close()
