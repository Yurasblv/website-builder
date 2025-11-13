from pydantic import Field

from app.core.config.base import BaseConfig


class APIConfig(BaseConfig):
    prefix: str = Field(default="tr-", description="API key prefix")
    length: int = Field(default=100, description="API key length")
