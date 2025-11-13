from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import noload, selectinload, with_polymorphic

from app.models import Domain, DomainCustom
from app.repository.base import (
    ModelInheritanceCreateMixin,
    PaginateRepositoryMixin,
    SQLAlchemyRepository,
)
from app.schemas.utils import PaginatedOutput


class DomainRepository(PaginateRepositoryMixin, SQLAlchemyRepository):
    model = Domain
    base_stmt = select(model)
    domain_with_analytics_load = selectinload(model.analytics)
    custom_domain_with_analytics_load = selectinload(DomainCustom.analytics)

    async def get_one(self, join_load_list: list = None, **filters: Any) -> Domain:
        transaction = with_polymorphic(self.model, "*")
        statement = select(transaction).where(*self.get_where_clauses(filters))
        return await self.execute(statement=statement, action=lambda result: result.scalars().one())

    async def paged_list(
        self, join_load_list: list[Any] | None = None, join_filters: dict[str, Any] | None = None, **filters: Any
    ) -> PaginatedOutput:
        if "user_id" in filters:
            repository = DomainCustomRepository(session=self.session)

            return await repository.paged_list(
                join_load_list=[self.custom_domain_with_analytics_load],
                join_filters=join_filters,
                **filters,
            )

        return await super().paged_list(join_load_list=join_load_list, join_filters=join_filters, **filters)


class DomainCustomRepository(PaginateRepositoryMixin, ModelInheritanceCreateMixin, SQLAlchemyRepository):
    model = DomainCustom
    analytics_no_load = noload(model.analytics)
