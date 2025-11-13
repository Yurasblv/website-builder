from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.enums import OrderDirection
from app.models import PBN, Domain, PBNPlan
from app.repository.base import PaginateRepositoryMixin, SQLAlchemyRepository
from app.schemas.utils import PaginatedOutput
from app.utils.paginator import paginate


class PBNRepository(PaginateRepositoryMixin, SQLAlchemyRepository):
    model = PBN
    base_stmt = select(model)

    # UserInfoLoad
    user_load = selectinload(model.user)

    # Domain-related
    domain_load = selectinload(model.domain)
    domain_with_analytics_load = domain_load.selectinload(Domain.analytics)

    # Relationship loaders
    children_load = selectinload(model.children)
    clusters_load = selectinload(model.clusters)
    money_site_load = selectinload(model.money_site)
    service_account_load = selectinload(model.service_account)
    server_load = selectinload(model.server)

    # Page loaders
    home_page_load = selectinload(model.page_home)
    contact_page_load = selectinload(model.page_contact)
    legal_page_load = selectinload(model.page_legal)
    extra_pages_load = selectinload(model.pages_extra)

    async def get_by_filters(
        self,
        *,
        join_load_list: list = None,
        page: int = 1,
        per_page: int = 10,
        order_by: str = "created_at",
        order_direction: OrderDirection = OrderDirection.DESC,
        **filters: Any,
    ) -> PaginatedOutput:
        stmt = self.base_stmt
        if any(
            [
                categories := filters.pop("domain__category_id__in", None),
                search_value := filters.pop("domain_name__icontains", None),
            ]
        ):
            stmt = stmt.join(Domain, Domain.pbn_id == self.model.id)

            if categories:
                stmt = stmt.where(Domain.category_id.in_(categories))

            if search_value:
                stmt = stmt.filter(Domain.name.ilike(search_value))

        stmt = self._build_query(stmt=stmt, join_load_list=join_load_list, **filters)

        return await paginate(
            self, stmt, page=page, per_page=per_page, order_by=order_by, order_direction=order_direction
        )


class PBNPlanRepository(SQLAlchemyRepository):
    model = PBNPlan
