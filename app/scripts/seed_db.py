import json
import asyncio
import aiofiles
from uuid6 import uuid7
from pathlib import Path
from sqlalchemy import Sequence
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


from app.api.models.profiles import Profile
from app.core.exceptions import ServerError
from app.database.session import async_engine
from app.api.services.profile_service import profile_service


async_session = async_sessionmaker(
    bind=async_engine,
    autocommit=False,
    autoflush=False,
    class_=AsyncSession,
)


async def seed_profiles():
    """
    database bulk insert is used for faster insertion
    it is wrapped around a try-except block which rollbacks
    changes if an exception is thrown ensuring atomicity of insertion
    """
    try:
        limit: int = 50
        session: AsyncSession = async_session()
        profiles: Sequence[Profile] = await profile_service._get_profiles(
            limit, session
        )

        # only insert data if not inserted already to prevent duplicates and ensure idempotency
        if not profiles:
            file_path: Path = Path(__file__).parent / "seed_profiles.json"

            try:
                async with aiofiles.open(file_path, "r", encoding="utf-8") as json_file:
                    data: dict = json.loads(await json_file.read())
                    profiles: list[dict] = data.get("profiles")
            except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as e:
                raise ServerError() from e

            for profile in profiles:
                profile["id"] = uuid7()
                profile["created_at"] = datetime.now(timezone.utc)

            await profile_service.create_profiles(profiles, session)
            await session.commit()
    except Exception as e:
        await session.rollback()
        raise ServerError() from e
    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(seed_profiles())
