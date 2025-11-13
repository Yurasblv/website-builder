from abc import ABC, abstractmethod
from typing import Any

from loguru import logger
from sentry_sdk import capture_exception
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exc import BaseHTTPException
from app.db.database import async_session, get_sessionmaker_without_pool
from app.repository import (
    AuthorRepository,
    BacklinkRepository,
    CategoryRepository,
    ClusterRepository,
    ClusterSettingsRepository,
    DomainCustomRepository,
    DomainRepository,
    IndustryRepository,
    IntegrationRepository,
    IntegrationWordPressRepository,
    MoneySiteRepository,
    MoneySiteServersRepository,
    MoneySiteServiceAccountRepository,
    PageClusterRepository,
    PagePBNContactRepository,
    PagePBNExtraRepository,
    PagePBNHomeRepository,
    PagePBNLegalRepository,
    PageRepository,
    PBNPlanRepository,
    PBNRepository,
    PostRepository,
    PostXRepository,
    ProjectRepository,
    ServerProviderHetznerRepository,
    ServerProviderRepository,
    ServerProviderScalewayRepository,
    ServiceAccountRepository,
    TransactionRefundRepository,
    TransactionRepository,
    TransactionSpendRepository,
    UserRepository,
)


class ABCUnitOfWork(ABC):
    session: AsyncSession

    # Repository classes
    author: AuthorRepository
    backlink: BacklinkRepository
    category: CategoryRepository
    cluster: ClusterRepository
    cluster_settings: ClusterSettingsRepository
    domain: DomainRepository
    domain_custom: DomainCustomRepository
    industry: IndustryRepository
    integration: IntegrationRepository
    integration_wordpress: IntegrationWordPressRepository
    money_site: MoneySiteRepository
    moneysite_service_account: MoneySiteServiceAccountRepository
    moneysite_server: MoneySiteServersRepository
    page: PageRepository
    page_cluster: PageClusterRepository
    page_pbn_contact: PagePBNContactRepository
    page_pbn_extra: PagePBNExtraRepository
    page_pbn_home: PagePBNHomeRepository
    page_pbn_legal: PagePBNLegalRepository
    pbn: PBNRepository
    pbn_plan: PBNPlanRepository
    post: PostRepository
    post_x: PostXRepository
    project: ProjectRepository
    server_provider: ServerProviderRepository
    server_provider_hetzner: ServerProviderHetznerRepository
    server_provider_scaleway: ServerProviderScalewayRepository
    service_account: ServiceAccountRepository
    transaction: TransactionRepository
    transaction_refund: TransactionRefundRepository
    transaction_spend: TransactionSpendRepository
    user: UserRepository

    @abstractmethod
    def __init__(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def __aenter__(self) -> "UnitOfWork":
        raise NotImplementedError

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close(exc_type, exc)

    @abstractmethod
    async def close(self, exc_type: Any, exc: Any) -> None:
        raise NotImplementedError


class UnitOfWork(ABCUnitOfWork):
    def __init__(self) -> None:
        self.session_maker = async_session

    async def __aenter__(self) -> "UnitOfWork":
        self.session = self.session_maker()

        self.author = AuthorRepository(self.session)
        self.backlink = BacklinkRepository(self.session)
        self.category = CategoryRepository(self.session)
        self.cluster = ClusterRepository(self.session)
        self.cluster_settings = ClusterSettingsRepository(self.session)
        self.domain = DomainRepository(self.session)
        self.domain_custom = DomainCustomRepository(self.session)
        self.industry = IndustryRepository(self.session)
        self.integration = IntegrationRepository(self.session)
        self.integration_wordpress = IntegrationWordPressRepository(self.session)
        self.money_site = MoneySiteRepository(self.session)
        self.moneysite_service_account = MoneySiteServiceAccountRepository(self.session)
        self.moneysite_server = MoneySiteServersRepository(self.session)
        self.page = PageRepository(self.session)
        self.page_cluster = PageClusterRepository(self.session)
        self.page_pbn_contact = PagePBNContactRepository(self.session)
        self.page_pbn_extra = PagePBNExtraRepository(self.session)
        self.page_pbn_home = PagePBNHomeRepository(self.session)
        self.page_pbn_legal = PagePBNLegalRepository(self.session)
        self.pbn = PBNRepository(self.session)
        self.pbn_plan = PBNPlanRepository(self.session)
        self.post = PostRepository(self.session)
        self.post_x = PostXRepository(self.session)
        self.project = ProjectRepository(self.session)
        self.server_provider = ServerProviderRepository(self.session)
        self.server_provider_hetzner = ServerProviderHetznerRepository(self.session)
        self.server_provider_scaleway = ServerProviderScalewayRepository(self.session)
        self.service_account = ServiceAccountRepository(self.session)
        self.transaction = TransactionRepository(self.session)
        self.transaction_refund = TransactionRefundRepository(self.session)
        self.transaction_spend = TransactionSpendRepository(self.session)
        self.user = UserRepository(self.session)

        return self

    async def close(self, exc_type: Any, exc: Any) -> None:
        """
        Finish the transaction and close the session in any case.
        """
        try:
            await self.finish(exc, exc_type)

        except Exception as e:
            capture_exception(e)

        finally:
            await self.session.close()
            await logger.complete()

            if exc:
                raise exc

    async def finish(self, exc: Any, exc_type: Any) -> None:
        if not exc:
            await self.session.commit()
            return

        if not issubclass(exc_type, BaseHTTPException):
            capture_exception(exc)
            logger.error("An error occurred while processing query. Rolling back. Error: {exc}", exc=exc)

        await self.session.rollback()


class UnitOfWorkNoPool(UnitOfWork):
    def __init__(self) -> None:
        super().__init__()
        self.session_maker = get_sessionmaker_without_pool()
