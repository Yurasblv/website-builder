import json
from typing import Any

from sqlalchemy import select

from app.db.redis import redis_pool
from app.models import Category
from app.repository.base import SQLAlchemyRepository


class CategoryRepository(SQLAlchemyRepository):
    model = Category

    async def get_multi(self, offset: int = 0, limit: int = 50, /, **filters: Any) -> dict:  # type: ignore
        redis = await redis_pool.get_redis()
        key = "categories:all"

        all_categories = await redis.hgetall(key)

        if all_categories:
            return {k.decode(): json.loads(v.decode()) for k, v in all_categories.items()}

        statement = select(self.model).offset(offset).limit(limit)

        if field := getattr(self.model, self.default_order_by, None):
            statement = statement.order_by(field.desc())

        categories = await self.execute(statement=statement, action=lambda result: result.scalars().all())

        categories_dict = {str(category.id): category.title for category in categories}

        if not categories_dict:
            return {}

        await redis.hset(key, mapping={k: json.dumps(v) for k, v in categories_dict.items()})
        await redis.expire(key, 3600)

        return categories_dict
