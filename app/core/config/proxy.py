from pydantic import Field

from app.core.config.base import BaseConfig


class ProxyConfig(BaseConfig):
    API_KEY: str = Field(..., alias="PROXY_SELLER_API_KEY")
    COUNTRY_ID: int = Field(default=561, alias="PROXY_COUNTRY_ID")
    PERIOD_ID: str = Field(default="1w", alias="PROXY_PERIOD_ID")
    TTL: int = Field(default=3600, alias="PROXY_SELLER_TTL")

    NUMBER_OF_PROXIES: int = 10
    MAX_ATTEMPTS: int = 10

    @property
    def base_url(self) -> str:
        """Constructs the proxy seller URL using the API key."""
        return f"https://proxy-seller.com/personal/api/v1/{self.API_KEY}/"
