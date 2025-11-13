from decimal import Decimal

from loguru import logger
from pydantic import Field, model_validator

from app.core.config.ai import AIConfig
from app.core.config.api import APIConfig
from app.core.config.base import BaseConfig
from app.core.config.build import BuildConfig
from app.core.config.celery import CeleryConfig
from app.core.config.cloudflare import CloudFlareConfig
from app.core.config.database import DataBaseConfig
from app.core.config.domain import DomainConfig
from app.core.config.integrations import IntegrationsConfig
from app.core.config.message_queue import MessageQueueConfig
from app.core.config.microservices import MicroServicesConfig
from app.core.config.next import NextServiceConfig
from app.core.config.provider_manager import ProviderManager
from app.core.config.proxy import ProxyConfig
from app.core.config.redis import RedisConfig
from app.core.config.scraper import ScraperConfig
from app.core.config.storage import StorageConfig
from app.enums.base import ExecutionMode, ProjectStage


class Settings(BaseConfig):
    EXECUTION_MODE: ExecutionMode = Field(default=ExecutionMode.TEST)
    STAGE: ProjectStage = Field(default=ProjectStage.LOCAL)
    PROJECT_NAME: str = Field(default="NDA AI Builder")
    SERVER_HOST: str = Field(default="localhost")
    SERVER_PORT: int = Field(default=8000)
    ENCRYPTION_KEY: str = Field(..., alias="ENCRYPTION_KEY")

    VERSION: str = Field(default="0.0.1")
    DEBUG: bool = Field(default=True)

    # Swagger
    SWAGGER_USERNAME: str = Field(default="admin")
    SWAGGER_PASSWORD: str = Field(default="admin")

    # Generating

    PAGE_PRICE: Decimal = Decimal(2.89)
    PAGE_REFRESH_PRICE: Decimal = Decimal(1)  # TODO: change after customer will decide on price
    MAX_PAGES: int = 1000

    MAX_THREADS: int = 5

    SENTRY_DSN: str
    SENTRY_WORKER_DSN: str

    ai: AIConfig = AIConfig()
    api: APIConfig = APIConfig()
    build: BuildConfig = BuildConfig()
    celery: CeleryConfig = CeleryConfig()
    cloudflare: CloudFlareConfig = CloudFlareConfig()
    db: DataBaseConfig = DataBaseConfig()
    domain: DomainConfig = DomainConfig()
    provider_manager: ProviderManager = ProviderManager()
    integrations: IntegrationsConfig = IntegrationsConfig()
    message_queue: MessageQueueConfig = MessageQueueConfig()
    microservices: MicroServicesConfig = MicroServicesConfig()
    next: NextServiceConfig = NextServiceConfig()
    proxy: ProxyConfig = ProxyConfig()
    redis: RedisConfig = RedisConfig()
    scraper: ScraperConfig = ScraperConfig()
    storage: StorageConfig = StorageConfig()

    @property
    def include_in_schema(self) -> bool:
        return self.STAGE != ProjectStage.PRODUCTION

    @property
    def is_test_mode(self) -> bool:
        return self.EXECUTION_MODE == ExecutionMode.TEST

    @property
    def is_production(self) -> bool:
        return self.STAGE == ProjectStage.PRODUCTION

    @property
    def tavily_concurrent_requests(self) -> int:
        return (
            self.scraper.TAVILY_CONCURRENT_REQUESTS_PROD
            if self.is_production
            else self.scraper.TAVILY_CONCURRENT_REQUESTS_DEV
        )

    @property
    def tavily_rpm_requests(self) -> int:
        return self.scraper.TAVILY_RMP_LIMIT

    @model_validator(mode="after")
    def production_extra_check(self) -> "Settings":
        if self.STAGE != ProjectStage.PRODUCTION:
            return self

        if not self.scraper.USE_PROXY:
            logger.error("Proxy is disabled in production mode")

        return self


settings = Settings()
