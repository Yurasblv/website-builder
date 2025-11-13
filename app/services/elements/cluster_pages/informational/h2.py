import random
from typing import Any

from loguru import logger
from sentry_sdk import capture_exception

from app.enums import ClusterEventEnum, ElementPrompts, InformationalElementType
from app.enums.elements.page_cluster.informational import InformationalTagType
from app.schemas.elements import ElementContent, H2ContentInput, H2ContentOutput
from app.schemas.elements.cluster_pages.base import (
    ElementSettings,
    H2HeaderSchema,
    ListElementOutput,
    StringElementOutput,
)
from app.services.ai import AIBase, ChainBuilder
from app.services.elements.cluster_pages.informational.base import InformationalPageElementService
from app.utils import traceable_generate
from app.utils.convertors import text_normalize
from app.utils.message_queue import enqueue_global_message


class InformationalPageH2Service(InformationalPageElementService):
    def __init__(self, ai: AIBase, chain_builder: ChainBuilder, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.ai = ai
        self.chain_builder = chain_builder

        self.h1_positions: list[int] = []
        self.h2_positions: list[int] = []

    async def __aenter__(self) -> "InformationalPageH2Service":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None: ...

    @staticmethod
    def distribute_h2(injection_elements: list[str], h2_tags_number: int) -> dict:
        if not injection_elements:
            return {InformationalElementType.HEAD_CONTENT: h2_tags_number}

        h2_distribution = {el: 0 for el in injection_elements}

        for _ in range(h2_tags_number):
            key = random.choice(list(h2_distribution.keys()))
            h2_distribution[key] += 1

        return h2_distribution

    def sort_elements(self, content: list[ElementContent], h2_positions: dict) -> list[ElementContent]:
        sorted_content_list: list[ElementContent] = []
        for v in content:
            v.position = len(sorted_content_list)

            for child in v.children:
                child.position = v.position

            if v.tag == InformationalElementType.HEAD_CONTENT:
                self.h1_positions.append(v.position)

            sorted_content_list.append(v)
            h2_count = h2_positions.get(v.tag, 0)

            if not h2_count:
                continue

            for i in range(h2_count):
                h2_element = ElementContent(tag=InformationalElementType.H2, position=v.position + i + 1)
                sorted_content_list.append(h2_element)

        return sorted_content_list

    @staticmethod
    def _renew_text_info(avg: int, default: int, upper_limit: int | None = None) -> int:
        result = max(int(avg), default)

        if upper_limit:
            return min(result, upper_limit)

        return result

    async def renew_text_info(self, h2_tags_limit: int) -> tuple[int, ...]:
        h2_tags_number = self._renew_text_info(
            self.page_metadata.text_info.h2_tags_number, default=max(h2_tags_limit, 1), upper_limit=10
        )
        n_words = self._renew_text_info(self.page_metadata.text_info.h2_tags_number, default=int(1500 / h2_tags_number))

        return h2_tags_number, n_words

    @traceable_generate(
        tags=["H2_CONTENT"],
    )
    async def create_h2_contents(
        self, elements: list[ElementContent], progress_per_element: float
    ) -> list[ElementContent]:
        # H2_HEADER 0 -> n P -> H2_HEADER -> n P ...
        logger.info(f"PageCluster {self.page_metadata.topic_name} creating H2 elements")

        injection_elements = [el.tag for el in elements if el.tag in InformationalElementType.h2_injection_elements()]
        logger.info(f"Start scrapper analyzing, page = {self.page_metadata.topic_name}")

        h2_tags_number, n_words = await self.renew_text_info(h2_tags_limit=len(injection_elements))

        total_article_length = h2_tags_number * n_words
        logger.info(
            f"Scrapper analyzed page = {self.page_metadata.topic_name}: "
            f"h2 number = {h2_tags_number},"
            f"summary length of h2 tags = {total_article_length}"
        )

        if self.generation_key:
            await enqueue_global_message(
                event=ClusterEventEnum.GENERATING,
                generation_key=self.generation_key,
                progress=progress_per_element * 0.1,
                message="Scraping documents",
            )

        progress_per_h2 = (progress_per_element * 0.9) / h2_tags_number

        h2_positions = self.distribute_h2(injection_elements=injection_elements, h2_tags_number=h2_tags_number)

        sorted_content_list = self.sort_elements(elements, h2_positions)

        logger.info(f"PageCluster {self.page_metadata.topic_name} creating element = {InformationalElementType.H2}")
        output: H2ContentOutput = await self.create_h2_content(
            H2ContentInput(
                summary=self.page_metadata.text_info.summary,
                n_words=int(total_article_length * 1.3),
                h2_tags_number=h2_tags_number,
            )
        )

        h2_headers: list[H2HeaderSchema] = await self.create_h2_headers(
            content=[element.content for element in output.h2_data],
            h2_tags_number=h2_tags_number,
        )

        content_summary: StringElementOutput = await self.ai.gpt_request(
            prompt=ElementPrompts.CONTENT_SUMMARY_TEMPLATE.format(content=output.h2_data, language=self.language),
            output_schema=StringElementOutput,
        )

        self.context = content_summary.data

        current_h2 = 0
        try:
            for el in sorted_content_list:
                if el.tag != InformationalElementType.H2:
                    continue

                h2_header = h2_headers.pop(0)
                text_block = output.h2_data.pop(0)

                chunks: ListElementOutput = await self.ai.gpt_request(
                    prompt=ElementPrompts.P_TAG_CHUNKING_TEMPLATE,
                    output_schema=ListElementOutput,
                    text=text_block.content,
                )

                dumped_chunks: list[ElementContent] = [
                    ElementContent(
                        tag=InformationalTagType.P,
                        content=paragraph,
                        html=True,
                        processed=True,
                    )
                    for paragraph in chunks.data
                ]

                el.content_id = text_normalize(h2_header.short)
                el.settings = ElementSettings(content=h2_header.short)
                el.content = h2_header.long
                el.children.extend(dumped_chunks)
                el.processed = True

                self.h2_positions.append(el.position)

                current_h2 += 1
                await enqueue_global_message(
                    event=ClusterEventEnum.GENERATING,
                    generation_key=self.generation_key,
                    progress=progress_per_h2,
                    message=f"Creating H2 element {current_h2}/{h2_tags_number}",
                )
        except Exception as e:
            capture_exception(e)
            logger.warning(f"An unexpected error occurred: {e}")

        # TODO return summary
        return sorted_content_list
