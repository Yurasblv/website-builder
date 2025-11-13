import re
import statistics

from aiohttp import ClientResponseError, ClientSession
from langchain_core.documents import Document
from loguru import logger
from orjson import loads

from app.core import settings
from app.enums import Language
from app.utils.scraper import H2TagsTransformer, ScraperRequestService


class Scraper:
    h2_transformer = H2TagsTransformer()

    @staticmethod
    def _calculate_average(values: list[int], default: int) -> int:
        if not values:
            return default

        median_value = statistics.median(values)
        mean_value = statistics.mean(values)
        avg = statistics.mean([median_value, mean_value])

        return int(avg)

    @staticmethod
    def is_link_ignored(link: str | None) -> bool:
        """
        Checks if a given link should be excluded based on the ignored sites list.

        Args:
            link: The URL to check.

        Returns:
            True if the link is not in the ignored sites list, False otherwise.
        """
        return bool(re.search(settings.scraper.ignored_uris, link)) if link else True

    @classmethod
    def get_results(cls, data: dict) -> list[str]:
        """
        Parses links and questions from search data.

        Args:
            data: Search data.

        Returns:
            A tuple of link list and question-answer dictionary.
        """
        return [r["link"] for r in data.get("organic_results", []) if not cls.is_link_ignored(r.get("link"))]

    @classmethod
    def get_metadata_from_results(cls, data: dict) -> list[dict]:
        metadata: list = []

        for result in data.get("organic_results", []):
            link = result.get("link")

            if cls.is_link_ignored(link):
                continue

            descr = result.get("about_this_result", {}).get("source", {}).get("description", "")
            snippet = result.get("snippet", "")
            description = descr or snippet

            metadata.append(dict(title=result.get("title", ""), link=link, description=description))

        return metadata

    @staticmethod
    def get_search_params(query: str, language: Language, num: int = 30) -> dict:
        """
        Builds request parameters based on the provided options.

        Args:
            query: page topic.
            language: cluster localization.
            num: number of results

        Returns:
            A search parameters for the given query and language.
        """
        return {
            "q": query,
            "location": language.country_name,
            "hl": language.language_code.lower(),
            "gl": language.lower(),
            "google_domain": "google.com",
            "api_key": settings.scraper.API_KEY,
            "num": num,
        }

    @staticmethod
    async def collect_search(params: dict) -> dict | None:
        """
        Collects search data asynchronously using the given input parameters.

        Args:
            params: Parameters for the search request.

        Returns:
            A dictionary containing search data if the request is successful, otherwise None.
        """

        try:
            async with ClientSession() as s, s.get(f"{settings.scraper.BASE_URL}/search", params=params) as response:
                body = await response.text()
                response.raise_for_status()
                return loads(body)

        except ClientResponseError:
            logger.error(f"ClientResponseError: {response.status} - {body}")
        except Exception as e:
            logger.error(f"Error: {e}")

        return None

    @classmethod
    async def get_documents(cls, data: dict) -> list[Document]:
        """
        Fetches documents from the specified URL and parses it into metadata and content.

        Args:
            data: Search data.

        Returns:
            A list of documents.
        """

        request_service = ScraperRequestService()
        urls = cls.get_results(data=data)

        await request_service.setup(urls=urls)
        return await request_service.aload()

    @classmethod
    async def check_website(cls, query: str, target_url: str, language: Language) -> bool:
        params = cls.get_search_params(query=query, language=language, num=200)
        search_data = await cls.collect_search(params)

        logger.debug(f"Search data: {search_data}")

        if not search_data:
            return False

        links = cls.get_results(search_data)

        logger.debug(f"Links: {links}")

        return any(target_url in link for link in links)
