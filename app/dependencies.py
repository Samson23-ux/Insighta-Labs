from sqlalchemy.ext.asyncio import AsyncSession


from app.database.session import async_session


async def get_session():
    try:
        session: AsyncSession = async_session()
        yield session
    finally:
        await session.close()
