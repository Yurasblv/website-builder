from pydantic import Field

from app.core.config.base import BaseConfig


class MicroServicesConfig(BaseConfig):
    response_channel: str = Field(default="responses", alias="RESPONSE_CHANNEL")
    request_channel: str = Field(default="requests", alias="REQUEST_CHANNEL")
