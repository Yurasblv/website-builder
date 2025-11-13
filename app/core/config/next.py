from pydantic import Field

from app.core.config.base import BaseConfig


class NextServiceConfig(BaseConfig):
    URL: str = Field(default="http://localhost:3005", description="Next.js service URL", alias="NEXT_SERVICE_URL")

    IFRAME_TOKEN_EXPIRE: int = Field(default=60 * 60, description="IFrame token expiration time in seconds")
