from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, Sequence, func, desc, insert


from app.api.models.profiles import Profile


class ProfileRepo:
    async def add_profiles_to_db(self, profiles: list[dict], session: AsyncSession):
        await session.execute(insert(Profile), profiles)
    
    async def _get_profiles(self, limit: int, session: AsyncSession):
        res = await session.execute(select(Profile).limit(limit))
        profiles: Sequence[Profile] = res.scalars().all()
        return profiles

    async def get_profiles(
        self,
        session: AsyncSession,
        gender: str | None,
        age_group: str | None,
        country_id: str | None,
        min_age: int | None,
        max_age: int | None,
        min_gender_probability: float | None,
        min_country_probability: float | None,
        sort_by: str | None,
        order: str | None,
        offset: int,
        limit: int,
    ) -> Sequence[Profile]:
        sortable_fields: dict = {
            "age": Profile.age,
            "created_at": Profile.created_at,
            "gender_probability": Profile.gender_probability,
        }

        stmt = select(Profile)

        if gender:
            stmt = stmt.where(func.lower(Profile.gender) == gender.lower())

        if age_group:
            stmt = stmt.where(func.lower(Profile.age_group) == age_group.lower())

        if country_id:
            stmt = stmt.where(func.lower(Profile.country_id) == country_id.lower())

        if min_age:
            stmt = stmt.where(Profile.age >= min_age)

        if max_age:
            stmt = stmt.where(Profile.age <= max_age)

        if min_gender_probability:
            stmt = stmt.where(Profile.gender_probability >= min_gender_probability)

        if min_country_probability:
            stmt = stmt.where(Profile.country_probability >= min_country_probability)

        if sort_by:
            sort = sortable_fields.get(sort_by)

            if order == "desc":
                stmt = stmt.order_by(desc(sort))
            else:
                stmt = stmt.order_by(sort)

        stmt = stmt.offset(offset).limit(limit)
        res = await session.execute(stmt)

        profiles: Sequence[Profile] = res.scalars().all()
        return profiles

    async def search_profiles(
        self, q: dict, offset: int, limit: int, session: AsyncSession
    ) -> Sequence[Profile]:
        query = [v for _, v in q.items()]
        print(query)

        stmt = select(Profile).where(*query).offset(offset).limit(limit)

        res = await session.execute(stmt)
        profiles: Sequence[Profile] = res.scalars().all()
        return profiles


profile_repo: ProfileRepo = ProfileRepo()
