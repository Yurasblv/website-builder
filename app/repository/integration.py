from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import with_polymorphic

from app.models import Integration, IntegrationWordPress
from app.repository.base import ModelInheritanceCreateMixin, ModelInheritanceDeleteMixin, SQLAlchemyRepository


class IntegrationRepository(SQLAlchemyRepository):
    model = Integration

    async def get_one_or_none(self, join_load_list: list = None, **filters: Any) -> Integration | None:
        transaction = with_polymorphic(Integration, "*")
        statement = select(transaction).where(*self.get_where_clauses(filters))
        return await self.execute(statement=statement, action=lambda result: result.scalar_one_or_none())


class IntegrationWordPressRepository(ModelInheritanceDeleteMixin, ModelInheritanceCreateMixin, SQLAlchemyRepository):
    model = IntegrationWordPress
