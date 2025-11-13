import copy
from typing import Any, Callable

from loguru import logger
from sentry_sdk import capture_exception

from app.enums import ClusterEventEnum, NavigationalElementType, PageIntent
from app.schemas.cluster.generation import PageGenerateRead
from app.schemas.page.cluster_page import ClusterPageGenerationMetadata, ClusterPageGeneratorResponse, ElementContent
from app.services.elements.cluster_pages.navigational import NavigationalPageElementService
from app.utils.message_queue import enqueue_global_message
from app.utils.use_types import ContentStructure

from .base import ClusterPagesGeneratorBase


class NavigationalPageGenerator(ClusterPagesGeneratorBase):
    __page_intent__ = PageIntent.NAVIGATIONAL

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    async def create_page_element(
        self,
        element: str,
        element_service: NavigationalPageElementService,
        element_content: ElementContent | list[ElementContent],
        progress_per_element: float,
    ) -> ElementContent | list[ElementContent]:
        if element == NavigationalElementType.REFERENCES:
            return element_content

        switcher: dict[str, Callable] = {
            "TITLE": element_service.generate_title,
            "META_WORDS": element_service.generate_meta_words,
            "META_DESCRIPTION": element_service.generate_meta_description,
            "H1": element_service.generate_h1_header,
            "HEAD_CONTENT": element_service.create_head_content_tag,
            "TABLE_FIRST": element_service.create_table,
            "TABLE_SECOND": element_service.create_table,
            "NEWS_BUBBLE": element_service.create_news_bubble,
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
        return [
            ClusterPageGenerationMetadata(
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
            for page in pages
        ]

    async def set_content_structure(self) -> ContentStructure:  # type:ignore
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
                case NavigationalElementType.AUTHOR:
                    cs[e_param.type] = NavigationalPageElementService.create_custom_author_element(
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

        return cs

    def filter_page_content_elements(
        self,
        page: ClusterPageGeneratorResponse | None,
        context: dict[str, Any],
    ) -> ClusterPageGeneratorResponse | None:
        page_context: ClusterPageGenerationMetadata = context["page_metadata"]

        if not page or not page.valid:
            self.generation_info.unprocessed_pages.add(page_context.page_uuid)
            return None

        page.filter_processed()
        page.sort_content()

        return page

    async def create_page_content(
        self,
        content_structure: ContentStructure,
        page_metadata: ClusterPageGenerationMetadata,
        progress_per_page: float,
        **kwargs: Any,
    ) -> ClusterPageGeneratorResponse:
        """
        Generates content for single page. All elements for page generate in semaphore asynchronously.

        Args:
            content_structure: dict with element names as keys and prepared ElementContent schema as value without data
            page_metadata: additional data for page content generation
            progress_per_page: percentage of content generation for one-page

        Returns:
            filled with content page object
        """
        logger.info(f"Create content for cluster= {self.cluster.id}, topic= {page_metadata.topic_name}")
        progress_per_element = (progress_per_page * 0.05) / max(len(content_structure), 1)  # 5% of page generation

        async with NavigationalPageElementService(
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

            original_content = await element_service.create_h2_contents(elements=original_content)
            original_content = await element_service.update_elements_by_context(
                original_content, element_service.context
            )

            release_content = (
                await element_service.create_references_element(
                    elements=copy.deepcopy(original_content),
                    progress_per_element=progress_per_page * 0.17,
                )
                if content_structure.get(NavigationalElementType.REFERENCES)
                else original_content
            )

        return ClusterPageGeneratorResponse(
            page_metadata=page_metadata, original_content=original_content, release_content=release_content
        )
