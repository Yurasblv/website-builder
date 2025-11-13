import json
from typing import Sequence

from loguru import logger
from pydantic import UUID4

from app.core.exc import (
    ClusterIsNotAllowToBuildException,
    ClusterIsNotAllowToUpdateException,
    ClusterPageTopicsUpdateException,
    ClusterPageUpdateException,
    ClusterVersionUpgradeException,
    PermissionDeniedException,
)
from app.enums import (
    ClusterEventEnum,
    FormattingPrompts,
    GenerationStatus,
    InformationalElementType,
    Language,
    ObjectExtension,
    PageIntent,
)
from app.models import Cluster, PageCluster
from app.schemas.cluster.base import ClusterSettingsCreate
from app.schemas.cluster.generation import ClusterRefreshRead, PageRefreshRead
from app.schemas.elements import ElementContent, StringElementOutput, page_elements_sample_mapper
from app.schemas.page import (
    ClusterPageCommon,
    ClusterPageFilters,
    ClusterPageGenerationMetadata,
    ClusterPageRelations,
    ClusterPagesElementsStyleUpdate,
    ClusterPageUpdate,
    ClusterPageUpdateCommon,
)
from app.schemas.user_info import UserInfoRead
from app.services.ai.base import AIBase
from app.services.next.xmind import XMindGeneratorService
from app.services.page.base import PageServiceBase
from app.services.storages import ovh_service
from app.utils import ABCUnitOfWork, UnitOfWorkNoPool, enqueue_global_message, text_normalize


