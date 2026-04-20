from sqlalchemy.ext.asyncio import AsyncSession


from app.api.models.profiles import Profile
from app.api.schemas.profiles import Profile as ProfileSchema


class ProfileService:
    async def get_profiles(
        self,
        session: AsyncSession,
        gender: str | None,
        age_group: str | None,
        country_id: str | None,
        min_age: str | None,
        max_age: str | None,
        min_gender_probability: str | None,
        min_country_probability: str | None,
        sort_by: str | None,
        order: str | None,
        page: str,
        limit: str,
    ) -> list[ProfileSchema]:
        pass

profile_service: ProfileService = ProfileService()
