from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession


from app.database.session import async_session


async def get_session():
    try:
        session: AsyncSession = async_session()
        yield session
    finally:
        await session.close()

async def get_client(request: Request):
    agify_client = request.app.state.agify
    genderize_client = request.app.state.genderize
    nationalize_client = request.app.state.nationalize

    return agify_client, genderize_client, nationalize_client
