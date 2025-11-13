from typing import Any

from pydantic import Field

from app.core.config.base import BaseConfig
from app.enums.provider import ServerProviderEndpoint


class ProviderManager(BaseConfig):
    URL: str = Field(default="http://localhost:8010", description="Provider manager URL", alias="PROVIDER_MANAGER_URL")

    version: str = Field("v1")

    def construct_url(self, endpoint: ServerProviderEndpoint, **kwargs: Any) -> str:
        return f"{self.URL}/api/{self.version}/{endpoint}".format(**kwargs)
