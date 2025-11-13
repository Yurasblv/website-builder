import asyncio
import concurrent.futures
import copy
from abc import ABC, abstractmethod
from asyncio import CancelledError
from typing import Any, Generator, Type, TypeVar

from loguru import logger
from pydantic import UUID4, BaseModel
from sentry_sdk import capture_exception

from app.core.config import settings
from app.core.exc import (
    ClusterAlreadyGeneratedException,
    ClusterIsGeneratingException,
    ClusterIsNotAllowToGenerateException,
    GenerateUndefinedErrorException,
    ScreenshotCreatorException,
)
from app.enums import (
    ClusterEventEnum,
    GenerationStatus,
    ObjectExtension,
    PageIntent,
    PageStatus,
    SpendType,
    TransactionStatus,
    WebsocketEventEnum,
)
from app.enums.project import ProjectType
from app.models import Cluster, PageCluster, TransactionSpend, UserInfo
from app.schemas.cluster import ClusterGenerateRead, ClusterGenerationInfo, ClusterSettingsRead
from app.schemas.cluster.generation import PageGenerateRead
from app.schemas.elements.cluster_pages import ElementContent
from app.schemas.page import ClusterPageGenerationMetadata, ClusterPageGeneratorResponse
from app.schemas.pbn import PBNClusterCreate
from app.services.calculation import CalculationService
from app.services.generation.base import GeneratorBase
from app.services.page.base import PageServiceBase
from app.services.storages import ovh_service
from app.services.transaction import TransactionSpendService
from app.utils import UnitOfWork, UnitOfWorkNoPool, enqueue_global_message
from app.utils.use_types import ContentStructure


class ClusterPagesGeneratorBase(ABC):
    __page_intent__ = PageIntent

    def __init__(
        self,
        user_id: UUID4,
        user_email: str,
        cluster: ClusterGenerateRead,
        settings: ClusterSettingsRead,
        generation_key: str,
        generation_info: ClusterGenerationInfo,
        pbn_id: UUID4 | None,
    ) -> None:
        self.user_id = user_id
        self.user_email = user_email
        self.cluster = cluster
        self.settings = settings
        self.generation_key = generation_key
        self.generation_info = generation_info
        self.pbn_id = pbn_id

    @abstractmethod
    async def create_page_element(self, *args: Any, **kwargs: Any) -> ElementContent | list[ElementContent]: ...

    @abstractmethod
    async def create_pages_metadata(self, *args: Any, **kwargs: Any) -> list[ClusterPageGenerationMetadata]: ...

    @abstractmethod
    async def set_content_structure(self) -> ContentStructure: ...

    @abstractmethod
    def filter_page_content_elements(self, *args: Any, **kwargs: Any) -> ClusterPageGeneratorResponse | None: ...

    @abstractmethod
    async def create_page_content(self, *args: Any, **kwargs: Any) -> ClusterPageGeneratorResponse: ...

    async def save_generated_page_content(self, response: ClusterPageGeneratorResponse) -> None:
        """
        Saves a generated page by uploading its content in JSON to OVH S3 storage

        Args:
            response: page data with generated data in content field

        """

        objects = {
            "original": PageServiceBase.jsonify_page_data(data=response.original_content),
            "release_v1": PageServiceBase.jsonify_page_data(data=response.release_content),
        }

        for postfix, data in objects.items():
            # ----------------------------------------- TODO: remove if statement after release
            if not settings.is_production and postfix == "release_v1":
                import json

                from app.enums.open_ai import banwords
                from app.utils.qa import process_ban_words

                ban_words = getattr(banwords, f"REPLACEMENTS_{self.cluster.language.name}")

                log_data = dict(
                    keyword=self.cluster.keyword,
                    topic_name=response.page_metadata.topic_name,
                    language=self.cluster.language,
                    ban_words=process_ban_words(
                        data=json.loads(data),
                        ban_words=list(ban_words.keys()),
                    ),
                )
                logger.info(f"Ban words info: {log_data}")
            else:
                logger.debug(f"Skipping ban words check for {postfix} in stage {settings.STAGE}")
            # ------------------------------------------

            object_name = ovh_service.construct_object_name(  # TODO: Replace with cluster_id/*
                user_email=self.user_email,
                cluster_id=response.page_metadata.cluster_id,
                extension=ObjectExtension.JSON,
                page_id=response.page_metadata.page_uuid,
                postfix=postfix,
            )

            if link := await ovh_service.save_file(data=data, object_name=object_name):
                objects[postfix] = link
                continue

            self.generation_info.unprocessed_pages.add(response.page_metadata.page_uuid)
            await ovh_service.delete_files_with_prefix(
                prefix=ovh_service.construct_object_name(  # TODO: Replace with cluster_id/*
                    user_email=self.user_email,
                    cluster_id=response.page_metadata.cluster_id,
                    page_id=response.page_metadata.page_uuid,
                )
            )

        async with UnitOfWorkNoPool() as uow:
            page: PageCluster = await uow.page_cluster.get_one(id=response.page_metadata.page_uuid)
            page.status = PageStatus.GENERATED

            page.releases.append(objects["release_v1"])
            page.original_content_file = objects["original"]

            if self.settings.general_style:
                page.general_style = self.settings.general_style.model_dump()

            if self.settings.reviews:
                page.reviews = {
                    "rating": self.settings.reviews.rating.random,
                    "count": self.settings.reviews.count.random,
                }


