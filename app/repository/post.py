from typing import Any

from sqlalchemy import select

from app.models import Post, PostX
from app.repository.base import ModelInheritanceCreateMixin, SQLAlchemyRepository


class PostRepository(SQLAlchemyRepository):
    model = Post


class PostXRepository(ModelInheritanceCreateMixin, SQLAlchemyRepository):
    model = PostX

    async def get_multi(self, offset: int = 0, limit: int = 5, /, **filters: Any) -> list[str]:
        statement = (
            select(self.model.text)  # need only text
            .where(*self.get_where_clauses(filters))
            .offset(offset)
            .limit(limit)
            .order_by(self.model.created_at.desc())
        )

        return await self.execute(statement=statement, action=lambda result: result.scalars().all())
