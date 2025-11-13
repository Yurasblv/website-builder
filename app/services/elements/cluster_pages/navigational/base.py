from typing import Any

from loguru import logger
from sentry_sdk import capture_exception

from app.enums import Commercial1TagType, ElementPrompts, NavigationalElementType
from app.schemas.elements.cluster_pages.base import (
    ElementContent,
    ElementSettings,
    H2ContentInput,
    H2ContentOutput,
    H2HeaderSchema,
    StringElementOutput,
)
from app.services.elements.cluster_pages.base import ElementServiceBase
from app.utils.convertors import text_normalize
from app.utils.decorators import traceable_generate


class NavigationalPageElementService(ElementServiceBase):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.context = ""

    async def __aenter__(self) -> "NavigationalPageElementService":
        await super().__aenter__()

        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await super().__aexit__(exc_type, exc, tb)

    async def create_head_content_tag(self, element_content: ElementContent) -> ElementContent:
        element_content = await super().create_head_content_tag(element_content)
        if element_content.processed:
            main_header_r: StringElementOutput = await self.ai.gpt_request(
                prompt=ElementPrompts.H1_GENERATION_TEMPLATE,
                assistant=ElementPrompts.H1_GENERATION_ASSISTANT,
                output_schema=StringElementOutput,
                keyword=self.cluster_keyword,
                topic=self.page_metadata.topic_name,
                language=self.language,
                country=self.target_country,
            )

            refactored_data: StringElementOutput = await self.ai.replace_string_camel_case(
                input_string=main_header_r.data, language=self.language
            )

            head_no_banwords: str = refactored_data.get_normalized(language=self.language)

            element_content.content = head_no_banwords or main_header_r.data

        return element_content

    async def create_h2_contents(self, elements: list[ElementContent]) -> list[ElementContent]:
        upd = []

        data = H2ContentInput(
            summary=self.page_metadata.text_info.summary,
            n_words=self.page_metadata.text_info.n_words,
            h2_tags_number=self.page_metadata.text_info.h2_tags_number,
        )

        response: H2ContentOutput = await super().create_h2_content(data=data)

        if not response:
            return elements

        h2_headers: list[H2HeaderSchema] = await self.create_h2_headers(
            content=[element.content for element in response.h2_data],
            h2_tags_number=self.page_metadata.text_info.h2_tags_number,
        )

        if not h2_headers:
            return elements

        header_iter = iter(h2_headers)
        content_summary: StringElementOutput = await self.ai.gpt_request(
            prompt=ElementPrompts.CONTENT_SUMMARY_TEMPLATE.format(content=response.h2_data, language=self.language),
            output_schema=StringElementOutput,
        )

        self.context = content_summary.data

        try:
            for idx, el in enumerate(elements):
                if el.tag not in NavigationalElementType.h2_injection_elements():
                    upd.append(el)
                    continue

                if not (header := next(header_iter, None)):
                    continue

                h2_element = ElementContent(
                    tag=Commercial1TagType.H2,
                    content=header.long,
                    position=el.position + 1,
                    processed=True,
                    settings=ElementSettings(content=header.short),
                    content_id=text_normalize(header.short),
                )

                h2_element.children.extend([response.h2_data[0]])

                replace_el_pos = idx + 1

                def update_position(element: ElementContent) -> None:
                    element.position += 1
                    for child in element.children:
                        update_position(child)

                for element in elements[replace_el_pos:]:
                    update_position(element)

                upd.extend([el, h2_element])

        except Exception as e:
            capture_exception(e)
            logger.warning(f"Error in NavigationalPageElementService.create_h2_contents: {e}")
            return elements

        return upd

    @traceable_generate(tags=[NavigationalElementType.REFERENCES])
    async def create_references_element(
        self,
        elements: list[ElementContent],
        progress_per_element: float,
    ) -> list[ElementContent]:
        # TODO: add reference processing
        return elements
