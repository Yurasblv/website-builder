from typing import Any, Callable

from loguru import logger
from sentry_sdk import capture_exception

from app.enums import (
    ClusterEventEnum,
    InformationalContactTags,
    InformationalCTATags,
    InformationalElementType,
    PageIntent,
    SourceLinkMode,
)
from app.schemas.cluster.generation import PageGenerateRead
from app.schemas.elements import ElementContent
from app.schemas.page import ClusterPageGenerationMetadata, ClusterPageGeneratorResponse
from app.services.elements.cluster_pages.informational import InformationalPageElementService
from app.utils.message_queue import enqueue_global_message
from app.utils.use_types import ContentStructure

from .base import ClusterPagesGeneratorBase


class InformationalPageGenerator(ClusterPagesGeneratorBase):
    __page_intent__ = PageIntent.INFORMATIONAL

    def __init__(self, *args, **kwargs) -> None:  # type:ignore
        super().__init__(*args, **kwargs)

    async def create_page_element(
        self,
        element: str,
        element_service: InformationalPageElementService,
        element_content: ElementContent | list[ElementContent],
        progress_per_element: float,
    ) -> ElementContent | list[ElementContent]:
        if element == InformationalElementType.REFERENCES:
            return element_content

        switcher: dict[str, Callable] = {
            "TITLE": element_service.generate_title,
            "META_WORDS": element_service.generate_meta_words,
            "META_DESCRIPTION": element_service.generate_meta_description,
            "H1": element_service.generate_h1_header,
            "HEAD_CONTENT": element_service.create_head_content_tag,
            "QUIZ": element_service.create_quiz,
            "GRAPH": element_service.create_graph,
            "FAQ": element_service.create_faqs,
            "TABLE": element_service.create_table,
            "NEWS_BUBBLE": element_service.create_news_bubble,
            "FACTS": element_service.create_facts,
            "RELATED_PAGES": element_service.create_related_pages_element,
        }

        obj = switcher.get(element, element_service.process_element)

        try:
            element_content = await obj(element_content=element_content)

        except Exception as e:
            capture_exception(e)
            logger.exception(e)

        await enqueue_global_message(
            event=ClusterEventEnum.GENERATING,
            generation_key=self.generation_key,
            progress=progress_per_element,
            message=f"Element {element} generated",
        )

        return element_content

    async def create_pages_metadata(self, pages: list[PageGenerateRead]) -> list[ClusterPageGenerationMetadata]:
        """
        Creates environment schema for each cluster page(topic) with additional information
            about related pages(parent and children), intent, category and keywords.

        Args:
            pages: pages to build metadata

        Returns:
            dict with keys as pages identifiers and values as ClusterPageGenerationMetadata schema for each page(topic)
        """

        pages_metadata: list[ClusterPageGenerationMetadata] = []

        for page in pages:
            page_metadata = ClusterPageGenerationMetadata(
                pbn_id=self.pbn_id,
                cluster_id=self.cluster.id,
                text_info=page.text_info,
                page_uuid=page.id,
                reviews=page.reviews,
                topic_name=page.topic,
                keywords=page.keywords,
                search_intent=page.search_intent,
                topic_category=page.category,
                target_audience=self.cluster.target_audience,
                parent_url=page.parent_id,
                parent_topic=page.parent_topic,
                neighbours_urls=page.neighbours_ids,
                neighbours_topics=page.neighbours_topics,
                children_urls=page.children_ids,
                children_topics=page.children_topics,
                geolocation=getattr(self.settings, "geolocation", {}),
            )

            if main_source_link := self.settings.main_source_link:
                match main_source_link.mode:
                    case SourceLinkMode.ALL:
                        page_metadata.main_source_link = main_source_link

                    case SourceLinkMode.HEAD if not page.parent_id:
                        page_metadata.main_source_link = main_source_link

            pages_metadata.append(page_metadata)

        return pages_metadata

    async def set_content_structure(self) -> ContentStructure:
        """
        Configures element chain with assigning personal style preferences for each element separately.
        Compare positioned element with element in element_style_params,
         and if it is in both lists, style will be assigned to positioned element.

        Returns:
            content_structure dictionary with assigned styles for positioned elements,
            where key is name of the element and value is prepared content schema without data
        """
        cs: ContentStructure = {}

        for e_param in self.settings.elements_params:
            if not e_param.enabled:
                continue

            match e_param.type:
                case InformationalElementType.AUTHOR:
                    cs[e_param.type] = InformationalPageElementService.create_custom_author_element(
                        self.cluster.author, params=e_param
                    )

                case _:
                    cs[e_param.type] = ElementContent(
                        tag=e_param.type,
                        position=e_param.position,
                        classname=e_param.className,
                        style=e_param.style,
                        settings=e_param.settings,
                    )

        if CONTACT := cs.get(InformationalContactTags.CONTACTS):
            contact_children: list[ElementContent] = []

            for tag in InformationalContactTags.list():
                contact_e: ElementContent | None = cs.pop(tag, None)

                if contact_e:
                    contact_e.processed = True
                    contact_children.append(contact_e)

            if contact_children:
                CONTACT.processed = True
                CONTACT.children = contact_children

        if CTA := cs.get(InformationalCTATags.CTA):
            cta_children: list[ElementContent] = []

            for tag in InformationalCTATags.list():
                cta_e: ElementContent | None = cs.pop(tag, None)

                if cta_e:
                    cta_e.processed = True
                    cta_children.append(cta_e)

            if cta_children:
                CTA.processed = True
                CTA.children = cta_children
        return cs

    def filter_page_content_elements(
        self,
        page: ClusterPageGeneratorResponse | None,
        context: dict[str, Any],
    ) -> ClusterPageGeneratorResponse | None:
        def filter_explicit_content(content: list[ElementContent]) -> list[ElementContent]:
            filtered_content = []

            for i in content:
                if not i.processed:
                    continue

                filtered_content.append(i)
            return filtered_content

        page_context: ClusterPageGenerationMetadata = context["page_metadata"]

        if not page or not page.valid:
            self.generation_info.unprocessed_pages.add(page_context.page_uuid)
            return None

        page.sort_content()
        page.release_content = filter_explicit_content(page.release_content)
        page.original_content = filter_explicit_content(page.original_content)

        return page

    async def create_page_content(
        self,
        content_structure: ContentStructure,
        page_metadata: ClusterPageGenerationMetadata,
        progress_per_page: float,
        hyperlinks_injection: bool = True,
    ) -> ClusterPageGeneratorResponse:
        """
        Generates content for single page. All elements for page generate in semaphore asynchronously.

        Args:
            content_structure: dict with element names as keys and prepared ElementContent schema as value without data
            page_metadata: additional data for page content generation
            progress_per_page: percentage of content generation for one-page
            hyperlinks_injection

        Returns:
            filled with content page object
        """

        logger.info(f"Create content for cluster= {self.cluster.id}, topic= {page_metadata.topic_name}")

        progress_per_element = (progress_per_page * 0.05) / max(len(content_structure), 1)  # 5% of page generation

        async with InformationalPageElementService(
            user_email=self.user_email,
            language=self.cluster.language,
            target_country=self.cluster.target_country,
            page_metadata=page_metadata,
            cluster_keyword=self.cluster.keyword,
            generation_key=self.generation_key,
        ) as element_service:
            original_content: list[ElementContent] = []

            results = [
                await self.create_page_element(
                    element=element,
                    element_service=element_service,
                    element_content=element_content,
                    progress_per_element=progress_per_element,
                )
                for element, element_content in content_structure.items()
            ]

            for data in results:
                if isinstance(data, ElementContent):
                    original_content.append(data)

                if isinstance(data, list):
                    original_content.extend(data)

            original_content, h1_positions, h2_positions, summary = await element_service.create_h2_contents(
                elements=original_content, progress_per_element=progress_per_page * 0.75
            )
            original_content = await element_service.update_elements_by_context(original_content, summary)

            release_content = await element_service.page_content_post_process(
                content=original_content,
                h1_positions=h1_positions,
                h2_positions=h2_positions,
                progress_per_page=progress_per_page,
                reference_enabled=all([InformationalElementType.REFERENCES in content_structure and h2_positions]),
            )

        return ClusterPageGeneratorResponse(
            page_metadata=page_metadata, original_content=original_content, release_content=release_content
        )
