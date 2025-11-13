import copy
import pickle
import random
from datetime import datetime
from typing import Any, Callable, Sequence
from uuid import uuid4

from loguru import logger
from pydantic import UUID4
from sentry_sdk import capture_exception

from app.core import settings
from app.core.exc import (
    IndustryNotFoundException,
    PBNExtraPageGenerationException,
    PBNExtraPageIsNotAllowToGenerateException,
)
from app.enums import (
    Country,
    FormattingPrompts,
    GenerationStatus,
    InformationalElementType,
    Language,
    ObjectExtension,
    PageStatus,
    PBNExtraPageEventEnum,
    PBNGenerationStatus,
    SpendType,
    StructurePrompts,
    TransactionStatus,
    WPPageType,
)
from app.models import PBN, PagePBNExtra, UserInfo
from app.schemas.author import AuthorElementContent
from app.schemas.elements.cluster_pages.base import CaseCheck, ElementContent, StringElementOutput, UUIDElementOutput
from app.schemas.elements.cluster_pages.samples import InformationalPageElementsParams
from app.schemas.integrations.wordpress import (
    IntegrationWordPressUpload,
    IntegrationWordPressUploadByChunks,
)
from app.schemas.page.pbn_page import PBNExtraPageCreate, PBNExtraPageGenerationMetadata, PBNExtraPageGeneratorResponse
from app.schemas.user_info import UserInfoRead
from app.services.ai.base import AIBase
from app.services.calculation import CalculationService
from app.services.cluster.static import PageStaticBuilder
from app.services.elements.cluster_pages.informational import InformationalPageElementService
from app.services.generation.base import GeneratorBase
from app.services.integrations.wordpress import IntegrationWordPressService
from app.services.page.page_pbn_extra import PBNExtraPageService
from app.services.pbn import PBNService
from app.services.storages import ovh_service
from app.services.transaction import TransactionSpendService
from app.utils import UnitOfWork, UnitOfWorkNoPool, enqueue_global_message
from app.utils.use_types import ContentStructure


