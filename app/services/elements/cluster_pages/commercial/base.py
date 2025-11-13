import random
from typing import Any

from loguru import logger

from app.enums import (
    ClusterEventEnum,
    Commercial1CTATags,
    Commercial1TagType,
    CommercialPagePrompt,
    ElementPrompts,
)
from app.enums.elements import Commercial1InnerCTATags
from app.schemas import StringElementOutput
from app.schemas.elements.cluster_pages.base import (
    ElementContent,
    ElementSettings,
    H2ContentInput,
    H2ContentOutput,
    H2HeaderSchema,
)
from app.schemas.elements.cluster_pages.commercial_page import BenefitsGrid, Card, CTASection, FeaturesSection
from app.services.elements.cluster_pages.base import ElementServiceBase
from app.utils import enqueue_global_message, retry_element_processing, traceable_generate
from app.utils.convertors import text_normalize


class CommercialPageElementService(ElementServiceBase):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.context = ""

    async def __aenter__(self) -> "CommercialPageElementService":
        await super().__aenter__()

        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await super().__aexit__(exc_type, exc, tb)

    @retry_element_processing
    @traceable_generate(
        tags=["CTA"],
    )
    async def create_cta(self, element_content: ElementContent) -> ElementContent:
        if element_content.processed:
            return element_content

        logger.info(f"Cluster page {self.page_metadata.topic_name} creating CTA content")

        response: CTASection = await self.ai.instructor_request(
            prompt=CommercialPagePrompt.CTA_SECTION_PROMPT_TEMPLATE.format(
                keyword=self.cluster_keyword,
                topic=self.page_metadata.topic_name,
                language=self.language,
                country=self.target_country,
            ),
            output_schema=CTASection,
        )

        if not response:
            return element_content

        fixed_cta: CTASection = response.get_normalized(language=self.language)

        element_content.children.extend(
            [
                ElementContent(
                    tag=Commercial1CTATags.CTA_HEADING_TEXT,
                    content=fixed_cta.headline,
                    position=element_content.position,
                    processed=True,
                ),
                ElementContent(
                    tag=Commercial1CTATags.CTA_DESCRIPTION_TEXT,
                    content=fixed_cta.paragraph,
                    position=element_content.position,
                    processed=True,
                ),
            ]
        )

        img = await self.create_image_content(
            element_content=ElementContent(tag=Commercial1CTATags.CTA_IMG, position=element_content.position),
            summary=response.paragraph,
        )

        if img and img.processed:
            element_content.href = img.href

        return element_content

    @retry_element_processing
    @traceable_generate(
        tags=["FEATURES"],
    )
    async def create_features(self, element_content: ElementContent) -> ElementContent:
        logger.info(f"Cluster page {self.page_metadata.topic_name} creating FEATURES content")

        response: FeaturesSection = await self.ai.instructor_request(
            prompt=CommercialPagePrompt.FEATURES_SECTION_PROMPT_TEMPLATE.format(
                keyword=self.cluster_keyword,
                topic=self.page_metadata.topic_name,
                language=self.language,
                country=self.target_country,
            ),
            output_schema=FeaturesSection,
            assistant=CommercialPagePrompt.FEATURES_SECTION_ASSISTANT,
            temperature=0.9,
        )

        if not response:
            return element_content

        if response:
            fixed_features: FeaturesSection = response.get_normalized(language=self.language)
            element_content.content = fixed_features.model_dump_json(exclude={"features"})

            for f in fixed_features.features:
                element_content.children.append(
                    ElementContent(
                        tag=Commercial1TagType.DIV, content=f.model_dump_json(warnings=False), processed=True
                    )
                )

        if element_content.children:
            element_content.processed = True

            features_img = await self.create_image_content(
                element_content=ElementContent(tag=Commercial1TagType.IMG, position=element_content.position),
                summary=fixed_features.paragraph,
            )

            if features_img and features_img.processed:
                element_content.href = features_img.href

        return element_content

    @retry_element_processing
    @traceable_generate(
        tags=["BENEFITS"],
    )
    async def create_benefits(self, element_content: ElementContent) -> ElementContent:
        logger.info(f"Cluster page {self.page_metadata.topic_name} creating BENEFITS content")

        response: BenefitsGrid = await self.ai.instructor_request(
            prompt=CommercialPagePrompt.BENEFITS_SECTION_PROMPT_TEMPLATE.format(
                keyword=self.cluster_keyword,
                topic=self.page_metadata.topic_name,
                language=self.language,
                country=self.target_country,
            ),
            output_schema=BenefitsGrid,
            assistant=CommercialPagePrompt.BENEFITS_SECTION_ASSISTANT,
        )

        if response:
            fixed_benefits: BenefitsGrid = response.get_normalized(language=self.language)
            element_content.content = response.header

            for b in fixed_benefits.benefits:
                element_content.children.append(
                    ElementContent(
                        tag=Commercial1TagType.DIV,
                        content=b.model_dump_json(warnings=False),
                        processed=True,
                        classname="default",
                    )
                )

        element_content.processed = bool(element_content.children)

        return element_content

    @retry_element_processing
    @traceable_generate(
        tags=["GRID"],
    )
    async def create_grid(self, element_content: ElementContent) -> ElementContent:
        logger.info(f"Cluster page {self.page_metadata.topic_name} creating GRID content")

        relations = random.sample(self.page_metadata.relations, min(len(self.page_metadata.relations), 6))

        if not relations:
            return element_content

        main_header_r: StringElementOutput = await self.ai.gpt_request(
            prompt=ElementPrompts.H1_GENERATION_TEMPLATE,
            assistant=ElementPrompts.H1_GENERATION_ASSISTANT,
            output_schema=StringElementOutput,
            keyword=self.cluster_keyword,
            topic=self.page_metadata.topic_name,
            language=self.language,
            country=self.target_country,
        )

        main_header = main_header_r.data

        formatted_header: StringElementOutput = await self.ai.replace_string_camel_case(
            input_string=main_header, language=self.language
        )
        header_no_banwords: str = formatted_header.get_normalized(language=self.language)
        element_content.content = header_no_banwords or main_header

        for r in relations:
            card_response: Card = await self.ai.instructor_request(
                prompt=CommercialPagePrompt.CARD_PROMPT_TEMPLATE.format(
                    keyword=self.cluster_keyword,
                    topic=r[1],
                    language=self.language,
                    country=self.target_country,
                ),
                output_schema=Card,
            )

            response: Card = card_response.get_normalized(language=self.language)

            card_e = ElementContent(
                tag=Commercial1TagType.CARD,
                position=element_content.position,
                classname="default",
                processed=True,
                children=[
                    ElementContent(
                        tag=Commercial1TagType.A,
                        position=element_content.position,
                        href=str(r[0]),
                        classname="default",
                        processed=True,
                    )
                ],
            )

            if not response:
                card_e.content = r[1]
                element_content.children.append(card_e)
                continue

            card_e.content = response.model_dump_json(warnings=False)
            card_img = await self.create_image_content(
                element_content=ElementContent(tag=Commercial1TagType.IMG, position=element_content.position),
                summary=f"{r[1]}: {response.description}",
            )

            if card_img.processed:
                card_e.href = card_img.href

            element_content.children.append(card_e)

        element_content.processed = bool(element_content.children)

        return element_content

    async def create_h2_contents(
        self, elements: list[ElementContent], progress_per_element: float
    ) -> list[ElementContent]:
        logger.info(f"Cluster page {self.page_metadata.topic_name} creating H2 content")

        data = H2ContentInput(
            summary=self.page_metadata.text_info.summary,
            n_words=self.page_metadata.text_info.n_words,
            h2_tags_number=self.page_metadata.text_info.h2_tags_number,
        )

        h2_response: H2ContentOutput = await super().create_h2_content(data=data)
        headers: list[H2HeaderSchema] = await self.create_h2_headers(
            content=[element.content for element in h2_response.h2_data],
            h2_tags_number=self.page_metadata.text_info.h2_tags_number,
        )
        content_summary: StringElementOutput = await self.ai.gpt_request(
            prompt=ElementPrompts.CONTENT_SUMMARY_TEMPLATE.format(content=h2_response.h2_data, language=self.language),
            output_schema=StringElementOutput,
        )

        self.context = content_summary.data

        progress_per_h2 = (progress_per_element * 0.9) / self.page_metadata.text_info.h2_tags_number

        for idx, el in enumerate(elements):
            if el.tag != "GRID":
                continue

            try:
                main_header_r: StringElementOutput = await self.ai.gpt_request(
                    prompt=ElementPrompts.H1_GENERATION_TEMPLATE,
                    assistant=ElementPrompts.H1_GENERATION_ASSISTANT,
                    output_schema=StringElementOutput,
                    keyword=self.cluster_keyword,
                    topic=self.page_metadata.topic_name,
                    language=self.language,
                    country=self.target_country,
                )

                reformated_header: StringElementOutput = await self.ai.replace_string_camel_case(
                    input_string=main_header_r.data, language=self.language
                )

                header_no_banwords: str = reformated_header.get_normalized(language=self.language)

                main_header = header_no_banwords or main_header_r.data

                h2_container = ElementContent(
                    tag=Commercial1TagType.H2,
                    content=main_header,
                    position=el.position + 1,
                    processed=True,
                )

                current_h2 = 0
                for idx, header in enumerate(headers):
                    h2_element = ElementContent(
                        tag=Commercial1TagType.H2,
                        content=header.long,
                        position=h2_container.position,
                        processed=True,
                        settings=ElementSettings(content=header.short),
                        content_id=text_normalize(header.short),
                    )

                    response: H2ContentOutput = await super().create_h2_content(data=data)

                    h2_element.children.extend([response.h2_data[idx]])
                    h2_container.children.append(h2_element)

                    current_h2 += 1

                    if self.generation_key:
                        await enqueue_global_message(
                            event=ClusterEventEnum.GENERATING,
                            generation_key=self.generation_key,
                            progress=progress_per_h2,
                            message=f"Creating H2 element {current_h2}/{len(headers)}",
                        )

                if h2_container.children:
                    replace_el_pos = idx + 1

                    def update_position(element: ElementContent) -> None:
                        element.position += 1
                        for child in element.children:
                            update_position(child)

                    for element in elements[replace_el_pos:]:
                        update_position(element)

                    return elements[:replace_el_pos] + [h2_container] + elements[replace_el_pos:]

            except Exception as e:
                logger.exception(e)

        return elements

    @retry_element_processing
    @traceable_generate(
        tags=["INNER_CTA"],
    )
    async def create_inner_cta(self, element_content: ElementContent) -> ElementContent:
        logger.info(f"Cluster page {self.page_metadata.topic_name} creating INNER_CTA description")

        cta_response: CTASection = await self.ai.instructor_request(
            prompt=CommercialPagePrompt.CTA_SECTION_PROMPT_TEMPLATE.format(
                keyword=self.cluster_keyword,
                topic=self.page_metadata.topic_name,
                language=self.language,
                country=self.target_country,
            ),
            output_schema=CTASection,
        )

        if not cta_response:
            return element_content

        response: CTASection = cta_response.get_normalized(language=self.language)
        for c in element_content.children:
            if c.tag == Commercial1InnerCTATags.INNER_CTA_HEADING_TEXT:
                c.content = response.headline
                c.processed = True

                element_content.processed = True

                break

        return element_content
