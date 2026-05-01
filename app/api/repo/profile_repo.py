from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, Sequence, func, desc, insert


from app.api.models.profiles import Profile


class ProfileRepoV1:
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
            sort = sortable_fields.get(sort_by.lower())

            if order:
                if order.lower() == "desc":
                    stmt = stmt.order_by(desc(sort))
                else:
                    stmt = stmt.order_by(sort)
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

        stmt = select(Profile).where(*query).offset(offset).limit(limit)

        res = await session.execute(stmt)
        profiles: Sequence[Profile] = res.scalars().all()
        return profiles

    async def get_stats(self, session: AsyncSession) -> dict:
        # Total profiles
        total_result = await session.execute(select(func.count(Profile.id)))
        total: int = total_result.scalar()

        # By gender
        gender_result = await session.execute(
            select(Profile.gender, func.count(Profile.id))
            .group_by(Profile.gender)
        )
        by_gender: dict = {row.gender: row.count for row in gender_result if row.gender}

        # Unique countries
        countries_result = await session.execute(
            select(func.count(func.distinct(Profile.country_id)))
        )
        unique_countries: int = countries_result.scalar()

        stats: dict = {
            "total": total,
            "gender_result": by_gender,
            "unique_countries": unique_countries
        }

        return stats
    
    async def get_profile(
        self, profile_id: UUID, session: AsyncSession
    ) -> Profile | None:
        stmt = select(Profile).where(Profile.id == profile_id)
        res = await session.execute(stmt)
        profile: Profile | None = res.scalar()
        return profile
    
    async def get_profile_by_name(
        self, name: str, session: AsyncSession
    ) -> Profile | None:
        stmt = select(Profile).where(Profile.name == name)
        res = await session.execute(stmt)
        profile: Profile | None = res.scalar()
        return profile

    async def add_profile_to_db(self, profile: Profile, session: AsyncSession):
        session.add(profile)
        await session.flush()
        await session.refresh(profile)

    async def delete_profile(self, profile: Profile, session: AsyncSession):
        await session.delete(profile)
        await session.flush()

profile_repo_v1: ProfileRepoV1 = ProfileRepoV1()