class PBNExtraPageGenerator(PBNExtraPageService, GeneratorBase):
    def __init__(self) -> None:
        super().__init__()

        self.obj: PBNExtraPageGenerationMetadata = None
        self.tx_id: UUID4 = None
        self.wp_service: IntegrationWordPressService = IntegrationWordPressService()

        self.general_style = InformationalPageElementsParams.general_style_sample
        self.elements_params = InformationalPageElementsParams.elements_param_sample
        self.skip_elements = ("COMMENT", "CONTACT")

        self.object_key = "request_extra_pbn_page_generate_{pbn_id}"

    @staticmethod
    async def _init() -> "PBNExtraPageGenerator":
        self = PBNExtraPageGenerator()
        await super(PBNExtraPageGenerator, self)._init()
        return self

    @staticmethod
    async def define_author(
        uow: UnitOfWork, *, keyword: str, language: Language, user_id: UUID4
    ) -> AuthorElementContent:
        ai = AIBase()

        industries = await uow.industry.get_multi()
        available_industries = {k: v.get_for_language(language) for k, v in industries.items()}

        response = await ai.instructor_request(
            prompt=StructurePrompts.INDUSTRY_DEFINITION_TEMPLATE.format(
                industries=available_industries,
                keyword=keyword,
            ),
            assistant=StructurePrompts.INDUSTRY_DEFINITION_ASSISTANT,
            output_schema=UUIDElementOutput,
        )
        industry_id = response.data

        if str(response.data) not in available_industries:
            raise IndustryNotFoundException(industry=industry_id, industries=available_industries)

        authors = await uow.author.get_all(industry_id=industry_id, created_by_id=user_id)

        return AuthorElementContent.model_validate(random.choice(authors))

    @staticmethod
    async def generate_main_title(keyword: str, language: Language, country: Country) -> str:
        title = ""

        async with AIBase() as ai:
            response = await ai.gpt_request(
                prompt=StructurePrompts.PAGE_NAME_GENERATION_TEMPLATE,
                assistant=StructurePrompts.PAGE_NAME_GENERATION_ASSISTANT,
                output_schema=StringElementOutput,
                topic=keyword,
                language=language,
                country=country,
                current_date=datetime.now().strftime("%Y-%m"),
            )
            if not response:
                return title

            assistant = getattr(FormattingPrompts, f"CASE_CHECK_STRING_ASSISTANT_{language.name}")
            text_case: CaseCheck = await ai.instructor_request(
                prompt=FormattingPrompts.SENTENCE_CASE_CHECK_STRING.format(text=response.data),
                output_schema=CaseCheck,
                assistant=assistant,
                system="You are a helpful assistant responsible "
                "for verifying that the input text is correctly formatted. \
                    The only acceptable formatting style is sentence case. \
                    Ensure the entire text strictly adheres to sentence case throughout.",
            )

            if not text_case.correct_case:
                output = await ai.instructor_request(
                    prompt=FormattingPrompts.REPLACE_CAMEL_CASE_TEMPLATE.format(
                        content=response.data, language=language
                    ),
                    assistant=FormattingPrompts.REPLACE_CAMEL_CASE_ASSISTANT,
                    system=settings.ai.OPENAI_FORMATTING_ROLE,
                    output_schema=StringElementOutput,
                )
                if output:
                    title = output.data

        return title

    async def create_page_element(
        self,
        element: str,
        element_service: InformationalPageElementService,
        element_content: ElementContent | list[ElementContent],
        progress_per_element: float,
    ) -> ElementContent | list[ElementContent]:
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

        if element == InformationalElementType.REFERENCES:
            return element_content

        try:
            element_content = await obj(element_content=element_content)

        except Exception as e:
            capture_exception(e)
            logger.exception(e)

        await enqueue_global_message(
            event=PBNExtraPageEventEnum.GENERATING,
            generation_key=self.object_key,
            progress=progress_per_element,
            message=f"Element {element} generated",
        )

        return element_content

    async def create_page_content(
        self,
        content_structure: ContentStructure,
    ) -> PBNExtraPageGeneratorResponse:
        """
        Generates content for single page. All elements for page generate in semaphore asynchronously.

        Args:
            content_structure: dict with element names as keys and prepared ElementContent schema as value without data

        Returns:
            filled with content page object
        """
        logger.info(f"Create extra page content for pbn = {self.obj.pbn_id}, topic= {self.obj.topic_name}")

        progress_per_element = 100 / max(len(content_structure), 1)

        async with InformationalPageElementService(
            user_email=self.obj.user_email,
            language=self.obj.language,
            target_country=self.obj.target_country,
            page_metadata=self.obj,
            cluster_keyword=self.obj.keyword,
            generation_key=self.object_key,
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
                elements=original_content, progress_per_element=progress_per_element * 0.75
            )

            original_content = await element_service.update_elements_by_context(original_content, summary)
            release_content, ban_keywords = await element_service.inject_hyperlinks(
                elements=copy.deepcopy(original_content),
                h1_positions=h1_positions,
                h2_positions=h2_positions,
                progress_per_page=progress_per_element,
            )
            if h2_positions:
                await element_service.create_references_element(
                    elements=release_content,
                    h2_positions=h2_positions,
                    ban_keywords=ban_keywords,
                    progress_per_element=progress_per_element * 0.17,  # 100% of page generation
                )

        return PBNExtraPageGeneratorResponse(original_content=original_content, release_content=release_content)

    async def _set_generation_params(self, tx_id: UUID4, obj: PBNExtraPageGenerationMetadata) -> None:
        self.tx_id = tx_id
        self.obj = obj
        self.object_key = self.object_key.format(pbn_id=obj.pbn_id)

        await self.redis.hset(
            name=self.object_key,
            mapping=dict(user_id=str(obj.user_id), pbn_id=str(obj.pbn_id), page_id=str(obj.page_uuid), progress=0),
        )

    async def set_content_structure(self) -> ContentStructure:
        cs: ContentStructure = {}

        for e_param in self.elements_params:
            if not e_param.enabled:
                continue

            match e_param.type:
                case InformationalElementType.AUTHOR:
                    cs[e_param.type] = InformationalPageElementService.create_custom_author_element(
                        self.obj.author, params=e_param
                    )

                case _:
                    if e_param.type.startswith(self.skip_elements):
                        continue

                    cs[e_param.type] = ElementContent(
                        tag=e_param.type,
                        position=e_param.position,
                        classname=e_param.className,
                        style=e_param.style,
                        settings=e_param.settings,
                    )

        return cs

    async def charge_for_content_generation(self, unit_of_work: UnitOfWork) -> UUID4:
        pages_price = CalculationService.cluster_pages_generation(pages_number=1)

        transaction = await TransactionSpendService().create(
            unit_of_work,
            user_id=self.obj.user_id,
            amount=pages_price,
            object_id=self.obj.pbn_id,
            object_type=SpendType.EXTRA_PBN_PAGE,
        )
        self.obj.tx_id = transaction.id

        await unit_of_work.session.flush()
        return transaction.id

    async def save_generated_page_content(self, response: PBNExtraPageGeneratorResponse) -> None:
        """
        Saves a generated page by uploading its content in JSON to S3 storage

        Args:
            response: page data with generated data in content field

        Returns:
            S3 file name for a saved JSON object
        """

        objects = {
            "original": self.jsonify_page_data(data=response.original_content),
            "release_v1": self.jsonify_page_data(data=response.release_content),
        }

        for postfix, data in objects.items():
            object_name = ovh_service.construct_object_name(
                user_email=self.obj.user_email,
                pbn_id=self.obj.pbn_id,
                extension=ObjectExtension.JSON,
                page_id=self.obj.page_uuid,
                postfix=postfix,
            )
            json_link = await ovh_service.save_file(data=data, object_name=object_name)

            if not json_link:
                await ovh_service.delete_files_with_prefix(
                    prefix=ovh_service.construct_object_name(
                        user_email=self.obj.user_email,
                        pbn_id=self.obj.pbn_id,
                        page_id=self.obj.page_uuid,
                    )
                )
                raise PBNExtraPageGenerationException(
                    user_id=self.obj.user_id, pbn_id=self.obj.pbn_id, info="File with extra page was not saved."
                )

            objects[postfix] = json_link

        async with UnitOfWorkNoPool() as uow:
            page = await uow.page_pbn_extra.get_one(id=self.obj.page_uuid)
            page.original_content_file = objects["original"]
            page.releases.append(objects["release_v1"])

            page.status = GenerationStatus.GENERATED

    def filter_page_content_elements(self, page: PBNExtraPageGeneratorResponse) -> PBNExtraPageGeneratorResponse:
        if not page.valid:
            raise PBNExtraPageGenerationException(
                user_id=self.obj.user_id, pbn_id=self.obj.pbn_id, info="Not found generated content."
            )

        page.filter_processed()
        page.sort_content()

        return page

    async def _generate(self) -> None:
        await PBNService.set_pbn_status(id_=self.obj.pbn_id, status=PBNGenerationStatus.EXTRA_PAGE_GENERATING)

        content_structure = await self.set_content_structure()
        page = await self.create_page_content(content_structure=content_structure)

        response = self.filter_page_content_elements(page=page)
        await self.save_generated_page_content(response=response)

        await PBNService.set_pbn_status(id_=self.obj.pbn_id, status=PBNGenerationStatus.GENERATED)

    async def _build(self) -> str:
        await PBNService.set_pbn_status(id_=self.obj.pbn_id, status=PBNGenerationStatus.EXTRA_PAGE_BUILDING)

        builder = PageStaticBuilder(
            cluster_id=str(self.obj.cluster_id),
            user_id=str(self.obj.user_id),
            page_id=str(self.obj.page_uuid),
            page_style=self.general_style,
            pbn_id=str(self.obj.pbn_id),
        )
        built_version = await builder.build()

        async with UnitOfWorkNoPool() as uow:
            db_page: PagePBNExtra = await uow.page_pbn_extra.get_one(id=self.obj.page_uuid)
            db_page.zip_file = built_version

        await PBNService.set_pbn_status(id_=self.obj.pbn_id, status=PBNGenerationStatus.BUILT)

        return built_version

    async def _deploy(self, built_version: str) -> None:
        await PBNService.set_pbn_status(id_=self.obj.pbn_id, status=PBNGenerationStatus.EXTRA_PAGE_DEPLOYING)
        await enqueue_global_message(
            event=PBNExtraPageEventEnum.DEPLOYING,
            user_id=self.obj.user_id,
            pbn_id=self.obj.pbn_id,
            page_id=self.obj.page_uuid,
        )

        await self.wp_service._chunk_uploading(
            chunk_data=IntegrationWordPressUploadByChunks(
                domain=self.obj.domain,
                api_key=self.obj.wp_token,
                keyword=self.obj.keyword,
                data=IntegrationWordPressUpload(type=WPPageType.ARTICLE),
                cluster_id=str(self.obj.cluster_id),
                user_id=str(self.obj.user_id),
                file_bytes=await ovh_service.get_file_by_name(file_name=built_version),
            )
        )

        await PBNService.set_pbn_status(id_=self.obj.pbn_id, status=PBNGenerationStatus.DEPLOYED)

    async def generate(self) -> None:
        logger.info(f"Start extra page generation for pbn = {self.obj.pbn_id} ...")

        try:
            await self._generate()
            built_version = await self._build()
            await self._deploy(built_version=built_version)

        except Exception as e:
            raise PBNExtraPageGenerationException(
                user_id=self.obj.user_id,
                pbn_id=self.obj.pbn_id,
                info=str(e),
            )

    async def prepare_for_generation(self, user: UserInfoRead, pbn_id: UUID4) -> Any:
        async with UnitOfWorkNoPool() as uow:
            db_obj: PBN = await uow.pbn.get_one(
                join_load_list=[uow.pbn.money_site_load, uow.pbn.server_load], user_id=user.id, id=pbn_id
            )

            if not db_obj.server:
                raise PBNExtraPageGenerationException(user_id=user.id, pbn_id=db_obj.id, info="PBN server not found.")

            moneysite_keyword = db_obj.money_site.keyword
            domain = f"http://{db_obj.server.public_net_ipv4}:{db_obj.wp_port}/"

        topic_name = await self.generate_main_title(
            keyword=moneysite_keyword, language=db_obj.language, country=db_obj.target_country
        )
        author = await self.define_author(uow, keyword=moneysite_keyword, language=db_obj.language, user_id=user.id)

        metadata = PBNExtraPageGenerationMetadata(
            domain=domain,
            wp_token=db_obj.wp_token,
            user_id=user.id,
            user_balance=user.balance,
            user_email=user.email,
            cluster_id=uuid4(),
            keyword=db_obj.money_site.keyword,
            topic_name=topic_name,
            author=author,
            pbn_id=pbn_id,
            language=db_obj.language,
            target_country=db_obj.target_country,
        )

        async with UnitOfWorkNoPool() as uow:
            tx = await TransactionSpendService.create(
                uow,
                user_id=user.id,
                amount=settings.PAGE_REFRESH_PRICE * 1,
                object_id=pbn_id,
                object_type=SpendType.EXTRA_PBN_PAGE,
            )
            obj_in = PBNExtraPageCreate(
                id=metadata.page_uuid, pbn_id=metadata.pbn_id, status=PageStatus.GENERATING
            ).model_dump(exclude={"backlink"})
            obj_in["topic"] = metadata.topic_name
            await uow.page_pbn_extra.create(obj_in=obj_in)

        await enqueue_global_message(
            event=PBNExtraPageEventEnum.CREATED,
            user_id=user.id,
            pbn_id=pbn_id,
            page_id=metadata.page_uuid,
        )
        await self._set_generation_params(tx_id=tx.id, obj=metadata)

    @staticmethod
    async def validate_request(user_id: UUID4, *, pbn_ids: list[UUID4]) -> list[UUID4]:
        """Check if there is an ongoing generation."""
        async with UnitOfWorkNoPool() as uow:
            db_objs: Sequence[PBN] = await uow.pbn.get_all(id__in=pbn_ids, user_id=user_id)

        for pbn in db_objs:
            if pbn.status != PBNGenerationStatus.DEPLOYED:
                raise PBNExtraPageIsNotAllowToGenerateException(pbn_id=pbn.id, status=pbn.status)

        return pbn_ids

    async def rollback_changes(self) -> None:
        """Update the database to reflect a completed generation."""

        await self.redis.delete(self.object_key)

        async with UnitOfWorkNoPool() as uow:
            user: UserInfo = await uow.user.get_one(id=self.obj.user_id)
            pbn: PBN = await uow.pbn.get_one(id=self.obj.pbn_id)

            if self.obj:
                await uow.page.delete(id=self.obj.page_uuid)

            if transaction := await uow.transaction_spend.get_one_or_none(id=self.tx_id):
                user.balance += transaction.amount
                pbn.status = PBNGenerationStatus.DEPLOYED
                transaction.status = TransactionStatus.CANCELLED

    async def finalize_generation(self) -> None:
        """Update the database to reflect a completed generation."""

        await self.redis.delete(self.object_key)

        async with UnitOfWorkNoPool() as uow:
            pbn = await uow.pbn.get_one(id=self.obj.pbn_id)
            pbn.pages_number += 1

        logger.success(f"Extra page generated and deployed. PBN ID = {self.obj.pbn_id}")

    async def _run_test_generation(self, user: UserInfoRead, pbn_ids: list[UUID4]) -> None:
        raise NotImplementedError

    async def run_dev_generation(self, user: UserInfoRead, pbn_ids: list[UUID4]) -> None:
        """
        Generates an extra page for specified pbn using keyword in the background.

        Args:
            user: current user
            pbn_ids: pbns IDs list

        Returns:
            The place in the queue, -1 if the test mode is enabled
        """

        from app.celery.tasks.pbns.extra_page import pbn_extra_page_generate_task

        for pbn_id in pbn_ids:
            pbn_extra_page_generate_task.apply_async(
                kwargs=dict(user_info_bytes=pickle.dumps(user), pbn_id_bytes=pickle.dumps(pbn_id)), queue="pbn"
            )
