from datetime import UTC, datetime
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.enums import PageType, PBNGenerationStatus
from app.models.backlink import Backlink
from app.models.page import Page
from app.models.pbn import PBN
from app.repository.base import SQLAlchemyRepository


class BacklinkRepository(SQLAlchemyRepository):
    model = Backlink
    base_stmt = select(model)
    page_load = selectinload(model.page)
    pbn_load = selectinload(model.pbn)
    pbn_domain_load = pbn_load.selectinload(PBN.domain)

    async def get_by_page_type(self, page_type: PageType, **filters: Any) -> Backlink | None:
        stmt = self.base_stmt.join(self.model.page).filter(Page.page_type == page_type)
        statement = self._build_query(stmt, **filters)

        return await self.execute(statement=statement, action=lambda result: result.scalars().one_or_none())

    async def get_relevant_to_enable(self, limit: int = 100) -> Sequence[Backlink]:
        statement = (
            self.base_stmt.options(self.page_load, self.pbn_load, self.pbn_domain_load)
            .join(self.model.pbn)
            .filter(
                self.model.is_visible == False,
                self.model.publish_at < datetime.now(UTC),
                PBN.status == PBNGenerationStatus.DEPLOYED,
            )
            .limit(limit)
        )

        return await self.execute(statement=statement, action=lambda result: result.scalars().all())
