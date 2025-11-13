import json
import pickle

from loguru import logger
from pydantic import UUID4

from app.core.config import settings
from app.enums import GenerationStatus, ObjectExtension, SpendType
from app.schemas.cluster.base import ClusterCreateData
from app.services.page import ClusterPageService
from app.services.storages import ovh_service
from app.services.transaction import TransactionSpendService
from app.utils import ABCUnitOfWork, UnitOfWork, text_normalize


class ClusterService:
    @staticmethod
    async def create_snapshot(user_email: str, cluster_id: UUID4) -> str | None:
        """
        Creates a snapshot for the cluster from the first page.

        Args:
            cluster_id: cluster identifier
            user_email: customer's email

        Raises:
            ScreenshotCreatorException: if no files found for snapshot creation

        """

        logger.debug(f"Creating screenshots for {cluster_id=}")

        prefix = ovh_service.construct_object_name(user_email=user_email, cluster_id=cluster_id)
        return await ovh_service.get_first(prefix=prefix, suffix=ObjectExtension.WEBP)

    @classmethod
    def process_elements(cls, elements: list, imgs: dict, path: str, children: bool = None) -> dict:
        images = {}
        pattern = f"{path}_{{tag}}_{{content_id}}.webp" if children else f"{path}_{{tag}}.webp"

        for element in elements:
            if element.get("tag") == "GRID":
                images.update(cls.process_elements(element.get("children", []), imgs, path, children=True))

            if not (href := element.get("href")):
                continue

            logger.debug(f"Processing href: {href}")
            content_id = href.split("_")[-1]

            if content_id in imgs:
                logger.debug(f"Found image for content_id: {content_id}")
                filename = pattern.format(tag=element.get("tag").lower(), content_id=element.get("content_id"))
                images[filename] = imgs[content_id]

        logger.debug(f"Processed {len(images)} images for path: {path}")
        return images

    @classmethod
    async def get_static_cluster_files(
        cls, cluster_id: UUID4 | str, user_id: UUID4 | str
    ) -> tuple[str, dict, dict, bytes | None]:
        """
        Get the zip file for a cluster.

        Args:
            cluster_id: cluster identifier
            user_id: current user identifier

        Returns:
            StreamingResponse: response with the zip file
        """

        unit_of_work = getattr(cls, "unit_of_work", UnitOfWork)

        async with unit_of_work() as uow:
            user = await uow.user.get_one(id=user_id)
            cluster = await uow.cluster.get_one(
                id=cluster_id,
                user_id=user.id,
                status__in=GenerationStatus.generated_statuses(),
                join_load_list=[uow.cluster.author_load, uow.cluster.pages_load],
            )
            cluster_language = cluster.language
            cluster_author_avatar = cluster.author.avatar
            pages_db = cluster.pages

        # Create a mapping of page IDs to topic paths
        page_paths = {str(p.id): p.topic_path for p in pages_db}
        # TODO: Replace with cluster_id/*
        prefix = ovh_service.construct_object_name(user_email=user.email, cluster_id=cluster_id)

        pages = {
            p.topic_path: await ClusterPageService.convert_cluster_page_common(
                cluster_language, p, children=False, content=False
            )
            for p in pages_db
        }

        # Fetch file names with the specified prefix
        files_names = await ovh_service.get_files_with_prefix(prefix=prefix)
        extensions = (".json", ".webp")
        files = {file for file in files_names if file.endswith(extensions) and not file.endswith("original.json")}
        extra_files_names = await ovh_service.get_files_with_prefix(prefix=str(cluster_id))
        extra_files = {file for file in extra_files_names if file.endswith(extensions)}

        # Fetch content of the files
        files_bytes = await ovh_service.get_files(*files)
        extra_files_bytes = await ovh_service.get_files(*extra_files)

        author_avatar = None

        if avatar_link := cluster_author_avatar:
            author_avatar = await ovh_service.get_file_by_name(avatar_link, bucket=settings.storage.authors)

        # PROCESS FILES
        images_set: dict[str, dict] = {}
        logger.debug(f"Processing {len(files_bytes)} files")

        for file_dict in files_bytes:
            key, value = file_dict.popitem()
            try:
                parts = key.split("_")
                page_id, content_id = parts[2], parts[3]
                path = page_paths.get(page_id, key)

                if key.endswith(".json"):
                    pages[path].content = json.loads(value.decode("utf-8")) if value else None
                else:
                    images_set.setdefault(path, {})[content_id] = value

            except (IndexError, KeyError):
                logger.warning(f"Could not process file with key: {key}")
        # END OF FILE PROCESSING

        # PROCESS JSON FILES
        images = {}
        for path, page in pages.items():
            if not page.content:
                logger.warning(f"Empty JSON content for {path}")
                continue

            try:
                imgs = images_set.get(path, {})
                logger.debug(f"Processing JSON file: {path} with {len(imgs)} images")

                images.update(cls.process_elements(page.content, imgs, path))

            except (json.JSONDecodeError, IndexError, KeyError) as e:
                logger.error(f"Error processing JSON {path}: {e}")
        logger.debug(f"Processed {len(images)} images")
        for extra_image in extra_files_bytes:
            key, value = extra_image.popitem()
            key = key.removeprefix(str(cluster_id))[1:]  # handle - and /
            images[key] = value
        # END OF JSON PROCESSING

        return text_normalize(cluster.keyword), pages, images, author_avatar

    @staticmethod
    async def upgrade_current_version(unit_of_work: ABCUnitOfWork, *, cluster_id: UUID4) -> None:
        """
        Upgrades the current version of the cluster.

        Args:
            unit_of_work: The unit of work instance for database transactions.
            cluster_id: The unique identifier of the cluster to be upgraded.
        """

        from app.celery.tasks.clusters import (
            cluster_refreshing_failure_task,
            cluster_refreshing_success_task,
            cluster_refreshing_task,
        )

        async with unit_of_work as uow:
            cluster = await unit_of_work.cluster.get_one(
                join_load_list=[uow.cluster.pages_load, uow.cluster.user_load],
                id=cluster_id,
            )

            transaction = await TransactionSpendService.create(
                uow,
                user_id=cluster.user_id,
                amount=settings.PAGE_REFRESH_PRICE * len(cluster.pages),
                object_id=cluster.id,
                object_type=SpendType.REFRESH_CLUSTER_PAGE,
            )

        kwargs = dict(
            user_id=str(cluster.user.id),
            user_email=str(cluster.user.email),
            cluster_id=str(cluster_id),
            transaction_id=str(transaction.id),
            keyword=str(cluster.keyword),
        )
        success_link = cluster_refreshing_success_task.s(**kwargs)
        failure_link = cluster_refreshing_failure_task.s(**kwargs)
        cluster_refreshing_task.apply_async(kwargs=kwargs, link=success_link, link_error=failure_link, queue="clusters")

    @staticmethod
    async def building(unit_of_work: ABCUnitOfWork, *, cluster_id: UUID4) -> None:
        """
        Build the cluster.

        Args:
            unit_of_work
            cluster_id: The unique identifier of the cluster to be built.
        """

        from app.celery.tasks.clusters import cluster_building_task

        async with unit_of_work:
            cluster = await unit_of_work.cluster.get_one(id=cluster_id)

        cluster_building_task.apply_async(
            kwargs=dict(
                user_id=str(cluster.user_id),
                cluster_id=str(cluster.id),
            ),
            queue="clusters",
        )

    @staticmethod
    async def generate(unit_of_work: ABCUnitOfWork, *, cluster_id: UUID4) -> None:
        """
        Generate the cluster.

        Args:
            unit_of_work
            cluster_id: The unique identifier of the cluster to be built.
        """

        from app.celery.tasks.clusters import cluster_generation_task

        async with unit_of_work:
            cluster = await unit_of_work.cluster.get_one(id=cluster_id)
            user = await unit_of_work.user.get_one(id=cluster.user_id)

        cluster_generation_task.apply_async(
            kwargs=dict(
                user_id=str(cluster.user_id),
                user_email=str(user.email),
                cluster_id=str(cluster.id),
            ),
            queue="clusters",
        )

    @staticmethod
    async def create(cluster_id: UUID4, data: ClusterCreateData) -> None:
        """
        Generate the cluster.

        Args:
            cluster_id: The unique identifier of the cluster to be built.
            data: The data for the cluster creation.
        """

        from app.celery.tasks.clusters import (
            cluster_creation_failure_task,
            cluster_creation_success_task,
            cluster_creation_task,
        )

        main_kwargs = dict(cluster_id=str(cluster_id), user_id=str(data.user_id))
        kwargs = main_kwargs | dict(data_pickle=pickle.dumps(data.data), file_data_pickle=pickle.dumps(data.file_data))

        success_link = cluster_creation_success_task.si(**main_kwargs)
        failure_link = cluster_creation_failure_task.s(**main_kwargs)
        cluster_creation_task.apply_async(kwargs=kwargs, link=success_link, link_error=failure_link, queue="clusters")
