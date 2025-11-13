import random
import re
from typing import Any

from langsmith import traceable
from loguru import logger
from sentry_sdk import capture_exception

from app.enums import InformationalElementType, Language, StructurePrompts
from app.schemas import BacklinkResponse, ClusterPageGenerationMetadata, ElementContent, StringElementOutput
from app.services import AIBase


class HyperlinkInjector:
    def __init__(self, page_metadata: ClusterPageGenerationMetadata, language: Language, ai: AIBase = AIBase()) -> None:
        self.page_metadata = page_metadata
        self.ai = ai
        self.language = language
        self.ban_keywords: set[str] = set()
        self.anchor = '<a href="{link}">{title}</a>'
        self.named_anchor = '<a id="{link}">{title}</a>'
        self.keyword_pattern = "<<keyword>>"
        self.default_temperature = 0.7

    async def __aenter__(self) -> "HyperlinkInjector":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None: ...

    @staticmethod
    def replace(pattern: str, link: str, response: BacklinkResponse) -> str:
        pattern_formatted = pattern.format(link=link, title=response.anchor)

        return re.sub(
            rf"({response.anchor})",
            rf"{pattern_formatted}",
            response.text,
        )

    @staticmethod
    def _categorize_elements(
        elements: list[ElementContent], h1_positions: list[int], h2_positions: list[int]
    ) -> tuple[list[ElementContent], list[ElementContent], list[ElementContent]]:
        h1_elements: list[ElementContent] = []
        h2_elements: list[ElementContent] = []
        updated_elements: list[ElementContent] = []

        for el in elements:
            if el.position in h1_positions:
                h1_elements.append(el)

            elif el.position in h2_positions:
                h2_elements.append(el)

            else:
                updated_elements.append(el)

        return h1_elements, h2_elements, updated_elements

    async def _process_h1_elements(
        self, h1_positions: list[int], elements: list[ElementContent]
    ) -> list[ElementContent]:
        for element in elements:
            if element.position in h1_positions:
                await self._process_main_source_link(h1_element=element)
                await self._process_parent_link(h1_element=element)

        return elements

    async def _process_main_source_link(self, h1_element: ElementContent) -> None:
        if not self.page_metadata.main_source_link:
            return None

        context = "\n".join([el.content for el in h1_element.children])

        if not context:
            return None

        keyword = self.page_metadata.main_source_link.keyword
        anchor_link = self.page_metadata.main_source_link.link

        sentence_response = await self._process_keyword(
            keyword=keyword, context=context, anchor_link=anchor_link, pattern=self.anchor
        )

        if sentence := sentence_response:
            h1_element.children[random.randint(0, len(h1_element.children) - 1)].content += sentence
            self.ban_keywords.add(keyword)

    async def _process_parent_link(self, h1_element: ElementContent) -> None:
        if not self.page_metadata.has_parent:
            return None

        context = "\n".join([el.content for el in h1_element.children])

        if not context:
            return None

        keyword: str = self.page_metadata.parent_topic
        anchor_link: str = self.page_metadata.parent_url

        sentence_response = await self._process_keyword(
            keyword=keyword, context=context, anchor_link=anchor_link, pattern=self.named_anchor
        )

        if sentence := sentence_response:
            h1_element.children[random.randint(0, len(h1_element.children) - 1)].content += sentence
            self.ban_keywords.add(keyword)

    @traceable(tags=[InformationalElementType.REFERENCES])
    async def _process_keyword(self, keyword: str, context: str, anchor_link: str, pattern: str) -> str:
        while True:
            response: BacklinkResponse = await self.ai.instructor_request(
                prompt=StructurePrompts.EXTRA_TEXT_INCORPORATION_TEMPLATE.format(
                    language=self.language,
                    topic=self.page_metadata.topic_name,
                    keyword=keyword,
                    context=context,
                ),
                output_schema=BacklinkResponse,
            )

            if response.anchor in response.text:
                break

        response_no_banwords = response.get_normalized(language=self.language)

        formatted_response = self.replace(pattern=pattern, link=anchor_link, response=response_no_banwords)

        return formatted_response

    async def _process_h2_elements(
        self, h2_positions: list[int], elements: list[ElementContent]
    ) -> list[ElementContent]:
        """
        Unused method
        """

        async def process(h2_element: ElementContent, relations: list[tuple]) -> None:
            if not relations or not h2_element.children:
                return

            for _id, _topic in relations:
                random_index = random.randint(0, len(h2_element.children) - 1)
                h2_p_element = h2_element.children[random_index]

                response = await self.ai.instructor_request(
                    prompt=StructurePrompts.ANCHOR_WORD_SELECTION_TEMPLATE.format(
                        language=self.language,
                        anchor_word=_topic,
                        text=h2_p_element.content,
                    )
                    + StructurePrompts.ANCHOR_WORDS_STOP_LIST.format(exclude_keywords=self.ban_keywords),
                    output_schema=StringElementOutput,
                )
                target_keyword = response.data
                insert_value = self.named_anchor.format(id=_id, name=_topic, title=_topic)
                h2_p_element.content = re.sub(f"({target_keyword})", insert_value, h2_p_element.content, count=1)
                self.ban_keywords.add(target_keyword)

        for element in elements:
            if element.position in h2_positions:
                await process(element, self.page_metadata.neighbours)
                await process(element, self.page_metadata.children)

        return elements

    async def inject_hyperlinks(
        self,
        elements: list[ElementContent],
        h1_positions: list[int],
        h2_positions: list[int],
    ) -> list[ElementContent]:
        try:
            elements = await self._process_h1_elements(h1_positions=h1_positions, elements=elements)
            # TODO: add relations for h2 tags
            # elements = await self._process_h2_elements(h2_positions, elements=elements)

        except Exception as e:
            capture_exception(e)
            logger.warning(f"Error injecting hyperlinks: {e}")

        return elements
