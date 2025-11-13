import asyncio
import concurrent.futures
import copy
import random
import re
from asyncio import CancelledError
from typing import Generator

from langsmith import traceable
from loguru import logger
from pydantic import UUID4
from sentry_sdk import capture_exception

from app.core import settings
from app.enums import GenerationStatus, PageIntent, PageType, PBNEventEnum, PBNGenerationStatus, PBNPrompt
from app.enums.websocket import MoneySiteEventEnum
from app.models import Backlink
from app.schemas.backlink import BacklinkCreate
from app.schemas.cluster import ClusterCreate, ClusterSettingsRead
from app.schemas.elements.cluster_pages.base import ElementContent, StringElementOutput
from app.schemas.elements.cluster_pages.samples import InformationalPageElementsParams, page_elements_sample_mapper
from app.schemas.page.cluster_page import ClusterPageCreate, ClusterPageGeneratorResponse
from app.schemas.pbn import PBNBacklinkResponse, PBNClusterCreate, PBNGenerate
from app.services.ai.base import AIBase
from app.services.elements.cluster_pages.informational.hyperlinks import HyperlinkInjector
from app.services.generation.cluster.structure import ClusterStructureGenerator
from app.services.generation.cluster_pages.base import ClusterGeneratorBuilder, GeneratorT
from app.services.pbn import PBNService
from app.utils import UnitOfWorkNoPool, enqueue_global_message
from app.utils.convertors import text_normalize


