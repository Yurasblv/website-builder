import json
import re
from typing import Sequence

from aiohttp import ClientSession
from loguru import logger
from pydantic import UUID4

from app.celery.schemas.pbn import PBNServerDeploy
from app.core.exc import ObjectNotFoundException, PBNBuildingException
from app.core.exc.pbn import PBNPlanStructureException
from app.enums import GenerationStatus, PageType, PBNEventEnum, PBNGenerationStatus
from app.enums.websocket import MoneySiteEventEnum
from app.models import PBN, PagePBNContact, PagePBNExtra, PagePBNHome, PagePBNLegal, PBNPlan
from app.schemas.backlink import BacklinkRead
from app.schemas.elements.cluster_pages.base import BaseStyle
from app.schemas.integrations.wordpress import IntegrationWordPressUpload, IntegrationWordPressUploadByChunks
from app.schemas.page.pbn_page import PBNExtraPageCommon, PBNPageCreate
from app.schemas.pbn import (
    PaginatedPBNResponse,
    PBNClusterCreate,
    PBNCreate,
    PBNDeploy,
    PBNFilters,
    PBNGenerate,
    PBNPlanRead,
    PBNPlanStructureRead,
    PBNRead,
    PBNRefresh,
)
from app.schemas.user_info import UserInfoRead
from app.schemas.utils import Ordering, PaginatedOutput, PaginationFilter, Search
from app.services.cluster.static import ClusterStaticBuilder
from app.services.integrations.wordpress import IntegrationWordPressPBNService
from app.services.storages import ovh_service
from app.utils import ABCUnitOfWork, UnitOfWork, UnitOfWorkNoPool, enqueue_global_message, text_normalize


