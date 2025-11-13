from typing import Any, Sequence

from sentry_sdk import capture_exception
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload, with_polymorphic

from app.db.database import create_null_pool_engine
from app.models import Page, PageCluster, PagePBNContact, PagePBNExtra, PagePBNHome, PagePBNLegal
from app.repository.base import ModelInheritanceCreateMixin, PaginateRepositoryMixin, SQLAlchemyRepository


class PageRepository(PaginateRepositoryMixin, SQLAlchemyRepository):
    model = Page

    async def get_one(self, **filters: Any) -> Page:  # type:ignore[override]
        transaction = with_polymorphic(self.model, "*")
        statement = select(transaction).where(*self.get_where_clauses(filters))

        return await self.execute(statement=statement, action=lambda result: result.scalars().one())

    async def get_multi(self, offset: int = 0, limit: int = 5000, /, **filters: Any) -> Sequence[Page]:
        transaction = with_polymorphic(Page, "*")
        statement = (
            select(transaction)
            .where(*self.get_where_clauses(filters))
            .offset(offset)
            .limit(limit)
            .order_by(self.model.created_at)
        )

        return await self.execute(statement=statement, action=lambda result: result.scalars().all())


class PageClusterRepository(ModelInheritanceCreateMixin, SQLAlchemyRepository):
    model = PageCluster
    base_stmt = select(model)
    cluster_load = selectinload(model.cluster)  # type:ignore
    children_load = selectinload(model.children)  # type:ignore

    async def get_multi(
        self, offset: int = 0, limit: int = 0, /, join_load_list: list = None, **filters: Any
    ) -> Sequence[PageCluster]:
        stmt = (
            self._build_query(join_load_list=join_load_list, **filters).offset(offset).order_by(self.model.created_at)
        )
        if limit:
            stmt = stmt.limit(limit)

        return await self.execute(statement=stmt, action=lambda result: result.scalars().all())

    async def get_page_intents(self, **filters: Any) -> list[dict[str, Any]]:
        stmt = (
            select(self.model.search_intent.label("intent"), func.count(self.model.search_intent).label("pages_count"))
            .where(*self.get_where_clauses(filters))
            .group_by(self.model.search_intent)
        )
        return await self.execute(statement=stmt, action=lambda result: result.mappings().all())

    async def create_bulk(self, pages: list[dict[str, Any]]) -> None:
        """
        Bulk sqlalchemy core insert records for pages object.

        Args:
            pages: list with pages dicts, each page was converted with in model_dump()

        Raises:
            Exception: with rollback of current transaction
        """
        async with create_null_pool_engine().begin() as tx:
            try:
                await tx.execute(Page.__table__.insert(), pages)  # type:ignore
                await tx.execute(self.model.__table__.insert(), pages)  # type:ignore
                await tx.commit()
            except Exception as e:
                capture_exception(e)
                await tx.rollback()
                raise e


class PagePBNHomeRepository(ModelInheritanceCreateMixin, SQLAlchemyRepository):
    model = PagePBNHome
    base_stmt = select(model)
    pbn_load = selectinload(model.pbn)  # type:ignore


class PagePBNLegalRepository(ModelInheritanceCreateMixin, SQLAlchemyRepository):
    model = PagePBNLegal
    base_stmt = select(model)
    pbn_load = selectinload(model.pbn)  # type:ignore


class PagePBNContactRepository(ModelInheritanceCreateMixin, SQLAlchemyRepository):
    model = PagePBNContact
    base_stmt = select(model)
    pbn_load = selectinload(model.pbn)  # type:ignore


class PagePBNExtraRepository(ModelInheritanceCreateMixin, SQLAlchemyRepository):
    model = PagePBNExtra
    base_stmt = select(model)
    pbn_load = selectinload(model.pbn)  # type:ignore