GeneratorT = TypeVar("GeneratorT", bound=ClusterPagesGeneratorBase)


class ClusterGeneratorBuilder(GeneratorBase):
    def __init__(self) -> None:
        super().__init__()

        self.cluster: ClusterGenerateRead = None
        self.pbn_id: UUID4 = None
        self.generation_key = "generating_cluster_{cluster_id}"

        self.generation_info = ClusterGenerationInfo()

    @staticmethod
    def run_generators(*args: Any, **kwargs: Any) -> dict[str, Any]:
        """
        Function for executing function with own parameters in own loop.

        Return:
            dict with result and kwargs for function executing

        Raises:
            Exception: if loop result had error
        """

        _generator = kwargs.pop("_generator")
        data = {"_generator": _generator, "result": None, "context": kwargs}
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(_generator.create_page_content(*args, **kwargs))
            data["result"] = result

        except Exception as e:
            logger.error(f"Process was exited with {e}")
            capture_exception(e)

        finally:
            pending_tasks = asyncio.all_tasks(loop)

            for task in pending_tasks:
                task.cancel()
                try:
                    loop.run_until_complete(task)
                except CancelledError:
                    pass

            loop.close()
            return data

    def _init_generator(
        self, intent: PageIntent, cluster_settings: ClusterSettingsRead
    ) -> Type[ClusterPagesGeneratorBase]:
        """
        Initialize generator class by intent.

        Args:
            intent: page intent
            cluster_settings: cluster settings

        Raises:
            ValueError: if generator not found for intent

        Returns:
            Generator class for specific intent
        """
        from .commerical import CommercialPageGenerator
        from .informational import InformationalPageGenerator
        from .navigational import NavigationalPageGenerator

        __page_intent_generator_mapper__ = {
            PageIntent.COMMERCIAL: CommercialPageGenerator,
            PageIntent.INFORMATIONAL: InformationalPageGenerator,
            PageIntent.NAVIGATIONAL: NavigationalPageGenerator,
            PageIntent.TRANSACTIONAL: None,
        }

        generator_class = __page_intent_generator_mapper__.get(intent)

        if generator_class is None:
            raise ValueError(f"No generator found for intent: {intent}")

        return generator_class(  # type: ignore
            user_id=self.user_id,
            user_email=self.user_email,
            pbn_id=self.pbn_id,
            cluster=ClusterGenerateRead.model_validate(self.cluster.model_dump(exclude={"pages", "settings"})),
            settings=cluster_settings,
            generation_key=self.generation_key,
            generation_info=self.generation_info,
        )

    async def _collect_generator_attrs(self, pages: list[PageGenerateRead] | None = None) -> dict[GeneratorT, dict]:
        generator_attrs_map = {}

        intent_page_map = self.sort_pages_by_intent(pages=pages)

        for intent, pages in intent_page_map.items():
            try:
                cluster_settings = self.cluster.settings[intent]

                generator: GeneratorT = self._init_generator(intent, cluster_settings)

                pages_metadata = await generator.create_pages_metadata(pages)
                content_structure = await generator.set_content_structure()

                generator_attrs_map[generator] = dict(
                    pages_metadata=pages_metadata, content_structure=content_structure
                )
            except Exception as e:
                logger.exception(e)
                capture_exception(e)

        return generator_attrs_map

    def sort_pages_by_intent(
        self, pages: list[PageGenerateRead] | None = None
    ) -> dict[PageIntent, list[PageGenerateRead]]:
        pages_generators_mapper = {}

        pages = pages or self.cluster.pages

        for page in pages:
            if page.search_intent not in pages_generators_mapper:
                pages_generators_mapper[page.search_intent] = [page]
            else:
                pages_generators_mapper[page.search_intent].append(page)
        return pages_generators_mapper

    @staticmethod
    async def _init() -> "ClusterGeneratorBuilder":
        self = ClusterGeneratorBuilder()
        await super(ClusterGeneratorBuilder, self)._init()
        return self

    @staticmethod
    def _to_cluster_read(obj: Cluster | PBNClusterCreate) -> ClusterGenerateRead:
        if isinstance(obj, BaseModel):
            return ClusterGenerateRead.model_validate(obj.model_dump())

        obj_dict = obj.__dict__
        obj_dict["settings"] = [setting.__dict__ for setting in obj_dict.get("settings", [])]
        obj_dict["pages"] = [page.__dict__ for page in obj_dict.get("pages", [])]
        return ClusterGenerateRead.model_validate(obj_dict)

    async def _set_generation_params(
        self, user_id: UUID4, user_email: str, obj: Cluster | PBNClusterCreate, pbn_id: UUID4 | None = None
    ) -> None:
        self.user_id = user_id
        self.user_email = user_email
        self.cluster = self._to_cluster_read(obj)
        self.generation_key = self.generation_key.format(cluster_id=obj.id)
        self.pbn_id = pbn_id

    async def charge_for_content_generation(self, unit_of_work: UnitOfWork, *, user_id: UUID4) -> None:
        pages_price = CalculationService.cluster_pages_generation(self.cluster.pages_number)

        transaction = await TransactionSpendService.create(
            unit_of_work,
            user_id=user_id,
            amount=pages_price,
            object_id=self.cluster.id,
            object_type=SpendType.CLUSTER_PAGES,
        )
        self.generation_info.pages_tx_id = transaction.id
        await unit_of_work.session.flush()

    async def run_unprocessed_pages(self, attrs: dict[GeneratorT, dict]) -> None:
        retry_attrs: dict[GeneratorT, dict] = {}

        for generator, data in attrs.items():
            generator.generation_info.clear()

            content_structure: ContentStructure = data["content_structure"]
            pages_metadata: dict[UUID4, ClusterPageGenerationMetadata] = {
                p.uuid: p for p in data.get("pages_metadata", [])
            }
            retry_metadata = []

            for page_id in self.generation_info.unprocessed_pages:
                if metadata := pages_metadata.get(page_id):
                    retry_metadata.append(metadata)

            if retry_metadata:
                retry_attrs[generator] = dict(pages_metadata=retry_metadata, content_structure=content_structure)

        self.generation_info.clear()

        for _generator, response in self._generate_pages_content(attrs=retry_attrs):
            await _generator.save_generated_page_content(response=response)

        for generator in retry_attrs.keys():
            self.generation_info.unprocessed_pages.update(generator.generation_info.unprocessed_pages)

    def _generate_pages_content(self, attrs: dict[GeneratorT, dict]) -> Generator[tuple, None, None]:
        """
        Generates content for a cluster's pages concurrently using threads.

        Args:
            attrs:
                generator: instance of generator
                pages_metadata: dict with pages identifiers as keys and environment schemas as value per page
                content_structure: dict with element names as keys and prepared ElementContent schema without data

        Yields:
            filled with content page object
        """
        task_attrs = []

        for generator, data in attrs.items():
            pages_metadata = data["pages_metadata"]
            content_structure = data["content_structure"]

            progress_per_page = 100 / max(len(pages_metadata), 1)

            for page_metadata in pages_metadata:
                task_attrs.append(
                    dict(
                        _generator=generator,
                        content_structure=copy.deepcopy(content_structure),
                        page_metadata=page_metadata,
                        progress_per_page=progress_per_page,
                    )
                )

        with concurrent.futures.ThreadPoolExecutor(max_workers=settings.MAX_THREADS) as executor:
            futures = [executor.submit(self.run_generators, **attr) for attr in task_attrs]

            for future in concurrent.futures.as_completed(futures):
                future_result = future.result()

                _generator: GeneratorT = future_result["_generator"]
                result = future_result["result"]
                context = future_result["context"]

                response = _generator.filter_page_content_elements(result, context)

                yield _generator, response

    async def generate(self, *args: Any, **kwargs: Any) -> None:
        logger.info(f"Start pages generation for cluster with id = {self.cluster.id} ...")

        try:
            attrs = await self._collect_generator_attrs()  # type: ignore

            for _generator, response in self._generate_pages_content(attrs=attrs):
                await _generator.save_generated_page_content(response=response)

            for generator in attrs.keys():
                self.generation_info.unprocessed_pages.update(generator.generation_info.unprocessed_pages)

            if self.generation_info.unprocessed_pages:
                await self.run_unprocessed_pages(attrs=attrs)

        except Exception as e:
            capture_exception(e)
            raise GenerateUndefinedErrorException(
                user_id=self.user_id,
                cluster_id=self.cluster.id,
                pages_number=self.cluster.topics_number,
            )

    async def prepare_for_generation(self, user_id: UUID4, user_email: str, cluster_id: UUID4) -> None:
        """Check if there is an ongoing generation."""
        try:
            async with UnitOfWorkNoPool() as uow:
                db_obj: Cluster = await uow.cluster.get_one(
                    join_load_list=[uow.cluster.author_load, uow.cluster.pages_load, uow.cluster.settings_load],
                    id=cluster_id,
                    user_id=user_id,
                    is_community=False,
                )

                cached_generation = await self.redis.hgetall(self.generation_key.format(cluster_id=cluster_id))

                if cached_generation and db_obj.status == GenerationStatus.GENERATING:
                    raise ClusterIsGeneratingException(user_id=user_id, cluster_id=cluster_id)

                await self.redis.delete(self.generation_key.format(cluster_id=cluster_id))

                if db_obj.status not in GenerationStatus.able_to_generate_statuses():
                    raise ClusterIsNotAllowToGenerateException(cluster_id=db_obj.id, status=db_obj.status)

                if not db_obj.pages:
                    raise ClusterAlreadyGeneratedException(cluster_id=db_obj.id)

                await self._set_generation_params(user_id=user_id, user_email=user_email, obj=db_obj)
                await self.charge_for_content_generation(uow, user_id=user_id)

        except Exception as e:
            raise e

        self.cluster.status = GenerationStatus.GENERATING

        await enqueue_global_message(
            event=ClusterEventEnum.STATUS_CHANGED,
            object_id=cluster_id,
            object_type="cluster",
            status=GenerationStatus.GENERATING,
            user_id=self.user_id,
        )

        await self.redis.hset(
            name=self.generation_key.format(cluster_id=cluster_id),
            mapping=dict(cluster_id=str(cluster_id), progress=0, user_id=str(user_id)),
        )

    async def refund_for_pages(self, tx: TransactionSpend, *, amount: int, user: UserInfo) -> None:
        broken_pages_refund = CalculationService.cluster_pages_generation(amount)

        if broken_pages_refund > tx.amount:
            broken_pages_refund = tx.amount

        if broken_pages_refund == tx.amount:
            tx.status = TransactionStatus.CANCELLED
            tx.info = "Refund for cluster generation."

        else:
            tx.status = TransactionStatus.COMPLETED
            tx.info = (
                f"Refund for broken cluster pages generation. Refund amount: {broken_pages_refund} for {amount} pages."
            )

        user.balance += broken_pages_refund

    async def finalize_generation(self, exception: Exception | None = None) -> None:
        """Update the database to reflect a completed generation."""
        from app.services.cluster.base import ClusterService

        status = GenerationStatus.GENERATION_FAILED if exception else GenerationStatus.GENERATED

        async with UnitOfWorkNoPool() as uow:
            cluster: Cluster = await uow.cluster.get_one(join_load_list=[uow.cluster.settings_load], id=self.cluster.id)
            project = await uow.project.get_one(id=cluster.project_id)
            user: UserInfo = await uow.user.get_one(id=self.user_id)
            pages_tx: TransactionSpend = await uow.transaction_spend.get_one(id=self.generation_info.pages_tx_id)

            cluster.status = status
            pages_tx.status = TransactionStatus.COMPLETED

            if draft_pages := await uow.page_cluster.get_count(status=PageStatus.DRAFT, cluster_id=self.cluster.id):
                await self.refund_for_pages(pages_tx, amount=draft_pages, user=user)
                await uow.session.flush()

            if not project.is_custom:
                project = await uow.project.get_or_create(type=ProjectType.CREATED, user_id=user.id)
                cluster.project_id = project.id

            # Check for cluster's condition to decide if snapshot can be applied.
            # Checks all cluster's settings at least for 1 related image and copy s3 url to db instance record.
            if status == GenerationStatus.GENERATED and any(
                el
                for setting in cluster.settings
                for el in setting.elements_params
                if "IMG" in el.get("type", "") and el.get("enabled", False)
            ):
                if ss := await ClusterService.create_snapshot(user_email=self.user_email, cluster_id=self.cluster.id):
                    cluster.snapshot = ss

                else:
                    e = ScreenshotCreatorException(
                        detail=f"No files found for snapshot creation. Cluster ID {self.cluster.id} "
                    )
                    capture_exception(e)

                    await enqueue_global_message(
                        event=WebsocketEventEnum.ERROR, user_id=self.user_id, msg=str(e), alias=e._exception_alias
                    )

        await enqueue_global_message(
            event=ClusterEventEnum.STATUS_CHANGED,
            object_id=self.cluster.id,
            object_type="cluster",
            status=status,
            user_id=self.user_id,
        )

        await self.redis.delete(self.generation_key)

        if exception:
            logger.error(f"Cluster {self.cluster.id} was not generated: {exception}.")
            raise exception

        logger.success(f"Cluster {self.cluster.id} was successfully generated.")
        await enqueue_global_message(
            event=ClusterEventEnum.GENERATED,
            user_id=str(user.id),
            cluster_id=self.cluster.id,
            keyword=self.cluster.keyword,
            message="Cluster generated successfully.",
        )

    async def _run_test_generation(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError

    async def run_dev_generation(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError
