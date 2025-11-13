import json
from typing import Any

from sqlalchemy import select

from app.db.redis import redis_pool
from app.models.industry import Industry
from app.repository.base import SQLAlchemyRepository
from app.schemas.industry import IndustryDetail


class IndustryRepository(SQLAlchemyRepository):
    model = Industry

    async def get_multi(  # type: ignore
        self, offset: int = 0, limit: int = 50, /, **filters: Any
    ) -> dict[str, IndustryDetail]:
        redis = await redis_pool.get_redis()
        key = "industries:all"

        all_industries = await redis.hgetall(key)

        if all_industries:
            return {k.decode(): IndustryDetail(**json.loads(v.decode())) for k, v in all_industries.items()}

        statement = select(self.model).where(*self.get_where_clauses(filters)).offset(offset).limit(limit)

        if field := getattr(self.model, self.default_order_by, None):
            statement = statement.order_by(field.desc())

        industries = await self.execute(statement=statement, action=lambda result: result.scalars().all())

        industries_dict = {
            str(industry.id): {"us": industry.title_us, "fr": industry.title_fr} for industry in industries
        }

        # TODO: fix  issue with no industries in cache: redis.exceptions.DataError: 'hset' with no key value pairs
        await redis.hset(key, mapping={k: json.dumps(v) for k, v in industries_dict.items()})
        await redis.expire(key, 3600)

        return {k: IndustryDetail(**v) for k, v in industries_dict.items()}