class PBNClusterGenerator(ClusterGeneratorBuilder):
    def __init__(
        self,
        ai: AIBase,
        pbn_obj: PBNGenerate,
        total_plan_pages: int,
    ) -> None:
        super().__init__()
        self.pbn_obj = pbn_obj
        self.ai = ai
        self.total_plan_pages = total_plan_pages
        self.skip_elements = "COMMENT", "CONTACT"

    @traceable(tags=["PBN_CLUSTER_KEYWORD"])
    async def generate_pbn_cluster_keyword(self) -> str:
        response = await self.ai.gpt_request(
            prompt=PBNPrompt.PBN_CLUSTER_KEYWORD_GENERATION,
            output_schema=StringElementOutput,
            keyword=self.pbn_obj.keyword,
            language=self.pbn_obj.language,
            country=self.pbn_obj.target_country,
        )
        return response.data

    async def _process_head_content(self, element: ElementContent, result: ClusterPageGeneratorResponse) -> None:
        if element.tag != "HEAD_CONTENT" or not result.page_metadata.parent_topic:
            return

        async with UnitOfWorkNoPool() as uow:
            domain = await uow.domain_custom.get_one(pbn_id=result.page_metadata.pbn_id)

        result.page_metadata.parent_topic = f"{domain.name}/{text_normalize(result.page_metadata.parent_topic)}"

        async with HyperlinkInjector(page_metadata=result.page_metadata, language=self.pbn_obj.language) as service:
            context = "\n".join([el.content for el in element.children])

            if not context:
                return None

            keyword: str = service.page_metadata.parent_topic
            anchor: str = service.anchor.format(link=keyword, title=keyword)

            if sentence := await service._process_keyword(keyword=keyword, context=context, anchor=anchor):
                element.children[random.randint(0, len(element.children) - 1)].content += sentence

    async def _process_meta_backlink(self, element: ElementContent, result: ClusterPageGeneratorResponse) -> None:
        if element.tag != "META_BACKLINK":
            return

        async with UnitOfWorkNoPool() as uow:
            backlink: Backlink = await uow.backlink.get_by_page_type(
                page_type=PageType.CLUSTER, page_id=result.page_metadata.page_uuid
            )

            if not backlink:
                return

        response: PBNBacklinkResponse = await self.ai.gpt_request(
            prompt=PBNPrompt.BACKLINK_SENTENCE_GENERATION_PROMPT,
            output_schema=PBNBacklinkResponse,
            keyword=backlink.keyword,
        )

        element.content = re.sub(
            rf"({response.anchor})",
            f'<a href="{backlink.url}" {backlink.html_visibility}>{response.anchor}</a>',
            response.sentence,
        )

    async def _inject_links(self, result: ClusterPageGeneratorResponse) -> None:
        for el in result.release_content:
            await self._process_head_content(element=el, result=result)
            await self._process_meta_backlink(element=el, result=result)

    @staticmethod
    def distribute_pages(pages_number: int) -> list[int]:
        q, remain = divmod(pages_number, 30)
        clusters = [30] * q

        if remain > 0:
            clusters.append(remain)

        return clusters

    def setup_backlink(
        self, settings_obj: ClusterSettingsRead, pages: list[ClusterPageCreate]
    ) -> BacklinkCreate | None:
        """
        Setup backlink for the cluster

        Args:
            settings_obj: Cluster settings object
            pages: List of pages

        Returns:
            bool: Backlink applied
        """

        for el in settings_obj.elements_params:
            if el.type != "META_BACKLINK":
                continue

            for page in pages:
                if page.parent_id:
                    continue

                backlink_obj = BacklinkCreate.init(
                    keyword=self.pbn_obj.keyword,
                    url=self.pbn_obj.money_site_url,
                    pbn_id=self.pbn_obj.id,
                    page_id=page.id,
                    backlink_publish_period_option=self.pbn_obj.backlink_publish_period_option,  # type:ignore
                )
                el.enabled = True
                el.visible = backlink_obj.is_visible

                return backlink_obj

    async def setup_pbn_clusters(self) -> list[PBNClusterCreate]:
        clusters = []
        backlink_obj = None
        backlink_enabled = all(
            [self.pbn_obj.backlink_page == PageType.CLUSTER, self.pbn_obj.backlink_publish_period_option]
        )

        for pages_amount in self.distribute_pages(pages_number=self.pbn_obj.pages_number):
            async with ClusterStructureGenerator(
                user_id=self.pbn_obj.id,
                data=ClusterCreate(
                    keyword=await self.generate_pbn_cluster_keyword(),
                    language=self.pbn_obj.language,
                    target_country=self.pbn_obj.target_country,
                    max_pages=pages_amount,
                ),
            ) as service:
                industry_id = await service.define_industry(service.data.keyword, service.data.language)
                author_id = await service.define_author(
                    service.user_id, industry_id, service.data.keyword, service.data.language
                )

                async with UnitOfWorkNoPool() as uow:
                    author = await uow.author.get_one(id=author_id)

                pages = await service.generate_cluster_topics()
                settings: list[ClusterSettingsRead] = []

                for intent in service.detected_page_intents:
                    cluster_settings = page_elements_sample_mapper.get(intent, InformationalPageElementsParams)

                    settings_obj = ClusterSettingsRead(
                        cluster_id=service.cluster_id,
                        search_intent=intent,
                        general_style=cluster_settings.general_style_sample,  # type: ignore
                        elements_params=cluster_settings.elements_param_sample,  # type: ignore
                    )

                    if settings_obj.search_intent == PageIntent.INFORMATIONAL:
                        for el in settings_obj.elements_params:
                            if el.type.startswith(self.skip_elements):
                                el.enabled = False
                                el.visible = False

                    if all([backlink_enabled, not backlink_obj]):
                        backlink_obj = self.setup_backlink(settings_obj=settings_obj, pages=pages)

                    settings.append(settings_obj)

                cluster_generate_obj = PBNClusterCreate(
                    id=service.cluster_id,
                    pbn_id=self.pbn_obj.id,
                    keyword=service.data.keyword,
                    language=service.data.language,
                    target_country=service.data.target_country,
                    topics_number=len(pages),
                    status=GenerationStatus.GENERATING,
                    user_id=self.pbn_obj.user_id,
                    author=author,
                    pages=pages,
                    settings=settings,
                    backlink=backlink_obj,
                    industry_id=industry_id,
                )
                clusters.append(cluster_generate_obj)

        return clusters

    @staticmethod
    async def _generate(data: dict[GeneratorT, dict]) -> list[tuple[GeneratorT, list[ClusterPageGeneratorResponse]]]:
        results = []

        for generator, info in data.items():
            pages_results = []

            pages_metadata = info["pages_metadata"]
            content_structure = info["content_structure"]

            progress_per_page = 100 / max(len(pages_metadata), 1)

            for page_metadata in pages_metadata:
                content = await generator.create_page_content(
                    content_structure=copy.deepcopy(content_structure),
                    page_metadata=page_metadata,
                    progress_per_page=progress_per_page,
                    hyperlinks_injection=False,
                )

                if not content:
                    raise Exception  # TODO: replace with custom

                pages_results.append(content)

            results.append((generator, pages_results))

        return results

    @staticmethod
    def run_thread(data: dict[GeneratorT, dict]) -> list[tuple[GeneratorT, list[ClusterPageGeneratorResponse]]]:
        loop = asyncio.new_event_loop()

        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(PBNClusterGenerator._generate(data=data))

        except Exception as e:
            logger.error(f"Process was exited with {e}")
            capture_exception(e)
            raise e

        finally:
            pending_tasks = asyncio.all_tasks(loop)

            for task in pending_tasks:
                task.cancel()
                try:
                    loop.run_until_complete(task)
                except CancelledError:
                    pass

            loop.close()

    def _generate_pbn_clusters_pages(
        self, generators_data: list[tuple[UUID4, dict[GeneratorT, dict]]]
    ) -> Generator[tuple[UUID4, list[tuple[GeneratorT, list[ClusterPageGeneratorResponse]]]], None, None]:
        futures = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=settings.MAX_THREADS) as executor:
            for cluster_id, data in generators_data:
                future = executor.submit(self.run_thread, data)  # type:ignore
                futures.append((cluster_id, future))

        for cluster_id, future in futures:
            try:
                result = future.result()

                if not result:
                    raise Exception

                yield cluster_id, result

            except Exception as e:
                raise e

    async def generate(self, clusters: list[PBNClusterCreate]) -> None:
        generators_data = []
        generated_pages_counter = 0
        money_site_progress = 0

        for cluster in clusters:
            builder = await super()._init()
            await builder._set_generation_params(
                user_id=self.pbn_obj.user_id, user_email=self.pbn_obj.user_email, obj=cluster, pbn_id=self.pbn_obj.id
            )

            cluster_attrs = await builder._collect_generator_attrs()  # type: ignore
            generators_data.append((cluster.id, cluster_attrs))

        # TODO: Refactor this/simplify
        for cluster_id, response in self._generate_pbn_clusters_pages(generators_data=generators_data):  # type:ignore
            for generator, pages in response:
                for page in pages:
                    page = generator.filter_page_content_elements(page, dict(page_metadata=page.page_metadata))

                    await self._inject_links(page)

                    await generator.save_generated_page_content(response=page)

                    generated_pages_counter += 1

                    await enqueue_global_message(
                        event=PBNEventEnum.GENERATING,
                        user_id=self.pbn_obj.user_id,
                        pbn_id=self.pbn_obj.id,
                        progress=(generated_pages_counter / self.pbn_obj.pages_number) * 100,
                        message=f"Page {page.page_metadata.page_uuid} for pbn generated.",
                    )
                    money_site_progress = (generated_pages_counter / self.total_plan_pages) * 50

                    await enqueue_global_message(
                        event=MoneySiteEventEnum.GENERATING,
                        user_id=self.pbn_obj.user_id,
                        money_site_id=self.pbn_obj.money_site_id,
                        progress=money_site_progress,
                    )

            async with UnitOfWorkNoPool() as uow:
                cluster = await uow.cluster.get_one(id=cluster_id)
                cluster.status = GenerationStatus.GENERATED

        await PBNService.set_pbn_status(id_=self.pbn_obj.id, status=PBNGenerationStatus.GENERATED)

        await enqueue_global_message(event=PBNEventEnum.GENERATED, user_id=self.pbn_obj.user_id, pbn_id=self.pbn_obj.id)

        await PBNService.build_pbn_static(
            pbn_obj=self.pbn_obj,
            clusters=clusters,
            total_plan_pages=self.total_plan_pages,
            money_site_progress=money_site_progress,
        )
