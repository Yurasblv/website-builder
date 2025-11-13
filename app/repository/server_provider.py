from typing import Any, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import with_polymorphic

from app.models import ServerProvider, ServerProviderHetzner, ServerProviderScaleway
from app.repository.base import ModelInheritanceCreateMixin, SQLAlchemyRepository


class ServerProviderRepository(SQLAlchemyRepository):
    model = ServerProvider

    # TODO: Is used?
    async def get_multi(self, offset: int = 0, limit: int = 5000, /, **filters: Any) -> Sequence[ServerProvider]:
        provider = with_polymorphic(self.model, "*")
        statement = (
            select(provider)
            .where(*self.get_where_clauses(filters))
            .offset(offset)
            .limit(limit)
            .order_by(self.model.created_at)
        )

        return await self.execute(statement=statement, action=lambda result: result.scalars().all())

    async def get_random_unique(self, limit: int, **filters: Any) -> Sequence[ServerProvider]:
        provider = with_polymorphic(self.model, "*")
        statement = (
            select(provider)
            .distinct(self.model.provider_type, self.model.location)
            .order_by(self.model.provider_type, self.model.location, func.random())
            .limit(limit)
        )
        statement = statement.where(*self.get_where_clauses(filters))

        return await self.execute(statement=statement, action=lambda result: result.scalars().all())


class ServerProviderHetznerRepository(ModelInheritanceCreateMixin, SQLAlchemyRepository):
    model = ServerProviderHetzner


class ServerProviderScalewayRepository(ModelInheritanceCreateMixin, SQLAlchemyRepository):
    model = ServerProviderScaleway
