from decimal import Decimal

from pydantic import Field

from app.core.config.base import BaseConfig


class DynadotConfig(BaseConfig):
    API_KEY: str = Field(..., alias="DYNADOT_API_KEY")
    API_BASE_URL: str = "https://api.dynadot.com/api3.json"
    BASE_URL: str = "https://www.dynadot.com/domain"
    YEARS_TO_BUY: int = 1


class DomainConfig(BaseConfig):
    MAX_PRICE: Decimal = Field(Decimal(7), alias="DOMAIN_MAX_PRICE")
    TTL: int = Field(default=1200, alias="DOMAIN_AI_TTL")

    dynadot: DynadotConfig = DynadotConfig()