class PBNService:
    @staticmethod
    async def set_pbn_status(id_: UUID4 | str, status: PBNGenerationStatus) -> PBN:
        async with UnitOfWorkNoPool() as uow:
            pbn = await uow.pbn.get_one(id=id_)
            pbn.status = status

        return pbn

    @staticmethod
    async def get_pbn_generation_plans(unit_of_work: ABCUnitOfWork) -> Sequence[PBNPlanRead]:
        async with unit_of_work as uow:
            return await uow.pbn_plan.get_multi()

    @staticmethod
    async def get_by_filters(
        unit_of_work: ABCUnitOfWork,
        *,
        search: Search,
        filters: PBNFilters,
        pagination: PaginationFilter,
        ordering: Ordering,
        user: UserInfoRead | None = None,
    ) -> PaginatedPBNResponse:
        """
        Get pbns by filters

        Args:
            unit_of_work
            search: parts to find
            filters: filters
            pagination: pagination
            ordering: ordering
            user: current user

        Returns:
            list of PBN objects
        """

        response = PaginatedPBNResponse()
        data = (
            filters.model_dump(exclude_none=True)
            | pagination.model_dump()
            | ordering.model_dump()
            | search.model_dump(context={"fields": ["domain_name"]})  # type:ignore
        )

        if user:
            data["user_id"] = user.id

        async with unit_of_work as uow:
            output: PaginatedOutput[PBN] = await uow.pbn.get_by_filters(
                join_load_list=[uow.pbn.money_site_load, uow.pbn.domain_with_analytics_load],
                **data,
            )
            response.count = output.count
            response.total_pages = output.total_pages

            for item in output.input_items:
                response.items.append(PBNRead.model_validate(item))

        return response

    @staticmethod
    async def get_by_id(unit_of_work: ABCUnitOfWork, *, pbn_id: UUID4, user_id: UUID4) -> PBNRead:
        async with unit_of_work as uow:
            return await uow.pbn.get_one(
                id=pbn_id,
                join_load_list=[uow.pbn.money_site_load, uow.pbn.domain_with_analytics_load],
                user_id=user_id,
            )

    @staticmethod
    async def get_pbn_plan_structure(unit_of_work: ABCUnitOfWork, *, plan_id: UUID4) -> PBNPlanStructureRead:
        """
        Get PBN plan structure by plan_id

        Args:
            unit_of_work
            plan_id: plan id

        Raises:
            PBNPlanStructureException: If structure is empty

        Returns:
            PBNPlanStructureRead
        """

        async with unit_of_work as uow:
            db_obj: PBNPlan = await uow.pbn_plan.get_one(id=plan_id)

        if structure := PBNPlanStructureRead.to_tree(db_obj.structure, list(db_obj.structure.keys())):
            return structure

        raise PBNPlanStructureException(plan_id=plan_id)

    @staticmethod
    async def setup_pbn(uow: UnitOfWork, *, obj: PBNGenerate) -> None:
        """
        Setup PBN

        Args:
            uow: unit of work
            obj: PBNGenerate object

        WSEvent:
            - PBNEventEnum.CREATED
        """

        create_obj = PBNCreate.model_validate(obj.model_dump(exclude={"expired_at"}))
        create_obj.expired_at = obj.expired_at
        db_pbn = await uow.pbn.create(obj_in=create_obj.model_dump())

        await uow.session.flush([db_pbn])

        await uow.domain.update(obj_in={"pbn_id": db_pbn.id}, id=obj.domain.id)

        await enqueue_global_message(
            event=PBNEventEnum.CREATED,
            user_id=db_pbn.user_id,
            pbn_id=db_pbn.id,
            money_site_id=str(obj.money_site_id),
        )

    @staticmethod
    async def save_pbn_data(
        home_page: PBNPageCreate,
        legal_page: PBNPageCreate,
        contact_page: PBNPageCreate,
        clusters: list[PBNClusterCreate],
    ) -> None:
        """
        Save PBN data

        Args:
            home_page: home page data
            legal_page: legal page data
            contact_page: contact page data
            clusters: list of clusters data
        """

        async with UnitOfWorkNoPool() as uow:
            home = await uow.page_pbn_home.create(home_page.model_dump(exclude={"backlink"}))
            await uow.session.flush([home])

            if backlink := home_page.backlink:
                backlink_dict = backlink.model_dump(exclude={"publish_at"})
                backlink_dict["publish_at"] = backlink.publish_at
                await uow.backlink.create(obj_in=backlink_dict)

            await uow.page_pbn_legal.create(legal_page.model_dump(exclude={"backlink"}))
            await uow.page_pbn_contact.create(contact_page.model_dump(exclude={"backlink"}))

            for cluster in clusters:
                cluster_data = cluster.model_dump(exclude={"settings", "pages", "author", "backlink"})
                cluster_data["author_id"] = cluster.author.id

                db_cluster = await uow.cluster.create(cluster_data)
                await uow.session.flush([db_cluster])

                for setting in cluster.settings:
                    await uow.cluster_settings.create(obj_in=setting)

                for page in cluster.pages:
                    await uow.page_cluster.create(obj_in=page.model_dump(exclude={"topic_path", "content_file"}))

                if backlink := cluster.backlink:
                    backlink_dict = backlink.model_dump(exclude={"publish_at"})
                    backlink_dict["publish_at"] = backlink.publish_at
                    await uow.backlink.create(obj_in=backlink_dict)

                await uow.session.flush()

    @classmethod
    async def build_pbn_static(
        cls,
        pbn_obj: PBNGenerate,
        total_plan_pages: int,
        clusters: list[PBNClusterCreate],
        money_site_progress: float,
    ) -> None:
        await cls.set_pbn_status(id_=pbn_obj.id, status=PBNGenerationStatus.BUILDING)

        built_pages_counter = 0
        try:
            for cluster in clusters:
                builder = ClusterStaticBuilder(cluster_id=str(cluster.id), user_id=str(pbn_obj.user_id))
                built_version = await builder.build()

                async with UnitOfWorkNoPool() as uow:
                    db_cluster = await uow.cluster.get_one(id=cluster.id)
                    db_cluster.link = built_version
                    db_cluster.status = GenerationStatus.BUILT

                built_pages_counter += cluster.topics_number

                await enqueue_global_message(
                    event=PBNEventEnum.BUILDING,
                    user_id=pbn_obj.user_id,
                    pbn_id=pbn_obj.id,
                    progress=built_pages_counter / pbn_obj.pages_number * 100,
                )

                await enqueue_global_message(
                    event=MoneySiteEventEnum.GENERATING,
                    user_id=pbn_obj.user_id,
                    money_site_id=pbn_obj.money_site_id,
                    progress=money_site_progress + (built_pages_counter / total_plan_pages * 50),
                )

        except Exception as e:
            message_pattern = ("Building of pbn {0} failed. Error: {1}", "pbn_id", "error")
            raise PBNBuildingException(message_pattern=message_pattern, pbn_id=pbn_obj.id, error=e)

        await cls.set_pbn_status(id_=pbn_obj.id, status=PBNGenerationStatus.BUILT)
        await enqueue_global_message(event=PBNEventEnum.BUILT, user_id=str(pbn_obj.user_id), pbn_id=str(pbn_obj.id))

    @classmethod
    async def rebuild_pbn_clusters(cls, obj: PBNRefresh | PBNDeploy, initial: bool = True) -> None:
        status = PBNGenerationStatus.BUILDING if initial else PBNGenerationStatus.REBUILDING
        await cls.set_pbn_status(id_=obj.id, status=status)
        rebuilt_pages_counter = 0

        try:
            for cluster in obj.clusters:
                builder = ClusterStaticBuilder(cluster_id=str(cluster.id), user_id=str(obj.user_id))
                built_version = await builder.build()

                async with UnitOfWorkNoPool() as uow:
                    db_cluster = await uow.cluster.get_one(id=cluster.id)
                    db_cluster.link = built_version
                    db_cluster.status = GenerationStatus.BUILT

                rebuilt_pages_counter += cluster.topics_number
                await enqueue_global_message(
                    event=PBNEventEnum.BUILDING,
                    user_id=obj.user_id,
                    pbn_id=obj.id,
                    progress=rebuilt_pages_counter / obj.pages_number * 100,
                )

        except Exception as e:
            message_pattern = ("Building of pbn {0} failed. Error: {1}", "pbn_id", "error")
            raise PBNBuildingException(message_pattern=message_pattern, pbn_id=obj.id, error=e)

        await cls.set_pbn_status(id_=obj.id, status=PBNGenerationStatus.BUILT)
        await enqueue_global_message(event=PBNEventEnum.BUILT, user_id=obj.user_id, pbn_id=obj.id)

    async def redeploy_pbn_cluster(self, obj: PBNRefresh | PBNDeploy, initial: bool = False) -> None:
        status = PBNGenerationStatus.DEPLOYING if initial else PBNGenerationStatus.REDEPLOYING
        await self.set_pbn_status(id_=obj.id, status=status)

        for cluster in obj.clusters:
            await self.upload_pbn_cluster(
                user_id=str(obj.user_id),
                cluster_id=cluster.id,
                cluster_keyword=cluster.keyword,
                cluster_link=cluster.link,
                url=obj.upload_pbn_url,
                wp_token=obj.wp_token,
            )

        await self.set_pbn_status(id_=obj.id, status=PBNGenerationStatus.DEPLOYED)

    @staticmethod
    async def upload_pbn_lead_pages(
        pbn_id: UUID4,
        home_page: PagePBNHome,
        legal_page: PagePBNLegal,
        contact_page: PagePBNContact,
        url: str,
        wp_token: str,
    ) -> None:
        await IntegrationWordPressPBNService.put_page_content(
            pbn_id,
            page_type=PageType.PBN_HOME,
            content_file=home_page.releases[-1],
            domain=url,
            wp_token=wp_token,
        )
        await IntegrationWordPressPBNService.put_page_content(
            pbn_id,
            page_type=PageType.PBN_CONTACT,
            content_file=contact_page.releases[-1],
            domain=url,
            wp_token=wp_token,
        )
        await IntegrationWordPressPBNService.put_page_content(
            pbn_id,
            page_type=PageType.PBN_LEGAL,
            content_file=legal_page.releases[-1],
            domain=url,
            wp_token=wp_token,
        )

    @staticmethod
    async def upload_pbn_cluster(
        user_id: str, cluster_id: UUID4, cluster_keyword: str, cluster_link: str, url: str, wp_token: str
    ) -> None:
        if not (file_bytes := await ovh_service.get_file_by_name(cluster_link)):
            raise ObjectNotFoundException(f"Static file not found for cluster {cluster_id}")

        chunk_data = IntegrationWordPressUploadByChunks(
            domain=url,
            api_key=wp_token,
            keyword=cluster_keyword,
            data=IntegrationWordPressUpload(),
            cluster_id=str(cluster_id),
            user_id=str(user_id),
            file_bytes=file_bytes,
        )
        await IntegrationWordPressPBNService._chunk_uploading(chunk_data=chunk_data)

    @classmethod
    async def upload_pbn_to_wp(cls, obj_in: PBNServerDeploy) -> None:
        async with UnitOfWorkNoPool() as uow:
            pbn: PBN = await uow.pbn.get_one(
                id=obj_in.pbn_id,
                join_load_list=[
                    uow.pbn.home_page_load,
                    uow.pbn.legal_page_load,
                    uow.pbn.contact_page_load,
                    uow.pbn.clusters_load,
                ],
            )
            home_page = pbn.page_home
            legal_page = pbn.page_legal
            contact_page = pbn.page_contact
            clusters = pbn.clusters

        await cls.upload_pbn_lead_pages(
            pbn_id=pbn.id,
            home_page=home_page,
            legal_page=legal_page,
            contact_page=contact_page,
            url=obj_in.upload_pbn_url,
            wp_token=obj_in.wp_token,
        )

        for cluster in clusters:
            await cls.upload_pbn_cluster(
                user_id=obj_in.user_id,
                cluster_id=cluster.id,
                cluster_keyword=cluster.keyword,
                cluster_link=cluster.link,
                url=obj_in.upload_pbn_url,
                wp_token=obj_in.wp_token,
            )

    @classmethod
    async def get_static_extra_page_files(
        cls, pbn_id: UUID4 | str, page_id: UUID4 | str, page_style: BaseStyle
    ) -> tuple[str, dict, dict, bytes | None]:
        """
        Get the zip file for a page.

        Returns:
            StreamingResponse: response with the zip file
        """

        async with UnitOfWorkNoPool() as uow:
            pbn: PBN = await uow.pbn.get_one(id=pbn_id)
            page: PagePBNExtra = await uow.page_pbn_extra.get_one(id=page_id)

        content = await ovh_service.get_file_by_name(page.current_release)

        if not content:
            raise ObjectNotFoundException(f"Static file not found for page {page_id}")

        page_obj = PBNExtraPageCommon(
            id=page.id,
            pbn_id=pbn.id,
            topic_path=page.topic_path,
            topic=page.topic,
            content=json.loads(content.decode("utf-8")),
            language=pbn.language,
            updated_at=page.updated_at,
            created_at=page.created_at,
            general_style=page_style,
        )

        author_avatar = None
        author_avatar_link = None
        image = None

        images = {}

        for el in page_obj.content:
            if el.get("tag") == "AUTHOR":
                for c in el.get("children", []):
                    if c.get("tag") == "IMG":
                        author_avatar_link = c.get("href")

            if el.get("tag") == "IMG":
                image = el.get("href")

        async with ClientSession() as session:
            if image:
                async with session.get(url=image) as response:
                    images = {f"{page.topic_path}_img.webp": await response.read()}

            if author_avatar_link:
                async with session.get(url=author_avatar_link) as response:
                    author_avatar = await response.read()

        return text_normalize(page.topic_path), {page.topic_path: page_obj}, images, author_avatar

    @staticmethod
    async def enable_hidden_backlinks(backlink: BacklinkRead) -> str | None:
        from app.services.page import PageServiceBase

        logger.info(
            f"Enable backlink= {backlink.id} for page= {backlink.page_type}:{backlink.page_id}, pbn= {backlink.pbn_id}"
        )
        data = await ovh_service.get_file_by_name(backlink.content_file)

        if not data:
            return None

        content = json.loads(data.decode("utf-8"))
        pattern = r'style="display: none;"'
        repl = r'style="display: block;"'

        match backlink.page_type:
            case PageType.PBN_HOME:
                for block in content:
                    if all(
                        [
                            block.get("blockName") == "core/paragraph",
                            backlink.id == block.get("attrs", {}).get("id") == str(backlink.id),
                        ]
                    ):
                        block["innerHTML"] = re.sub(pattern, repl, block.get("innerHTML", ""))

                        innerContent = []
                        for inner_content in block.get("innerContent", []):
                            innerContent.append(re.sub(pattern, repl, inner_content))

                        block["innerContent"] = innerContent

                return await ovh_service.save_file(
                    data=PageServiceBase.jsonify_page_data(data=content), object_name=backlink.content_file
                )

            case PageType.CLUSTER:
                for el in content:
                    if el["tag"] == "META_BACKLINK":
                        el["content"] = re.sub(pattern, repl, el["content"])

                        return await ovh_service.save_file(
                            data=PageServiceBase.jsonify_page_data(data=content), object_name=backlink.content_file
                        )