class ClusterPageService(PageServiceBase):
    @staticmethod
    async def convert_cluster_page_common(
        language: Language, page: PageCluster, children: bool = True, content: bool = True
    ) -> ClusterPageCommon:
        """
        Transform db PageCluster object into ClusterPageCommon schema,
            with defining related pages and downloading content from OVH S3 storage.

        Args:
            language: cluster's language
            page: db page record
            children: flag for adding children ids in list.
                      Useful in cases where no need to get relations between pages.
            content: flag for downloading content from OVH S3 storage.

        Returns:
            ClusterPageCommon schema
        """

        obj = ClusterPageCommon.model_validate(
            page.__dict__, context={"language": language, "topic_path": text_normalize(page.topic)}
        )

        if children:
            obj.related_children = [item.id for item in page.children]

        if content and (file_name := page.current_release):
            data = await ovh_service.get_file_by_name(file_name)
            obj.content = json.loads(data.decode("utf-8")) if data else None

        return obj

    @classmethod
    async def get_page_json(
        cls, unit_of_work: ABCUnitOfWork, *, page_id: UUID4, cluster_id: UUID4, user_id: UUID4
    ) -> ClusterPageCommon:
        """
        Get single page by identifier.

        Args:
            unit_of_work
            page_id: page id
            cluster_id: cluster id
            user_id: user id

        Raises:
            PermissionDeniedException: if user doesn't have permission to view this page

        Returns:
            ClusterPageCommon schema with db PageCluster data
        """

        async with unit_of_work:
            cluster: Cluster = await unit_of_work.cluster.get_one(id=cluster_id)

            if not cluster.is_community and cluster.user_id != user_id:
                raise PermissionDeniedException("You don't have permission to view this page")

            page: PageCluster = await unit_of_work.page_cluster.get_one(
                join_load_list=[unit_of_work.page_cluster.cluster_load, unit_of_work.page_cluster.children_load],
                id=page_id,
                cluster_id=cluster_id,
            )
        return await cls.convert_cluster_page_common(cluster.language, page)

    @classmethod
    async def get_cluster_pages_by_filters(
        cls,
        unit_of_work: ABCUnitOfWork,
        *,
        cluster_id: UUID4,
        user_id: UUID4,
        filters: ClusterPageFilters = ClusterPageFilters(),
        content: bool = False,
    ) -> Sequence[ClusterPageCommon | PageCluster]:
        """
        Get multiple pages by filters.

        Args:
            unit_of_work
            cluster_id: The cluster id.
            user_id: The user id.
            filters: pages filters
            content: flag to upload OVH json content or not

        Returns:
            ClusterPageCommon or PageCluster objs with db data depending on content flag
        """
        filters_dict = filters.model_dump(exclude_none=True, exclude_unset=True)
        limit = filters_dict.pop("limit", 0)
        offset = filters_dict.pop("offset", 0)
        async with unit_of_work:
            cluster = await unit_of_work.cluster.get_one(id=cluster_id, user_id=user_id)

            if content:
                pages: Sequence[PageCluster] = await unit_of_work.page_cluster.get_multi(
                    offset,
                    limit,
                    cluster_id=cluster_id,
                    join_load_list=[unit_of_work.page_cluster.children_load],
                    **filters_dict,
                )
                return [await cls.convert_cluster_page_common(cluster.language, page) for page in pages]
            return await unit_of_work.page_cluster.get_multi(offset, limit, cluster_id=cluster_id, **filters_dict)

    @classmethod
    async def get_pages_tree(cls, unit_of_work: ABCUnitOfWork, *, cluster_id: UUID4) -> list[ClusterPageRelations]:
        """
        Get cluster pages tree structure.

        Args:
            unit_of_work
            cluster_id: The cluster id.

        Returns:
            The list of page structures
        """

        async with unit_of_work:
            pages = await unit_of_work.page_cluster.get_all(cluster_id=cluster_id)

        page_map, children_map = cls._create_maps(pages)
        root_pages = [page for page in pages if not page.parent_id]
        return cls._build_pages_relations(root_pages, children_map)

    @staticmethod
    def _create_maps(pages: Sequence[PageCluster]) -> tuple[dict[UUID4, PageCluster], dict[UUID4, list[PageCluster]]]:
        """
        Creates two mappers from list of PageCluster objects:

        The children_map is constructed by iterating through the given pages,
        identifying those with a `parent_id`, and appending them to the appropriate parent's list.

        Args:
            pages: list of db PageCluster objects

        Returns:
            page_map: dict mapping each page's identifier to its corresponding PageCluster object.
            children_map: dict mapping each parent page identifier to a list of its child PageCluster objects.

        Example:
            page_map = {
                UUID('98dff90d-4e43-45f7-995a-c357e2b6ad9e'): PageCluster,
                UUID('e4091a5b-b73a-4a8c-96ab-1bb254f5ecce'): PageCluster
            }

            children_map : {
                UUID('98dff90d-4e43-45f7-995a-c357e2b6ad9e'): [PageCluster , PageCluster]
            }
        """
        page_map = {page.id: page for page in pages}
        children_map: dict[UUID4, list] = {pid: [] for pid in page_map if page_map[pid].parent_id}

        for page in pages:
            if not page.parent_id:
                continue

            if page.parent_id not in children_map:
                children_map[page.parent_id] = []
            children_map[page.parent_id].append(page)

        return page_map, children_map

    @staticmethod
    def _build_pages_relations(
        root_pages: list[PageCluster], children_map: dict[UUID4, list[PageCluster]]
    ) -> list[ClusterPageRelations]:
        """
        Constructs a hierarchical structure of pages starting from the root pages and
        organizing their children according to the children_map mapper.

        Recursively traverses the pages to build a list of ClusterPageGenerationMetadata
        objects, representing the relationship between parent and child pages.

        Args:
            root_pages: list of main head (no parent_id) db PageCluster objects
            children_map: dict mapping each parent page identifier to a list of its child PageCluster objects.

        Returns:
            page structures representing the hierarchical structure

        Example:

            root_pages = [

            PageCluster(id=UUID('98dff90d-4e43-45f7-995a-c357e2b6ad9e'), parent_id=None, topic='History of Cartoons'),
                ...
            ]
            children_map = {
                UUID('98dff90d-4e43-45f7-995a-c357e2b6ad9e'): [
                    PageCluster(id=UUID('0ef3904e-a2e9-417b-8999-986a98598875'),
                    parent_id=UUID('98dff90d-4e43-45f7-995a-c357e2b6ad9e'),
                    topic='Evolution of cartoons in the US')
                ,...
            ]

            pages_relations = [
                  ClusterPageGenerationMetadata(
                        id=UUID('98dff90d-4e43-45f7-995a-c357e2b6ad9e'),
                        head=True,
                        topic='History of Cartoons',
                        related_parent=None,
                        related_children=[
                            ClusterPageRelations(
                                id=UUID('0ef3904e-a2e9-417b-8999-986a98598875'),
                                head=False,
                                topic='Evolution of cartoons in the US',
                                related_parent=UUID('98dff90d-4e43-45f7-995a-c357e2b6ad9e'),
                                created_at="2021-09-01T12:00:00",
                                related_children=[]
                            ),
                        ...
            )])]

        """
        pages_relations: list[ClusterPageRelations] = []
        processed_pages: set[UUID4] = set()
        for root_page in root_pages:
            stack = [(root_page, None)]
            while stack:
                current_page, parent_relations = stack.pop()
                if current_page.id in processed_pages:
                    continue
                processed_pages.add(current_page.id)
                page_relations = ClusterPageRelations(
                    id=current_page.id,
                    search_intent=current_page.search_intent,
                    cluster_id=current_page.cluster_id,
                    topic=current_page.topic,
                    category=current_page.category,
                    related_parent=current_page.parent_id,
                    updated_at=current_page.updated_at,
                    created_at=current_page.created_at,
                    related_children=[],
                )
                if parent_relations:
                    parent_relations.related_children.append(page_relations)
                if current_page.id in children_map:
                    for child in children_map[current_page.id]:
                        stack.append((child, page_relations))  # type:ignore
                if parent_relations is None:
                    pages_relations.append(page_relations)
        return pages_relations

    @staticmethod
    async def update_cluster_pages_topics(
        unit_of_work: ABCUnitOfWork, *, obj_in: list[ClusterPageUpdateCommon], cluster_id: UUID4, user_id: UUID4
    ) -> int:
        """
        Update topic names for pages on STEP2 during edit tree structure.

        Args:
            unit_of_work
            obj_in: list with topic names for pages and their identifiers
            cluster_id: cluster id
            user_id: user id

        Raises:
            PermissionDeniedException: if user doesn't have permission to update this page

        Returns:
            The number of updated pages.
        """

        upd_result = 0
        async with unit_of_work as uow:
            cluster: Cluster = await unit_of_work.cluster.get_one(
                join_load_list=[uow.cluster.settings_load], id=cluster_id, user_id=user_id, pbn_id=None
            )
            if cluster.status != GenerationStatus.STEP2:
                raise ClusterPageTopicsUpdateException(
                    f"Pages for cluster with {cluster.status} state can not be update"
                )
            db_settings_intents: list[PageIntent] = [s.search_intent for s in cluster.settings]

            if not cluster:
                raise PermissionDeniedException("You don't have permission to update this page")

            for obj in obj_in:
                if obj.search_intent and not page_elements_sample_mapper.get(obj.search_intent):
                    raise ClusterPageUpdateException(f"{obj.search_intent} is not allowed to update.")

                obj_data = obj.model_dump(exclude={"id"}, exclude_none=True)
                upd_result += await uow.page_cluster.update(obj_data, id=obj.id, cluster_id=cluster_id)

            await uow.session.flush()

            pages_intents: list[PageIntent] = list(
                filter(
                    None,
                    [
                        data.get("intent", None)
                        for data in await uow.page_cluster.get_page_intents(cluster_id=cluster_id)
                    ],
                )
            )
            settings_to_delete = list(set(db_settings_intents) - set(pages_intents))

            for s in cluster.settings:
                if s.search_intent in settings_to_delete:
                    await uow.session.delete(s)

            settings_to_create = list(set(pages_intents) - set(db_settings_intents))
            for intent in settings_to_create:
                cluster.settings.append(
                    ClusterSettingsCreate(
                        cluster_id=cluster.id,
                        search_intent=intent,
                        general_style=page_elements_sample_mapper[intent].general_style_sample,  # type: ignore
                        elements_params=page_elements_sample_mapper[intent].elements_param_sample,  # type: ignore
                    ).to_model()
                )

        await XMindGeneratorService.generate(cluster_id=cluster_id)

        return upd_result

    @classmethod
    async def update_page_by_id(
        cls,
        unit_of_work: ABCUnitOfWork,
        *,
        upd_data: ClusterPageUpdate,
        page_id: UUID4,
        cluster_id: UUID4,
        user_id: UUID4,
    ) -> UUID4:
        """
        Update page by id.

        Args:
            unit_of_work:
            upd_data: data for update
            cluster_id: cluster id
            page_id: page id
            user_id: user id

        Raises:
            PermissionDeniedException: if user doesn't have permission to update
            PermissionDeniedException: if page content is not generated yet

        Returns:
            page identifier
        """

        async with unit_of_work:
            cluster: Cluster = await unit_of_work.cluster.get_one_or_none(
                id=cluster_id, user_id=user_id, is_community=False, pbn_id=None
            )

            if not cluster:
                raise PermissionDeniedException("You don't have permission to update this page")

            if cluster.status not in GenerationStatus.able_to_build_statuses():
                raise ClusterIsNotAllowToUpdateException(cluster_id=cluster.id, status=cluster.status)

            page: PageCluster = await unit_of_work.page_cluster.get_one(id=page_id, cluster_id=cluster_id)

            if not page.current_release:
                raise PermissionDeniedException("You can't update page content before generation")

            if upd_data.general_style:
                page.general_style = upd_data.general_style.model_dump()

            if upd_data.content:
                cleaned_data = cls.bleach_clean_data(upd_data.content)
                await ovh_service.delete_files_with_prefix(prefix=page.current_release)
                await ovh_service.save_file(
                    data=cls.jsonify_page_data(data=cleaned_data), object_name=page.current_release
                )

        return page_id

    @classmethod
    async def update_cluster_pages_styles(
        cls,
        unit_of_work: ABCUnitOfWork,
        *,
        obj_in: ClusterPagesElementsStyleUpdate,
        cluster_id: UUID4,
        user: UserInfoRead,
    ) -> None:
        async with unit_of_work:
            cluster: Cluster = await unit_of_work.cluster.get_one(
                id=cluster_id, user_id=user.id, is_community=False, pbn_id=None
            )

            if cluster.status not in GenerationStatus.able_to_build_statuses():
                raise ClusterIsNotAllowToBuildException(cluster_id=cluster_id, status=cluster.status)

            upd_style_mapping = {str(i.tag): (i.style, i.settings, i.classname) for i in obj_in.style_params}

            pages: Sequence[ClusterPageCommon] = await cls.get_cluster_pages_by_filters(
                unit_of_work, cluster_id=cluster_id, user_id=user.id, content=True
            )
            for page in pages:
                if page.search_intent != PageIntent.INFORMATIONAL:
                    continue

                upd_content: list[ElementContent] = []

                if general_style := getattr(obj_in, "general_style", None):
                    await unit_of_work.page_cluster.update({"general_style": general_style.model_dump()}, id=page.id)

                if not page.content or not obj_in.style_params:
                    continue

                for data in page.content:
                    content = ElementContent.model_validate(data)
                    tag_upd_data = upd_style_mapping.get(content.tag, None)
                    if (
                        content.tag not in InformationalElementType.elements_not_for_style_edit()
                        and tag_upd_data is not None
                    ):
                        content.style, content.settings, content.classname = tag_upd_data
                    upd_content.append(content)

                object_name = ovh_service.construct_object_name(  # TODO: Replace with cluster_id/*
                    user_email=user.email, cluster_id=cluster_id, extension=ObjectExtension.JSON, page_id=page.id
                )
                await ovh_service.delete_files_with_prefix(prefix=object_name)
                cleaned_data = cls.bleach_clean_data(upd_content)
                await ovh_service.save_file(data=cls.jsonify_page_data(data=cleaned_data), object_name=object_name)

    @staticmethod
    async def get_cluster_pages_search_intents(
        unit_of_work: ABCUnitOfWork, *, cluster_id: UUID4, user: UserInfoRead
    ) -> list[dict]:
        async with unit_of_work as uow:
            await uow.cluster.get_one(id=cluster_id, user_id=user.id, is_community=False)
            return await uow.page_cluster.get_page_intents(cluster_id=cluster_id)

    @staticmethod
    async def upgrade_cluster_version(user_id: str, user_email: str, cluster_id: str) -> list[str]:
        release_to_del = []

        cluster: ClusterRefreshRead = await ClusterPageService.prepare_data_for_upgrade(
            user_id=user_id, cluster_id=cluster_id
        )

        for i, page in enumerate(cluster.pages, start=1):
            last_release = page.releases[-1]
            last_release_version = (last_release.split("release_v")[-1]).removesuffix(".json")
            new_release_version = int(last_release_version) + 1
            new_release = last_release.replace(f"release_v{last_release_version}", f"release_v{new_release_version}")
            logger.info(f"Refreshing page: {page.topic} | {last_release} -> {new_release} ...")

            elements = await ClusterPageService.rephrase_content(user_email=user_email, cluster=cluster, page=page)

            await enqueue_global_message(
                event=ClusterEventEnum.GENERATING,
                user_id=user_id,
                cluster_id=cluster_id,
                generation_key=f"generating_cluster_{cluster_id}",
                progress=(i / cluster.pages_number) * 0.95,
                message=f"Refreshing Page: {page.id}",
            )

            data = ClusterPageService.jsonify_page_data(data=elements)
            link = await ovh_service.save_file(data=data, object_name=new_release)

            if not link:
                return []

            async with UnitOfWorkNoPool() as uow:
                page = await uow.page_cluster.get_one(id=page.id)

                if len(page.releases) >= 2:
                    release_to_del.append(page.releases[0])
                    page.releases.pop(0)

                page.releases.append(link)

            logger.success(f"Page: {page.topic} | {last_release} -> {new_release} was refreshed")

        return release_to_del

    @staticmethod
    async def rephrase_content(
        user_email: str,
        cluster: ClusterRefreshRead,
        page: PageRefreshRead,
    ) -> list[ElementContent]:
        """
        Retrieves the content of a given release, processes each element, and rephrases the content
        for elements with a specific tag P.
        Returns:
            list of elements with rephrased content.
        """
        from app.services.elements.cluster_pages import InformationalPageElementService

        data = await ovh_service.get_file_by_name(file_name=page.original_content_file)
        content: list[ElementContent] = [
            ElementContent.model_validate(obj)
            for obj in json.loads(data.decode("utf-8"))  # type: ignore[union-attr]
        ]

        reference_enabled = False
        async with AIBase() as ai:
            for pos, element in enumerate(content):  # TODO: add logic to rephrase children's P tags
                if element.tag == "HEAD_CONTENT":
                    page.h1_positions.append(pos)

                if element.tag == "H2":
                    page.h2_positions.append(pos)

                if element.tag == "REFERENCES":
                    reference_enabled = True

                if element.tag != "P":
                    continue

                response = await ai.gpt_request(
                    prompt=FormattingPrompts.REPHRASE_TEMPLATE,
                    output_schema=StringElementOutput,
                    input_text=element.content,
                )

                if response.data:
                    element.content = response.data

        mapper = {
            PageIntent.COMMERCIAL: None,  # TODO: implement
            PageIntent.INFORMATIONAL: InformationalPageElementService,
            PageIntent.NAVIGATIONAL: None,  # TODO: implement
            PageIntent.TRANSACTIONAL: None,  # TODO: implement
        }

        if not (_class := mapper.get(page.search_intent)):
            return content

        page_metadata = ClusterPageGenerationMetadata(
            pbn_id=None,
            cluster_id=cluster.id,
            page_uuid=page.id,
            topic_name=page.topic,
            search_intent=page.search_intent,
            topic_category=page.category,
            parent_id=page.parent_id,
            parent_topic=page.parent_topic,
            neighbours_ids=page.neighbours_ids,
            neighbours_topics=page.neighbours_topics,
            children_ids=page.children_ids,
            children_topics=page.children_topics,
        )

        if settings := cluster.settings.get(page.search_intent):
            page.main_source_link = settings.main_source_link

        async with _class(
            user_email=user_email,
            language=cluster.language,
            target_country=cluster.target_country,
            cluster_keyword=cluster.keyword,
            page_metadata=page_metadata,
            generation_key=f"generating_cluster_{cluster.id}",
        ) as element_service:
            return await element_service.page_content_post_process(
                content=content,
                h1_positions=page.h1_positions,
                h2_positions=page.h2_positions,
                progress_per_page=80.0,
                reference_enabled=reference_enabled,
            )

    @classmethod
    async def prepare_data_for_upgrade(cls, user_id: str, cluster_id: str) -> ClusterRefreshRead:
        """
        Prepares data for cluster upgrade.

        Args:
            user_id: user ID
            cluster_id: The unique identifier of the cluster to be upgraded.

        Returns:
            List of PageCluster objects to be used for the upgrade process.
        """

        async with UnitOfWorkNoPool() as uow:
            db_obj: Cluster = await uow.cluster.get_one(
                join_load_list=[uow.cluster.author_load, uow.cluster.pages_load, uow.cluster.settings_load],
                id=cluster_id,
                user_id=user_id,
                is_community=False,
            )
            if not db_obj.pages:
                raise ClusterVersionUpgradeException(details="No pages found for upgrade")

            return ClusterRefreshRead.model_validate(db_obj.__dict__)
