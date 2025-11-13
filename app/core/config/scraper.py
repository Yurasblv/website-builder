import os

from pydantic import Field

from app.core.config.base import BaseConfig


class ScraperConfig(BaseConfig):
    API_KEY: str = Field(..., alias="SERP_API_KEY")
    BASE_URL: str = "https://serpapi.com"

    USER_AGENT: str = Field(
        default=(
            "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        ),
        alias="SCRAPER_USER_AGENT",
    )

    BLACKLIST_FILE: str = Field(default="blacklist.txt")
    IGNORE_PATTERN: str = ""

    TIMEOUT: float = 15.0
    MAX_LINKS: int = 3
    LAUNCH_TIMEOUT_MS: int = 10000
    URL_CALLBACK_TIMEOUT_MS: int = 20000
    USE_PROXY: bool = Field(default=False, alias="SCRAPER_USE_PROXY")

    TAVILY_API_KEY: str = Field(..., alias="TAVILY_API_KEY")
    TAVILY_CONCURRENT_REQUESTS_DEV: int = 3
    TAVILY_CONCURRENT_REQUESTS_PROD: int = 10
    TAVILY_RMP_LIMIT: int = 10

    @property
    def ignored_uris(self) -> str:
        if not self.IGNORE_PATTERN:
            base_path = os.path.dirname(__file__)
            blacklist_path = os.path.join(base_path, *[".."] * 3, self.BLACKLIST_FILE)

            with open(os.path.abspath(blacklist_path), "r") as file:
                self.IGNORE_PATTERN = "|".join(set(file.read().splitlines()))

        return self.IGNORE_PATTERN
