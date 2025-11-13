from httpx import Timeout
from pydantic import Field

from app.core.config.base import BaseConfig


class WordPressConfig(BaseConfig):
    base_url: str = Field(default="{domain}wp-json/NDA-integration{endpoint}", alias="WP_BASE_URL")
    timeout: Timeout = Timeout(None)  # TODO: Replace after test


class IntegrationsConfig(BaseConfig):
    wp: WordPressConfig = WordPressConfig()
