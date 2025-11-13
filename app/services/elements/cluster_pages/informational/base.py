import copy
from typing import Any

from loguru import logger

from app.enums import ClusterEventEnum
from app.schemas.elements import ElementContent
from app.services.elements.cluster_pages.base import ElementServiceBase
from app.services.scraper import Scraper
from app.utils import enqueue_global_message

from .hyperlinks import HyperlinkInjector
from .reference import ReferencePageElementService


class InformationalPageElementService(ElementServiceBase):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.scraper = Scraper()
        self.context = ""

    async def __aenter__(self) -> "InformationalPageElementService":
        await super().__aenter__()

        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await super().__aexit__(exc_type, exc, tb)

    async def create_h2_contents(
        self, elements: list[ElementContent], progress_per_element: float
    ) -> tuple[list[ElementContent], list[int], list[int], str]:
        from .h2 import InformationalPageH2Service

        async with InformationalPageH2Service(
            user_email=self.user_email,
            language=self.language,
            target_country=self.target_country,
            page_metadata=self.page_metadata,
            cluster_keyword=self.cluster_keyword,
            ai=self.ai,
            chain_builder=self.chain_builder,
            generation_key=self.generation_key,
        ) as service:
            try:
                elements = await service.create_h2_contents(
                    elements=elements, progress_per_element=progress_per_element
                )
                self.context += service.context

            except Exception as e:
                logger.exception(e)

            return elements, service.h1_positions, service.h2_positions, service.context

    async def create_references_element(
        self,
        elements: list[ElementContent],
        h2_positions: list[int],
        ban_keywords: set[str],
        progress_per_element: float,
    ) -> None:
        async with ReferencePageElementService(
            user_email=self.user_email,
            ai=self.ai,
            scraper=self.scraper,
            page_metadata=self.page_metadata,
            language=self.language,
            target_country=self.target_country,
        ) as s:
            return await s.create_references_element(
                generation_key=self.generation_key,
                elements=elements,
                h2_positions=h2_positions,
                ban_keywords=ban_keywords,
                progress_per_element=progress_per_element,
            )

    async def inject_hyperlinks(
        self,
        elements: list[ElementContent],
        h1_positions: list[int],
        h2_positions: list[int],
        progress_per_page: float,
    ) -> tuple[list[ElementContent], set[str]]:
        async with HyperlinkInjector(page_metadata=self.page_metadata, ai=self.ai, language=self.language) as service:
            elements = await service.inject_hyperlinks(
                elements=elements, h1_positions=h1_positions, h2_positions=h2_positions
            )
            await enqueue_global_message(
                event=ClusterEventEnum.GENERATING,
                generation_key=self.generation_key,
                progress=progress_per_page,
                message="Hyperlinks injected",
            )
            return elements, service.ban_keywords

    async def page_content_post_process(
        self,
        content: list[ElementContent],
        h1_positions: list[int],
        h2_positions: list[int],
        progress_per_page: float,
        reference_enabled: bool = False,
    ) -> list[ElementContent]:
        """
        Post-processes the page content by injecting hyperlinks and creating references elements.

        Args:
            content: The page content to be processed.
            h1_positions: The positions of H1 elements.
            h2_positions: The positions of H2 elements.
            progress_per_page: The progress percentage for the page generation.
            reference_enabled

        Returns:
            A tuple containing the release content and a set of banned keywords.
        """

        release_content, ban_keywords = await self.inject_hyperlinks(
            elements=copy.deepcopy(content),
            h1_positions=h1_positions,
            h2_positions=h2_positions,
            progress_per_page=progress_per_page * 0.03,  # 83% of page generation
        )
        if reference_enabled:
            await self.create_references_element(
                elements=release_content,
                h2_positions=h2_positions,
                ban_keywords=ban_keywords,
                progress_per_element=progress_per_page * 0.17,  # 100% of page generation
            )

        return release_content
