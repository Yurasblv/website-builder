import asyncio
import re
from typing import Any
from uuid import uuid4

from aiohttp import BasicAuth, ClientSession
from loguru import logger

from app.core.config import settings
from app.enums import ClusterEventEnum, Country, ElementPrompts, InformationalElementType, Language
from app.schemas.elements import ElementContent, ListElementOutput, ReferencesContentSchema, StringElementOutput
from app.schemas.page.cluster_page import ClusterPageGenerationMetadata
from app.schemas.page.pbn_page import PBNExtraPageGenerationMetadata
from app.services.ai import AIBase
from app.services.proxy import proxy_service
from app.services.scraper import Scraper
from app.utils import enqueue_global_message, traceable_generate, uppercase_first_letter


class ReferencePageElementService:
    def __init__(
        self,
        user_email: str,
        ai: AIBase,
        scraper: Scraper,
        target_country: Country,
        language: Language,
        page_metadata: ClusterPageGenerationMetadata | PBNExtraPageGenerationMetadata,
    ) -> None:
        self.user_email = user_email
        self.ai = ai
        self.scraper = scraper
        self.page_metadata = page_metadata
        self.target_country = target_country
        self.language = language

    async def __aenter__(self) -> "ReferencePageElementService":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None: ...

    async def get_relevant_h2_texts(self, h2_positions: list, elements: list[ElementContent]) -> list[str]:
        texts_list: list = []

        for element in elements:
            if element.position in h2_positions:
                texts_list.extend([el.content for el in element.children])

        if not texts_list:
            return texts_list

        response = await self.ai.gpt_request(
            prompt=ElementPrompts.REFERENCES_KEYWORDS_EXTRACTION_TEMPLATE,
            output_schema=ListElementOutput,
            system=settings.ai.OPENAI_JOURNALIST_ROLE,
            texts_list=texts_list,
            language=self.language,
        )

        if response:
            return response.data

        return texts_list

    async def validate_footprint_source(self, metadata_list: list[dict]) -> list[dict] | None:
        proxies = []
        method = self.validate_url

        if settings.scraper.USE_PROXY:
            proxies = (await proxy_service.get_proxies())[:5]
            method = self.validate_url_with_proxy

        async with ClientSession(headers={"User-Agent": settings.scraper.USER_AGENT}) as session:
            task = [method(session, metadata, proxies) for metadata in metadata_list]
            results = await asyncio.gather(*task)

            return [metadata for metadata in results if metadata]

    @staticmethod
    async def validate_url_with_proxy(session: ClientSession, metadata: dict, proxies: list) -> dict | None:
        for proxy in proxies:
            try:
                link = metadata.get("link")
                proxy_url = proxy.get("server")
                auth = BasicAuth(proxy.get("username"), proxy.get("password"))

                async with session.get(link, proxy=proxy_url, proxy_auth=auth, timeout=10) as response:
                    response.raise_for_status()
                    content_type = response.headers.get("Content-Type", "")

                    pattern = "|".join(["text/html", "text/plain"])

                    if re.search(pattern, content_type):
                        return metadata

            except Exception as e:
                logger.debug(f"Error validating source: {e}")
                continue

    @staticmethod
    async def validate_url(session: ClientSession, metadata: dict, *_: Any, **__: Any) -> dict | None:
        try:
            async with session.get(metadata.get("link"), timeout=10) as response:
                response.raise_for_status()
                content_type = response.headers.get("Content-Type", "")

                pattern = "|".join(["text/html", "text/plain"])

                if re.search(pattern, content_type):
                    return metadata

        except Exception as e:
            logger.debug(f"Error validating source: {e}")

    async def search_footprint_source(self, query: str) -> str | None:
        try:
            search_params = self.scraper.get_search_params(query=query, language=self.language, num=10)
            data = await self.scraper.collect_search(params=search_params)

            if not data:
                return None

            metadata_list = self.scraper.get_metadata_from_results(data=data)
            validated_source = await self.validate_footprint_source(metadata_list)

            if not validated_source:
                return None

            response = await self.ai.gpt_request(
                prompt=ElementPrompts.REFERENCES_URL_SELECTOR_TEMPLATE,
                output_schema=StringElementOutput,
                system=settings.ai.OPENAI_JOURNALIST_ROLE,
                keyword=query,
                metadata_list=validated_source,
            )

            if response:
                return response.data

        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")

    @traceable_generate(tags=[InformationalElementType.REFERENCES])
    async def create_references_element(
        self,
        generation_key: str,
        elements: list[ElementContent],
        h2_positions: list[int],
        ban_keywords: set[str],
        progress_per_element: float,
    ) -> None:
        keywords = await self.get_relevant_h2_texts(h2_positions=h2_positions, elements=elements)
        keywords = [kw for kw in keywords if kw not in ban_keywords]
        keyword_limit = min(5, len(keywords))
        if not keyword_limit:
            return None

        progress_per_keyword = progress_per_element / keyword_limit

        logger.info(f"keywords: {keywords}")

        if not keywords:
            return None

        s_pos = 1

        references_content = ""

        for kw in keywords:
            if s_pos > 5:
                break

            try:
                href = await self.search_footprint_source(query=kw)

                if not href:
                    continue

                fn_id = str(uuid4())
                insert_value = f'<ref fn_item_id="{fn_id}">{s_pos}</ref>'

                for element in elements:
                    if element.position not in h2_positions:
                        continue

                    for inner_el in element.children:
                        upd_content = self.inject_text_reference(
                            keyword=kw, text=inner_el.content, value=insert_value, ban_keywords=ban_keywords
                        )

                        if upd_content != inner_el.content:
                            inner_el.content = upd_content

                            break

                content = uppercase_first_letter(kw)
                references_content += ReferencesContentSchema(id=fn_id, href=href, content=content).model_dump_json()
                s_pos += 1

                if generation_key:
                    await enqueue_global_message(
                        event=ClusterEventEnum.GENERATING,
                        generation_key=generation_key,
                        progress=progress_per_keyword,
                        message="Injecting references",
                    )

            except Exception as e:
                logger.warning(f"Error injecting references: {e}")
                continue

        if generation_key:
            rest_progress = progress_per_element - progress_per_keyword * s_pos
            if rest_progress > 0:
                await enqueue_global_message(
                    event=ClusterEventEnum.GENERATING,
                    generation_key=generation_key,
                    progress=rest_progress,
                    message="References injection completed",
                )

        if not references_content:
            return

        for el in elements:
            if el.tag == InformationalElementType.REFERENCES:
                el.processed = True
                el.content = references_content

    @staticmethod
    def inject_text_reference(keyword: str, text: str, value: str, ban_keywords: set[str]) -> str:
        unique_replacements = {}
        ban_intervals = []
        end_chars = [".", ",", "!", "?", " "]

        for ban_keyword in ban_keywords:
            pattern = rf"(?i)\b({re.escape(ban_keyword)})\b(?![s'\"])"

            for match in re.finditer(pattern, text):
                ban_intervals.append((match.start(), match.end()))

        for match in re.finditer(rf"(?i)\b({re.escape(keyword)})\b(?![s'\"])", text):
            if any(start <= match.start() <= end for start, end in ban_intervals):
                continue

            replacement = match.group(0)

            # check if next character is allowed char
            if match.end() < len(text) and text[match.end()] not in end_chars:
                continue

            while True:  # generate unique key
                key = f"<{uuid4()}"[: len(replacement) - 1] + ">"
                if key not in unique_replacements:
                    break

            unique_replacements[key] = replacement + value
            text = text[: match.start()] + key + text[match.end() :]

        for key, replacement in unique_replacements.items():
            text = text.replace(key, replacement)

        return text
