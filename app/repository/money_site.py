from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import MoneySite
from app.models.association import MoneySiteServerAssociation, MoneySiteServiceAccountAssociation
from app.repository.base import SQLAlchemyRepository


class MoneySiteRepository(SQLAlchemyRepository):
    model = MoneySite
    base_stmt = select(model)
    pbns_load = selectinload(model.pbns)
    plan_load = selectinload(model.plan)
    servers_load = selectinload(model.servers)
    accounts_load = selectinload(model.service_accounts)


class MoneySiteServiceAccountRepository(SQLAlchemyRepository):
    model = MoneySiteServiceAccountAssociation
    base_stmt = select(model)

    async def get_used_by_domain(self, domain: str) -> list[str]:
        statement = select(self.model.service_account_id).distinct().where(self.model.money_site_domain == domain)
        return await self.execute(statement=statement, action=lambda result: result.scalars().all())


class MoneySiteServersRepository(SQLAlchemyRepository):
    model = MoneySiteServerAssociation
    base_stmt = select(model)

    async def get_used_by_domain(self, domain: str) -> list[str]:
        statement = select(self.model.server_provider_id).distinct().where(self.model.money_site_domain == domain)
        return await self.execute(statement=statement, action=lambda result: result.scalars().all())
