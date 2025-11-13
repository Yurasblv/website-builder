from typing import Any

from sqlalchemy import Select, func, select

from app.enums import OrderDirection
from app.schemas.utils.paginator import PaginatedOutput


class Paginator:
    def __init__(
        self,
        repository: Any,
        query: Select,
        page: int,
        per_page: int,
        order_by: str,
        order_direction: OrderDirection,
    ):
        self.repository = repository
        self.query = query
        self.page = page
        self.per_page = self.limit = per_page
        self.offset = (page - 1) * per_page

        self.number_of_pages = 0

        field_name = order_by if hasattr(self.repository.model, order_by) else "created_at"
        field = getattr(self.repository.model, field_name)
        self.order_by = getattr(field, order_direction)

    async def get_response(self) -> PaginatedOutput:
        return PaginatedOutput(
            count=await self._get_total_count(),
            total_pages=self.number_of_pages,
            input_items=await self._get_items(),
        )

    async def _get_items(self) -> list:
        statement = self.query.limit(self.limit).offset(self.offset).order_by(self.order_by())
        return await self.repository.execute(statement=statement, action=lambda result: result.scalars().all())

    def _get_number_of_pages(self, count: int) -> int:
        quotient, rest = divmod(count, self.per_page)
        return quotient if not rest else quotient + 1

    async def _get_total_count(self) -> int:
        session = self.repository.session
        count = await session.scalar(select(func.count()).select_from(self.query.subquery()))
        self.number_of_pages = self._get_number_of_pages(count)
        return count


async def paginate(
    repository: Any,
    query: Select,
    page: int,
    per_page: int,
    order_by: str,
    order_direction: OrderDirection,
) -> PaginatedOutput:
    paginator = Paginator(
        repository=repository,
        query=query,
        page=page,
        per_page=per_page,
        order_by=order_by,
        order_direction=order_direction,
    )
    return await paginator.get_response()
