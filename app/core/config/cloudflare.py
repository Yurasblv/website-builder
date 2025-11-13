from pydantic import Field

from app.core.config.base import BaseConfig


class CloudFlareConfig(BaseConfig):
    BASE_URL: str = "https://api.cloudflare.com/client/v4"
    TOKEN: str = Field(..., alias="CLOUDFLARE_API_TOKEN")

    redis_key: str = "{0}_ssl_cert"
