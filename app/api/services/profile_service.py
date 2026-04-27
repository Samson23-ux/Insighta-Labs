import csv
import aiofiles
import pycountry
from pathlib import Path
from uuid import UUID
from uuid6 import uuid7
from datetime import datetime , timezone
from sqlalchemy import Sequence, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import BooleanClauseList
from httpx import AsyncClient, Response, ConnectTimeout, ConnectError


from app.api.models.profiles import Profile
from app.api.repo.profile_repo import profile_repo_v1
from app.utils import is_integer, is_number, is_float
from app.api.schemas.profiles import ProfileCreateV1, ProfileV1 as ProfileSchema
from app.core.exceptions import (
    QueryError,
    ServerError,
    ResponseError,
    ParameterError,
    MissingNameError,
    InvalidTypeError,
    CheckTimeoutError,
    ProfileNotFoundError,
    ProfilesNotFoundError,
)


class ProfileServiceV1:
    async def validate_parameters(
        self,
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
    ) -> tuple:
        if gender:
            if await is_number(gender):
                raise InvalidTypeError()

        if age_group:
            if await is_number(age_group):
                raise InvalidTypeError()

        if country_id:
            if await is_number(country_id):
                raise InvalidTypeError()

        if min_age:
            min_age: int | bool = await is_integer(min_age)
            if not min_age:
                raise InvalidTypeError()

        if max_age:
            max_age: int | bool = await is_integer(max_age)
            if not max_age:
                raise InvalidTypeError()

        if min_gender_probability:
            min_gender_probability: float | bool = await is_float(
                min_gender_probability
            )
            if not min_gender_probability:
                raise InvalidTypeError()

        if min_country_probability:
            min_country_probability: float | bool = await is_float(
                min_country_probability
            )
            if not min_country_probability:
                raise InvalidTypeError()

        if sort_by:
            sortable_fields: list = ["age", "created_at", "gender_probability"]
            if await is_number(sort_by) or sort_by.lower() not in sortable_fields:
                raise InvalidTypeError()

        if order:
            data_order: list = ["asc", "desc"]
            if await is_number(order) or order.lower() not in data_order:
                raise InvalidTypeError()

        page: int | bool = await is_integer(page)
        if not page or page < 1:
            raise InvalidTypeError()

        limit: int | bool = await is_integer(limit)
        if not limit or limit < 1 or limit > 50:
            raise InvalidTypeError()

        return (
            min_age,
            max_age,
            min_gender_probability,
            min_country_probability,
            page,
            limit,
        )

    async def normalize_query(self, q: str) -> tuple:
        # A list of valid query words
        recognized_words: list[str] = [
            "or",
            "male",
            "young",
            "child",
            "adult",
            "above",
            "below",
            "equal",
            "senior",
            "female",
            "between",
            "minimum",
            "maximum",
            "teenager",
        ]

        ## Country mapping
        country_dict: dict[str, str] = {}

        valid_words: list = []
        query_words: list[str] = q.split()
        for i, word in enumerate(query_words):
            word_list: list[str] = list(word)
            if word_list[-1].lower() == "s":
                word_list.pop()
                query_words[i] = "".join(word_list)

            normalized_word: str = query_words[i].lower()
            to_integer: int | None = await is_integer(normalized_word)
            country_name = pycountry.countries.get(name=normalized_word)

            if normalized_word in recognized_words:
                if normalized_word not in valid_words:
                    valid_words.append(normalized_word)
            elif to_integer:
                if not to_integer < 0:
                    if to_integer not in valid_words:
                        valid_words.append(to_integer)
            elif country_name:
                if normalized_word not in valid_words:
                    valid_words.append(normalized_word)

                if normalized_word not in country_dict:
                    country_dict[normalized_word] = country_name.alpha_2

        return valid_words, country_dict

    async def process_range(
        self, i: int, q: str, normalized_query: list, processed: list
    ):
        query = None

        ## when a word from the range class is used there needs
        # to be at least one more index
        if i + 1 > len(normalized_query) - 1:
            raise QueryError()

        first_int = normalized_query[i + 1]
        if not isinstance(first_int, int):
            raise QueryError()

        if q == "between":
            if i + 2 > len(normalized_query) - 1:
                raise QueryError()

            second_int: int = normalized_query[i + 2]
            if not isinstance(second_int, int):
                raise QueryError()

            processed.append(second_int)
            query = and_(Profile.age >= first_int, Profile.age <= second_int)
        else:
            if q == "above":
                query = Profile.age > first_int
            elif q == "below":
                query = Profile.age < first_int
            elif q == "equal":
                query = Profile.age == first_int
            elif q == "maximum":
                query = Profile.age <= first_int
            elif q == "minimum":
                query = Profile.age >= first_int

        processed.append(first_int)
        return query

    async def process_logical_operator(
        self,
        i: int,
        q: str,
        range_query: list,
        country_dict: dict,
        gender_k: tuple,
        gender_v,
        age_groups_k: tuple,
        age_groups_v,
        normalized_query: list,
        processed: list,
        memory: list,
        queries: dict,
    ):
        next_query = None
        query_class = None
        if i == 0 or i == len(normalized_query) - 1:
            raise QueryError()

        last_query = queries.get(memory[-1])

        next_word = normalized_query[i + 1]

        if next_word in gender_k:
            query_class: str = gender_k[0]
            next_query = gender_v == next_word
        elif next_word in age_groups_k:
            query_class: str = age_groups_k[0]

            if next_word == "young":
                next_query = and_(Profile.age >= 16, Profile.age <= 24)
            else:
                next_query = age_groups_v == next_word
        elif next_word in country_dict:
            query_class: str = "country_id"
            country_id: str = country_dict.get(next_word)
            next_query = Profile.country_id == country_id
        elif next_word in range_query:
            query_class: str = "range"
            next_query: str = await self.process_range(
                i + 1, next_word, normalized_query, processed
            )
        else:
            raise QueryError()

        last_word = memory[-1]
        new_word = f"{last_word} {q} {query_class}"

        queries.pop(last_word)
        memory.append(new_word)
        processed.append(next_word)

        # check if the last query is an or filter to identify a chain of or operators
        if isinstance(last_query, BooleanClauseList):
            ## last_query.clauses is iterable
            queries.update({new_word: or_(*last_query.clauses, next_query)})
        else:
            queries.update({new_word: or_(last_query, next_query)})

    async def map_query(self, normalized_query: list[str], country_dict: dict) -> dict:
        # Column mappings
        gender: dict = {("gender", "male", "female", "young"): Profile.gender}
        range_query: list = ["above", "below", "equal", "maximum", "minimum", "between"]
        age_groups: dict = {
            ("age_group", "child", "teenager", "adult", "senior"): Profile.age_group
        }

        queries: dict = {}  # hold mapped queries
        memory: list[str] = []  # serve as the last processed query
        processed: list[str] = []  # identify processed words to skip

        ((gender_k, gender_v),) = gender.items()
        ((age_groups_k, age_groups_v),) = age_groups.items()

        if not normalized_query:
            raise QueryError()

        for i, q in enumerate(normalized_query):
            if q in processed:
                continue

            if q in gender_k:
                query_class: str = gender_k[0]
                processed.append(q)
                memory.append(query_class)
                queries.update({query_class: gender_v == q})
            elif q in age_groups_k:
                query_class: str = age_groups_k[0]
                processed.append(q)
                memory.append(query_class)

                if q == "young":
                    queries.update(
                        {query_class: and_(Profile.age >= 16, Profile.age <= 24)}
                    )
                else:
                    queries.update({query_class: age_groups_v == q})
            elif q in country_dict:
                country_id: str = country_dict.get(q)
                processed.append(q)
                memory.append("country_id")
                queries.update({"country_id": Profile.country_id == country_id})
            elif q == "or":
                await self.process_logical_operator(
                    i,
                    q,
                    range_query,
                    country_dict,
                    gender_k,
                    gender_v,
                    age_groups_k,
                    age_groups_v,
                    normalized_query,
                    processed,
                    memory,
                    queries,
                )
            elif q in range_query:
                query = await self.process_range(i, q, normalized_query, processed)
                processed.append(q)
                memory.append("range")
                queries.update({"range": query})
            else:
                raise QueryError()

        return queries

    async def agify_request(self, name: str, client: AsyncClient):
        curr_retries: int = 0
        total_retries: int = 5
        status: str = "failure"

        while curr_retries < total_retries and status != "success":
            try:
                res: Response = await client.get(f"/?name={name}")
                status: str = "success"
            except (ConnectTimeout, ConnectError):
                curr_retries += 1

        if status == "failure":
            raise CheckTimeoutError()

        json_res: dict = res.json()
        age: str | None = json_res.get("age")

        if not age:
            raise ResponseError(external_api="Agify")

        return json_res

    async def genderize_request(self, name: str, client: AsyncClient):
        curr_retries: int = 0
        total_retries: int = 5
        status: str = "failure"

        while curr_retries < total_retries and status != "success":
            try:
                res: Response = await client.get(f"/?name={name}")
                status: str = "success"
            except (ConnectTimeout, ConnectError):
                curr_retries += 1

        if status == "failure":
            raise CheckTimeoutError()

        json_res: dict = res.json()
        gender: str | None = json_res.get("gender")
        sample_size: int = json_res.get("count")

        if not gender or sample_size == 0:
            raise ResponseError(external_api="Genderize")

        return json_res

    async def nationalize_request(self, name: str, client: AsyncClient):
        curr_retries: int = 0
        total_retries: int = 5
        status: str = "failure"

        while curr_retries < total_retries and status != "success":
            try:
                res: Response = await client.get(f"/?name={name}")
                status: str = "success"
            except (ConnectTimeout, ConnectError):
                curr_retries += 1

        if status == "failure":
            raise CheckTimeoutError()

        json_res: dict = res.json()
        country: list = json_res.get("country")

        if len(country) < 1:
            raise ResponseError(external_api="Nationalize")

        return json_res

    async def create_profiles(self, profiles: list[dict], session: AsyncSession):
        await profile_repo_v1.add_profiles_to_db(profiles, session)

    async def _get_profiles(
        self, limit: int, session: AsyncSession
    ) -> Sequence[Profile]:
        return await profile_repo_v1._get_profiles(limit, session)

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
    ) -> dict:
        (
            min_age,
            max_age,
            min_gender_probability,
            min_country_probability,
            page,
            limit,
        ) = await self.validate_parameters(
            gender,
            age_group,
            country_id,
            min_age,
            max_age,
            min_gender_probability,
            min_country_probability,
            sort_by,
            order,
            page,
            limit,
        )

        offset: int = (page * limit) - limit

        try:
            profiles: Sequence[Profile] = await profile_repo_v1.get_profiles(
                session,
                gender,
                age_group,
                country_id,
                min_age,
                max_age,
                min_gender_probability,
                min_country_probability,
                sort_by,
                order,
                offset,
                limit,
            )

            if not profiles:
                raise ProfilesNotFoundError()

            data: dict = {}
            profiles_out: list[ProfileSchema] = []

            for profile in profiles:
                profiles_out.append(ProfileSchema.model_validate(profile))

            next_page: str | None = f"/api/profiles?page={str(page+1)}&limit={str(limit)}" if page < 203 else None
            prev_page: str | None = f"/api/profiles?page={str(page-1)}&limit={str(limit)}" if page > 1 else None

            links: dict = {
                "self": f"/api/profiles?page={str(page)}&limit={str(limit)}",
                "next": next_page,
                "prev": prev_page
            }

            data["links"] = links
            data["profiles"] = profiles_out

            return data
        except Exception as e:
            if isinstance(e, ProfilesNotFoundError):
                raise ProfilesNotFoundError()

            raise ServerError() from e

    async def search_for_profiles(
        self, q: str, page: str, limit: str, session: AsyncSession
    ) -> dict:
        if not q:
            raise ParameterError()

        if await is_number(q):
            raise InvalidTypeError()

        page: int | bool = await is_integer(page)
        if not page or page < 1:
            raise InvalidTypeError()

        limit: int | bool = await is_integer(limit)
        if not limit or limit < 10 or limit > 50:
            raise InvalidTypeError()

        offset: int = (page * limit) - limit

        normalized_query, country_dict = await self.normalize_query(q)

        mapped_query: dict = await self.map_query(normalized_query, country_dict)

        try:
            profiles: Sequence[Profile] = await profile_repo_v1.search_profiles(
                mapped_query, offset, limit, session
            )

            if not profiles:
                raise ProfilesNotFoundError()

            data: dict = {}
            profiles_out: list[ProfileSchema] = []

            for profile in profiles:
                profiles_out.append(ProfileSchema.model_validate(profile))
                
            next_page: str | None = f"/api/profiles?page={str(page+1)}&limit={str(limit)}" if page < 203 else None
            prev_page: str | None = f"/api/profiles?page={str(page-1)}&limit={str(limit)}" if page > 1 else None

            links: dict = {
                "self": f"/api/profiles?page={str(page)}&limit={str(limit)}",
                "next": next_page,
                "prev": prev_page
            }

            data["links"] = links
            data["profiles"] = profiles_out

            return data
        except Exception as e:
            if isinstance(e, ProfilesNotFoundError):
                raise ProfilesNotFoundError()

            raise ServerError() from e

    async def export_csv(
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
    ) -> Path:
        data: dict = await self.get_profiles(
            session,
            gender,
            age_group,
            country_id,
            min_age,
            max_age,
            min_gender_probability,
            min_country_probability,
            sort_by,
            order,
            page,
            limit
        )

        profiles: list[ProfileSchema] = data.get("profiles")

        profile_data: list[dict] = [p.model_dump() for p in profiles]
        export_filename: str = f"profiles_{datetime.now(timezone.utc).isoformat()}"
        export_path: Path = Path(__file__ ).parent.parent / "exports" / export_filename
        profiles_headers = ["id", "name", "gender", "gender_probability", "age", "age_group", "country_id", "country_name", "country_probability", "created"]

        async with aiofiles.open(export_path, "a") as f:
            writer = csv.DictWriter(f, fieldnames=profiles_headers)

            writer.writeheader()
            writer.writerows(profile_data)

        return export_path

    async def get_profile(
        self, profile_id: UUID, session: AsyncSession
    ) -> ProfileSchema:
        try:
            profile: Profile | None = await profile_repo_v1.get_profile(
                profile_id, session
            )

            if not profile:
                raise ProfileNotFoundError(profile_id=profile_id)

            profile_out: ProfileSchema = ProfileSchema.model_validate(profile)
            return profile_out
        except Exception as e:
            if isinstance(e, ProfileNotFoundError):
                raise ProfileNotFoundError(profile_id=profile_id)

            raise ServerError() from e

    async def create_profile(
        self, profile_create: ProfileCreateV1, client: tuple, session: AsyncSession
    ) -> ProfileSchema:
        name: str = profile_create.name

        if not name:
            raise MissingNameError()

        if await is_number(name):
            raise InvalidTypeError()

        existing_profile: Profile | None = await profile_repo_v1.get_profile_by_name(
            name, session
        )

        if existing_profile:
            existing_profile_out: ProfileSchema = ProfileSchema.model_validate(
                existing_profile
            )
            return {"data": existing_profile_out, "exists": True}

        agify_client, genderize_client, nationalize_client = client

        agify_res: dict = await self.agify_request(name, agify_client)
        genderize_res: dict = await self.genderize_request(name, genderize_client)
        nationalize_res: dict = await self.nationalize_request(name, nationalize_client)

        age: int = agify_res.get("age")

        if age >= 0 and age <= 12:
            age_group: str = "child"
        elif age >= 13 and age <= 19:
            age_group: str = "teenager"
        elif age >= 20 and age <= 59:
            age_group: str = "adult"
        elif age >= 60:
            age_group: str = "senior"

        country: dict = {}
        max_probability = 0
        countries: list[dict] = nationalize_res.get("country")

        for c in countries:
            probability: float = c.get("probability")
            if probability > max_probability:
                country: dict = c
                max_probability: float = probability

        country_name: str = pycountry.countries.get(alpha_2=country.get("country_id"))

        profile_db: Profile = Profile(
            id=uuid7(),
            name=name,
            gender=genderize_res.get("gender"),
            gender_probability=genderize_res.get("probability"),
            age=age,
            age_group=age_group,
            country_id=country.get("country_id"),
            country_name=country_name,
            country_probability=country.get("probability"),
        )

        try:
            await profile_repo_v1.add_profile_to_db(profile_db, session)
            profile_id: UUID = profile_db.id

            profile: Profile = await profile_repo_v1.get_profile(profile_id, session)
            profile_out: ProfileSchema = ProfileSchema.model_validate(profile)

            await session.commit()
            return {"data": profile_out, "exists": False}
        except Exception as e:
            await session.rollback()
            raise ServerError() from e

    async def delete_profile(self, profile_id: UUID, session: AsyncSession):
        profile: Profile | None = await profile_repo_v1.get_profile(profile_id, session)

        if not profile:
            raise ProfileNotFoundError(profile_id=profile_id)

        try:
            await profile_repo_v1.delete_profile(profile, session)
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise ServerError() from e


profile_service_v1: ProfileServiceV1 = ProfileServiceV1()
