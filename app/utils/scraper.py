from math import ceil
from typing import Any, AsyncIterator

import aiohttp
from aiohttp import BasicAuth, ClientProxyConnectionError, ClientTimeout, ServerDisconnectedError
from aiohttp.client_exceptions import ClientResponseError, ConnectionTimeoutError
from bs4 import BeautifulSoup
from langchain_core.documents import BaseDocumentTransformer, Document
from loguru import logger
from sentry_sdk import capture_exception

from app.core import settings


class H2TagsTransformer(BaseDocumentTransformer):
    def transform_documents(self, documents: list[Document], **kwargs: Any) -> list[Document]:
        transformed_documents = []
        for doc in documents:
            soup = BeautifulSoup(doc.page_content, "html.parser")
            try:
                h2_tags = soup.find_all("h2")
                p_tags = soup.find_all("p")

                if not p_tags or not h2_tags:
                    continue

                p_words = []
                for p in p_tags:
                    p_words.extend(p.text.split())

                for script in soup(["script", "style"]):
                    script.extract()

                text = soup.get_text(separator="\n")
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                cleaned_text = "\n".join(lines)

                new_doc = Document(
                    page_content=cleaned_text,
                    metadata={
                        **doc.metadata,
                        "h2_count": len(h2_tags),
                        "p_avg_words": ceil(len(p_words) / len(p_tags)),
                    },
                )
                transformed_documents.append(new_doc)

            except Exception as e:
                capture_exception(e)
                continue

        return transformed_documents

    async def atransform_documents(self, documents: list[Document], **kwargs: Any) -> list[Document]:
        raise NotImplementedError


class ScraperRequestService:
    def __init__(self) -> None:
        self.proxies: list[dict] = []
        self.urls: list[str] = []
        self.user_agent = settings.scraper.USER_AGENT

    async def setup(self, urls: list[str], user_agent: str = None) -> None:
        """Setting up the scraper with proxies if enabled in the settings."""
        from app.services.proxy import proxy_service

        if settings.scraper.USE_PROXY:
            self.proxies = await proxy_service.get_proxies()

        self.urls = urls
        self.user_agent = user_agent or self.user_agent

    async def lazy_load(self) -> AsyncIterator[Document]:
        """
        Lazily load text content from the provided URLs.

        This method yields Documents one at a time as they're scraped,
        instead of waiting to scrape all URLs before returning.

        Yields:
            Document: The scraped content encapsulated within a Document object.
        """
        processed_urls = 0
        for url in self.urls[:10]:
            html_content = await self.ascrape_with_request(url)

            if not html_content:
                logger.info(f"Failed to scrape content for {url}, html is empty.")
                continue

            yield Document(page_content=html_content, metadata={"source": url})

            processed_urls += 1
            if processed_urls >= settings.scraper.MAX_LINKS:
                break

    async def aload(self) -> list[Document]:
        """
        Load and return all Documents from the provided URLs.

        Returns:
            list[Document]: A list of Document objects
            containing the scraped content from each URL.

        """
        documents = []
        async for document in self.lazy_load():
            documents.append(document)
        logger.info(f"Scraped documents: {[document.metadata for document in documents if documents]}")
        return documents

    async def ascrape_with_request(self, url: str) -> str | None:
        """
        Asynchronously scrape the content of a given URL using the httpx library.

        Args:
            url: The URL to scrape.

        Returns:
            The scraped HTML content or an error message if an exception occurs.

        """
        if settings.scraper.USE_PROXY:
            return await self._scrape_with_proxy(url)

        return await self._scrape(url)

    async def _scrape(self, url: str) -> str | None:
        logger.debug(f"Starting scraping {url}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url=url,
                    headers={"User-Agent": self.user_agent},
                    timeout=ClientTimeout(total=settings.scraper.TIMEOUT),
                ) as response:
                    response.raise_for_status()
                    content = await response.text()
                    logger.success("Content scraped")
                    return content

        except (ClientResponseError, ConnectionTimeoutError) as e:
            capture_exception(e)

        except Exception:
            pass

    async def _scrape_with_proxy(self, url: str) -> str | None:
        logger.debug(f"Starting scraping {url} with proxy")
        break_exception = (ClientProxyConnectionError, ServerDisconnectedError)

        for proxy in self.proxies[: settings.scraper.MAX_LINKS]:
            headers = {"User-Agent": self.user_agent}
            proxy_url = proxy["server"]
            proxy_auth = BasicAuth(proxy["username"], proxy["password"])

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url=url,
                        headers=headers,
                        proxy=proxy_url,
                        proxy_auth=proxy_auth,
                        timeout=ClientTimeout(total=settings.scraper.TIMEOUT),
                    ) as response:
                        response.raise_for_status()
                        content = await response.text()
                        logger.success("Content scraped")
                        return content

            except (ClientResponseError, ConnectionTimeoutError) as e:
                capture_exception(e)
                break

            except Exception as e:
                if any(isinstance(e, exception) for exception in break_exception):
                    break
