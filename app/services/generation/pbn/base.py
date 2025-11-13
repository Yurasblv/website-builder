import asyncio
import json
import pickle
import random
import re
import tempfile
from typing import Any, Sequence
from urllib.parse import urlparse
from uuid import uuid4

from aiohttp import ClientSession
from celery import chain, group
from loguru import logger
from pydantic import HttpUrl
from pydantic.v1 import UUID4
from sentry_sdk import capture_exception

from app.celery.schemas.pbn import PBNServerSetup, PBNServerStatusCheck
from app.core import settings
from app.core.exc import MoneysiteIsProcessingException, PBNPageTemplateException
from app.core.exc.pbn import MoneysiteRequestException
from app.db.redis import redis_pool
from app.enums import (
    BacklinkPublishPeriodEnum,
    Country,
    ExceptionAlias,
    Language,
    ObjectExtension,
    PageStatus,
    PageType,
    PBNGenerationStatus,
    PBNPrompt,
    SpendType,
    TransactionStatus,
)
from app.enums.provider import ServerProviderType
from app.enums.websocket import MoneySiteEventEnum, PBNEventEnum, WebsocketEventEnum
from app.models import PBN, Domain, DomainCustom, MoneySite, PBNPlan, ServerProvider, ServiceAccount, TransactionSpend
from app.models.association import MoneySiteServerAssociation, MoneySiteServiceAccountAssociation
from app.schemas.page.pbn_page import PBNPageCreate
from app.schemas.pbn import (
    BacklinkCreate,
    MoneySiteCreate,
    PBNBacklinkResponse,
    PBNGenerate,
    PBNGenerationRequest,
    PBNLeadPageImageMetadata,
    PBNPlanStructureRead,
    UpdatedTags,
)
from app.schemas.user_info import UserInfoRead
from app.services.ai.base import AIBase
from app.services.ai.image_generator import ImageGenerator
from app.services.generation.base import GeneratorBase
from app.services.pbn import PBNService
from app.services.server_provider.base import get_provider
from app.services.storages import ovh_service
from app.services.transaction import TransactionRefundService, TransactionSpendService
from app.utils import UnitOfWork, UnitOfWorkNoPool, enqueue_global_message

from .cluster import PBNClusterGenerator


class PBNPagesGenerator(PBNService, GeneratorBase):
    def __init__(self) -> None:
        super().__init__()
        self.ai: AIBase = None
        self.request_key = "request_generating_pbns_{user_id}"
        self.obj: PBNGenerate = None
        self.cluster_generator: PBNClusterGenerator = None

    @staticmethod
    async def _init() -> "PBNPagesGenerator":
        self = PBNPagesGenerator()
        await super(PBNPagesGenerator, self)._init()
        self.ai = AIBase()
        return self

    async def _set_generation_params(self, total_plan_pages: int, metadata: PBNGenerate) -> None:
        self.obj = metadata
        self.obj.backlink_page = PageType.CLUSTER

        self.cluster_generator = PBNClusterGenerator(ai=self.ai, pbn_obj=self.obj, total_plan_pages=total_plan_pages)

    @staticmethod
    async def _get_unused_domains(
        uow: UnitOfWork, *, moneysite_url: HttpUrl, domain_ids: list[UUID4], user_id: UUID4
    ) -> Sequence[Domain]:
        """
        Get unused domains from the database.

        Args:
            uow
            moneysite_url: URL of the money site
            domain_ids: List of desired domain UUIDs
            user_id: User ID

        Raises:
            MoneysiteRequestException: If not enough domains are available

        Returns:
            List of Domain objects that are not used and match the given UUIDs.
        """

        domains = await uow.domain_custom.get_all(
            join_load_list=[uow.domain_custom.analytics_no_load], id__in=domain_ids, user_id=user_id, pbn_id=None
        )

        if len(domains) != len(domain_ids):
            pattern = "Request to generate pbns for moneysite '{0}' failed. Not enough domains in the request."
            raise MoneysiteRequestException(message_pattern=(pattern, "moneysite_url"), moneysite_url=moneysite_url)

        return domains

    @staticmethod
    async def _get_unused_service_accounts(
        uow: UnitOfWork, *, moneysite_url: HttpUrl, limit: int, domain: str
    ) -> Sequence[ServiceAccount]:
        """
        Get unused service accounts from the database.
        Args:
            uow
            moneysite_url: URL of the money site
            limit: Number of service accounts to retrieve
            domain: Domain to filter the service accounts by

        Raises:
            MoneysiteRequestException: If not enough service accounts are available

        Returns:
            List of ServiceAccount objects that are not used and match the given domain.
        """

        used_account_ids = await uow.moneysite_service_account.get_used_by_domain(domain=domain)
        service_accounts = await uow.service_account.get_random(limit=limit, id__not_in=used_account_ids)

        if len(service_accounts) < limit:
            pattern = "Request to generate pbns for moneysite '{0}' failed. Not enough service accounts."
            raise MoneysiteRequestException(message_pattern=(pattern, "moneysite_url"), moneysite_url=moneysite_url)

        return service_accounts

    @staticmethod
    async def _get_available_servers(uow: UnitOfWork, limit: int, domain: str) -> Sequence[ServerProvider]:
        """
        Get available servers from the database.

        Args:
            uow
            limit: Number of servers to retrieve
            domain: Domain to filter the servers by

        Returns:
            List of ServerProvider objects that are not used and match the given domain.
        """

        used_server_ids = await uow.moneysite_server.get_used_by_domain(domain=domain)
        servers = await uow.server_provider.get_random_unique(limit=limit, id__not_in=used_server_ids)

        if (n := limit - len(servers)) > 0:
            servers.extend([None] * n)  # type:ignore[attr-defined]

        return servers

    @staticmethod
    async def _get_template_folders(limit: int) -> list[str]:
        """
        Get random template folders from the storage.

        Args:
            limit: Number of folders to retrieve

        Returns:
            List of folder names.
        """

        # TODO: add limit and random params to ovh_service.get_folders_list

        s3_templates_folders = [
            "web-agency",
            "love-nature",
            "nonprofit",
            "planet-earth",
            "shop",
        ]

        # s3_templates_folders = await ovh_service.get_folders_list()

        s3_templates_folders.extend(random.choices(s3_templates_folders, k=max(0, limit - len(s3_templates_folders))))
        return random.sample(s3_templates_folders, k=limit)

    @classmethod
    async def validate_request(
        cls, uow: UnitOfWork, *, pbn_plan: PBNPlan, user_id: UUID4, request_data: PBNGenerationRequest
    ) -> list[tuple[Domain, PBNPlanStructureRead, ServiceAccount, str, ServerProvider]]:
        """
        Validate the request data and prepare the necessary data for PBN generation.

        Args:
            uow: Unit of Work instance
            pbn_plan: PBN plan object
            user_id: User ID
            request_data: Request data object

        Returns:
            List of tuples containing the necessary data for PBN generation.
        """

        pbn_list = PBNPlanStructureRead.to_list(root=request_data.pbn_structure, amount=pbn_plan.websites_amount)
        limit = len(pbn_list)
        money_site_domain = request_data.money_site_domain

        domains = await cls._get_unused_domains(
            uow, moneysite_url=request_data.money_site_url, domain_ids=request_data.domain_uuid_list, user_id=user_id
        )
        service_accounts = await cls._get_unused_service_accounts(
            uow, moneysite_url=request_data.money_site_url, limit=limit, domain=money_site_domain
        )
        templates = await cls._get_template_folders(limit=limit)
        servers = await cls._get_available_servers(uow, limit=limit, domain=money_site_domain)

        # Validate the backlink condition
        if all(not pbn.backlink for pbn in pbn_list):
            request_data.backlink_publish_period_option = None

        return list(zip(domains, pbn_list, service_accounts, templates, servers))

    async def prepare_for_generation(  # type:ignore[override]
        self, user: UserInfoRead, request_data: PBNGenerationRequest, money_site_id: UUID4 = None
    ) -> tuple[TransactionSpend, int, list[PBNGenerate]]:
        """Check if request valid."""
        generate_list = []

        try:
            async with UnitOfWorkNoPool() as uow:
                pbn_plan: PBNPlan = await uow.pbn_plan.get_one(id=request_data.plan_id)
                pbn_plan.check_balance(balance=user.balance)
                money_site_url = str(request_data.money_site_url)

                data = await self.validate_request(uow, pbn_plan=pbn_plan, user_id=user.id, request_data=request_data)

                if await self.redis.hgetall(self.request_key.format(user_id=user.id)):  # TODO: Duplication?
                    raise MoneysiteIsProcessingException(moneysite_url=money_site_url, user_id=user.id)

                money_site_create = MoneySiteCreate(
                    id=money_site_id,
                    url=money_site_url,
                    keyword=request_data.keyword,
                    plan_id=pbn_plan.id,
                    user_id=user.id,
                )

                money_site_db = await uow.money_site.create(obj_in=money_site_create)
                await uow.session.flush([money_site_db])

                transaction = await TransactionSpendService.create(
                    uow,
                    user_id=user.id,
                    amount=pbn_plan.price,
                    object_id=money_site_create.id,
                    object_type=SpendType.PBN,
                )

                for domain, pbn, service_account, template, server in data:
                    category = await uow.category.get_one(id=domain.category_id)

                    obj_in = PBNGenerate(
                        id=pbn.id,
                        user_email=user.email,
                        keyword=request_data.keyword,
                        money_site_url=money_site_url,
                        user_id=user.id,
                        tier=pbn.tier,
                        domain=domain,
                        template=template,
                        pages_number=pbn.pages,
                        server_id=server.id if server else None,
                        language=request_data.language,
                        target_country=request_data.country,
                        category=category.title,
                        money_site_id=money_site_create.id,
                        service_account_id=service_account.id,
                        parent_id=pbn.parent_id,
                    )
                    if request_data.backlink_publish_period_option and pbn.backlink:
                        obj_in.backlink_page = random.choice([PageType.PBN_HOME, PageType.CLUSTER])
                        obj_in.backlink_publish_period_option = request_data.backlink_publish_period_option

                    await self.setup_pbn(uow, obj=obj_in)

                    await uow.session.flush()

                    generate_list.append(obj_in)

        except Exception as e:
            raise e

        await self.redis.hset(
            name=self.request_key.format(user_id=user.id), key="money_site_id", value=str(money_site_create.id)
        )
        return transaction, pbn_plan.pages_amount, generate_list

    async def generate_lead_page(self, page_type: PageType) -> PBNPageCreate:
        backlink = None

        if all([self.obj.backlink_page == PageType.PBN_HOME, self.obj.backlink_publish_period_option]):
            backlink = self.obj.backlink_publish_period_option

        async with PBNPageGenerator(
            s3_template_folder=self.obj.template,
            _type=page_type,
            ai=self.ai,
            pbn_id=self.obj.id,
            user_email=self.obj.user_email,
            pbn_category=self.obj.category,
            keyword=self.obj.keyword,
            language=self.obj.language,
            country=self.obj.target_country,
            backlink=backlink,
            money_site_url=self.obj.money_site_url,
        ) as generator:
            return await generator.generate()

    async def setup_lead_pages(self) -> list[PBNPageCreate]:
        tasks = [self.generate_lead_page(page_type=page_type) for page_type in PageType.pbn_lead_pages()]
        return await asyncio.gather(*tasks)

    async def generate(self) -> None:
        await self.set_pbn_status(id_=self.obj.id, status=PBNGenerationStatus.GENERATING)

        home_page, legal_page, contact_page = await self.setup_lead_pages()
        clusters = await self.cluster_generator.setup_pbn_clusters()

        await self.save_pbn_data(
            home_page=home_page, legal_page=legal_page, contact_page=contact_page, clusters=clusters
        )

        await self.cluster_generator.generate(clusters=clusters)  # type:ignore
        async with UnitOfWorkNoPool() as uow:
            money_site: MoneySite = await uow.money_site.get_one(id=self.obj.money_site_id)
            money_site.pbns_generated += 1

            if self.obj.server_id:
                server_association = MoneySiteServerAssociation(
                    money_site_id=self.obj.money_site_id,
                    server_provider_id=self.obj.server_id,
                    money_site_domain=self.obj.money_site_domain,
                )
                uow.session.add(server_association)

            service_account_association = MoneySiteServiceAccountAssociation(
                money_site_id=self.obj.money_site_id,
                service_account_id=self.obj.service_account_id,
                money_site_domain=self.obj.money_site_domain,
            )
            uow.session.add(service_account_association)

    async def rollback_pbn_generation(self, e: Exception, spend_tx_id: str) -> None:
        """
        Rollback changes in case of an error during PBN generation.

        Raises:
            Exception: Raises the original exception
        """
        async with UnitOfWorkNoPool() as uow:
            info = "Refund for PBN generation. Refund amount: {pages} pages."
            await TransactionRefundService.create(
                uow,
                user_id=self.obj.user_id,
                spend_tx_id=UUID4(spend_tx_id),
                amount=self.obj.pages_number * settings.PAGE_PRICE,
                info=info.format(pages=self.obj.pages_number),
                status=TransactionStatus.COMPLETED,
                object_type=SpendType.PBN,
            )

            pbn: PBN = await uow.pbn.get_one(
                id=self.obj.id,
                join_load_list=[
                    uow.pbn.home_page_load,
                    uow.pbn.legal_page_load,
                    uow.pbn.contact_page_load,
                    uow.pbn.clusters_load,
                ],
            )
            if pbn.status in PBNGenerationStatus.list(2):
                await uow.session.delete(pbn)

        await enqueue_global_message(
            event=WebsocketEventEnum.ERROR,
            user_id=self.obj.user_id,
            pbn_id=self.obj.id,
            alias=getattr(e, "_exception_alias", ExceptionAlias.PBNGenerationFailed),
        )

    @classmethod
    async def finalize_deploy(cls, pbn_id: str, status_to_set: PBNGenerationStatus = None) -> None:
        from app.services.cloudflare import CloudflareService

        pbn = await cls.set_pbn_status(id_=pbn_id, status=status_to_set)

        if status_to_set == PBNGenerationStatus.DEPLOYED:
            async with UnitOfWorkNoPool() as uow:
                money_site: MoneySite = await uow.money_site.get_one(id=pbn.money_site_id)
                money_site.pbns_deployed += 1

            await enqueue_global_message(event=PBNEventEnum.DEPLOYED, user_id=pbn.user_id, pbn_id=pbn.id)

        else:
            async with UnitOfWorkNoPool() as uow:
                domain_custom: DomainCustom | None = await uow.domain_custom.get_one_or_none(pbn_id=pbn.id)

            if domain_custom:
                await CloudflareService.delete_a_record(domain_name=domain_custom.name)

        logger.info(f"PBN {pbn_id}. Status: {status_to_set}")

    @classmethod
    async def finalize_generation(
        cls, generation_key: str, user_id: str, money_site_id: str, money_site_url: str, tx_id: str
    ) -> None:
        from app.celery.tasks.pbns import (
            check_server_status_task,
            pbn_finalize_deploy_handler_task,
            pbn_upload_to_instance_task,
            register_a_record,
            setup_instance_environment_task,
            setup_wp_tools_task,
        )

        redis = await redis_pool.get_redis()
        await redis.delete(generation_key)

        async with UnitOfWorkNoPool() as uow:
            money_site: MoneySite = await uow.money_site.get_one(id=money_site_id)
            spent_tx = await uow.transaction_spend.get_one(id=tx_id)

            if money_site.pbns_generated <= 0:
                spent_tx.status = TransactionStatus.CANCELLED
                await uow.session.delete(money_site)
                logger.info("Money site without generated PBN records. Deleted.")
                return

            spent_tx.status = TransactionStatus.COMPLETED
            await enqueue_global_message(
                event=MoneySiteEventEnum.GENERATED, user_id=user_id, money_site_id=money_site_id
            )
            pbns = await uow.pbn.get_all(join_load_list=[uow.pbn.domain_load], money_site_id=money_site_id)

            for pbn in pbns:
                pbn.status = PBNGenerationStatus.DEPLOYING

                if pbn.server_id:
                    server_db_obj: ServerProvider = await uow.server_provider.get_one(id=pbn.server_id)
                    task_chain = chain(
                        register_a_record.s(
                            data=pickle.dumps(
                                PBNServerSetup(
                                    user_id=user_id,
                                    pbn_id=pbn.id,
                                    domain=pbn.domain.name,
                                    public_net_ipv4=server_db_obj.public_net_ipv4,
                                    ssh_private_key=server_db_obj.ssh_private_key,
                                    provider_type=server_db_obj.provider_type,
                                )
                            ),
                        ),
                        setup_wp_tools_task.s(),
                        pbn_upload_to_instance_task.s(),
                    )
                    task_chain.apply_async(
                        link=pbn_finalize_deploy_handler_task.si(
                            pbn_id=str(pbn.id), status_to_set=PBNGenerationStatus.DEPLOYED
                        ),
                        link_error=pbn_finalize_deploy_handler_task.si(
                            pbn_id=str(pbn.id), status_to_set=PBNGenerationStatus.DEPLOY_FAILED
                        ),
                    )
                    continue

                server_data = random.choice(ServerProviderType.combinations())
                provider = get_provider(server_data["provider_type"])
                try:
                    server: ServerProvider = await provider.launch_server(uow, server_data=server_data)

                except Exception as e:
                    capture_exception(e)
                    pbn.status = PBNGenerationStatus.DEPLOY_FAILED
                    await uow.session.flush([pbn])

                    continue

                await uow.session.flush([server])

                server_association = MoneySiteServerAssociation(
                    money_site_id=money_site_id,
                    server_provider_id=server.id,
                    money_site_domain=urlparse(money_site_url).netloc.replace("www.", ""),
                )
                uow.session.add(server_association)

                pbn.server_id = server.id
                await uow.session.flush()

                task_chain = chain(
                    check_server_status_task.s(
                        data=pickle.dumps(
                            PBNServerStatusCheck(
                                user_id=user_id,
                                pbn_id=pbn.id,
                                domain=pbn.domain.name,
                                server_id=server.server_id,
                                location=server.location,
                                provider_type=server.provider_type,
                            )
                        )
                    ),
                    setup_instance_environment_task.s(),
                    register_a_record.s(),
                    setup_wp_tools_task.s(),
                    pbn_upload_to_instance_task.s(),
                )

                task_chain.apply_async(
                    link=pbn_finalize_deploy_handler_task.si(
                        pbn_id=str(pbn.id), status_to_set=PBNGenerationStatus.DEPLOYED
                    ),
                    link_error=pbn_finalize_deploy_handler_task.si(
                        pbn_id=str(pbn.id), status_to_set=PBNGenerationStatus.DEPLOY_FAILED
                    ),
                )

            logger.success(f"PBN network for money site {money_site_url} was successfully generated.")

    async def _run_test_generation(self, user: UserInfoRead, request_data: PBNGenerationRequest) -> None:
        raise NotImplementedError

    async def run_dev_generation(self, user: UserInfoRead, *, money_site_id: UUID4, data: PBNGenerationRequest) -> None:
        """
        Generates a pbn in the background.

        Args:
            user: customer
            money_site_id: UUID of target db website
            data: request data

        Raises:
            WorkerUnavailableException: if no free workers are available

        Returns:
            PBNQueueResponse with the queue number
        """

        from app.celery.tasks.pbns import pbn_finalize_generation_handler_task, pbn_generate_task

        transaction, total_plan_pages, metadata_list = await self.prepare_for_generation(
            user=user, request_data=data, money_site_id=money_site_id
        )
        tasks_group = group(
            [
                pbn_generate_task.s(
                    total_plan_pages=total_plan_pages, spend_tx_id=str(transaction.id), data=pickle.dumps(metadata)
                ).set(task_id=str(uuid4()))
                for metadata in metadata_list
            ]
        )

        callback = pbn_finalize_generation_handler_task.si(
            **dict(
                generation_key=self.request_key.format(user_id=user.id),
                user_id=str(user.id),
                money_site_id=str(money_site_id),
                money_site_url=str(data.money_site_url),
                tx_id=str(transaction.id),
            )
        )

        tasks_group.apply_async(link=callback, queue="pbn")


class PBNPageGenerator:
    settings = settings.integrations.wp

    def __init__(
        self,
        s3_template_folder: str,
        _type: PageType,
        pbn_id: UUID4,
        ai: AIBase,
        user_email: str,
        keyword: str,
        pbn_category: str,
        language: Language,
        country: Country,
        money_site_url: str,
        backlink: BacklinkPublishPeriodEnum | None,
    ) -> None:
        self.s3_template_folder = s3_template_folder
        self._type = _type
        self.page_id = uuid4()
        self.user_email = user_email
        self.pbn_id = pbn_id
        self.pbn_category = pbn_category
        self.keyword = keyword
        self.language = language
        self.country = country
        self.backlink = backlink
        self.money_site_url = money_site_url

        self.context = ""

        self.ai = ai
        self.image_generator = ImageGenerator()
        self.session: ClientSession = None

    async def __aenter__(self) -> "PBNPageGenerator":
        self.session = ClientSession()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self.session:
            await self.session.close()

    async def download_sample(self) -> tuple:
        logger.info(f"Downloading {self.s3_template_folder} template for {self._type} page, pbn = {self.pbn_id}.")
        path = f"{self.s3_template_folder}/{self._type.wp_path}"
        files = []

        for key in [f"{path}.txt", f"{path}_content.json"]:
            data = await ovh_service.get_file_by_name(key, bucket=settings.storage.pbn_assets)

            if not data:
                message_pattern = ("Template render for {0} type failed. Template not found {1}", "page_type", "key")
                raise PBNPageTemplateException(message_pattern=message_pattern, page_type=self._type, key=key)

            files.append(data)

        template_data = json.loads(files[1])

        placeholders: list = list(filter(None, files[0].decode().split("\n")))

        logger.success(f"Downloading template for {self._type} page, pbn = {self.pbn_id} finished.")

        return placeholders, template_data["content"]

    @staticmethod
    def _parse_placeholder(value: str) -> tuple[str, ...]:
        if value.startswith("img_"):  # TODO: Is used only in one place
            tag, image_id, category, size = value.split("__")
            width, height = size.split("_")
            return image_id, category, width, height

        element_tag, element_name, _ = value.split("__")
        return element_tag, element_name

    @staticmethod
    def replace_image_tags(new_src: str, new_alt: str, text: str) -> str:
        upd_text = re.sub(r'(src="[^"]*")', f' src="{new_src}"', text)
        upd_text = re.sub(r'(alt="[^"]*")', f' alt="{new_alt}"', upd_text)
        return upd_text

    async def insert_backlink_block(self) -> tuple[dict, BacklinkCreate]:
        backlink_create_obj = BacklinkCreate.init(
            keyword=self.keyword,
            url=self.money_site_url,
            pbn_id=self.pbn_id,
            page_id=self.page_id,
            backlink_publish_period_option=self.backlink,  # type: ignore[arg-type]
        )

        block_sample: dict[str, Any] = {
            "blockName": "core/paragraph",
            "attrs": {"id": f"{backlink_create_obj.id}", "align": "center", "style": {"color": {"text": "#121212"}}},
            "innerBlocks": [],
            "innerHTML": '\n<p id= class="backlink" style="color:#121212">{{content}}</p>\n',
            "innerContent": [
                '\n<p class="has-text-align-center has-text-color" style="color:#121212">{{content}}</p>\n'
            ],
        }

        response: PBNBacklinkResponse = await self.ai.gpt_request(
            prompt=PBNPrompt.BACKLINK_SENTENCE_GENERATION_PROMPT,
            output_schema=PBNBacklinkResponse,
            keyword=self.keyword,
        )

        value = re.sub(
            rf"({response.anchor})",
            rf'<a href=\\"{self.money_site_url}\\" {backlink_create_obj.html_visibility}>{response.anchor}</a>',
            response.sentence,
        )
        encoded_data = json.dumps(block_sample, skipkeys=True, ensure_ascii=False)
        encoded_data = re.sub(r"\{\{" + "content" + r"\}\}", value, encoded_data)

        block = json.loads(encoded_data)
        return block, backlink_create_obj

    def insert_texts(self, data: Any, mapping: dict) -> dict:
        try:
            encoded_data = json.dumps(data, skipkeys=True, ensure_ascii=False)

            for key, value in mapping.items():
                value = value.replace("\n", "").replace('"', "")
                if key in encoded_data:
                    encoded_data = re.sub(f"({{{{{key}}}}})", value, encoded_data)

            return json.loads(encoded_data)

        except Exception:
            pattern = "Template render for {0} type failed. Text injection failed. Pbn {1}"
            raise PBNPageTemplateException(
                message_pattern=(pattern, "page_type", "pbn_id"),
                page_type=str(self._type),
                bn_id=self.pbn_id,
            )

    async def _generate_images(self, data: list) -> dict[str, Any]:
        logger.info(f"Starting generation images for {self._type} page, pbn = {self.pbn_id}.")

        content: dict[str, dict] = {}
        generated_image_queries: list[str] = []

        for img_element in data:
            try:
                image_id, image_category, str_width, str_height = self._parse_placeholder(img_element)

                height = int(str_height)
                width = int(str_width)

                large_image = height >= 600 or width >= 600

                if height > width:
                    orientation = "portrait"

                elif width > height:
                    orientation = "landscape"

                else:
                    orientation = "square"

                prompt = PBNPrompt.IMAGE_GENERATION_TEMPLATE.format(
                    keyword=self.keyword,
                    language=self.language,
                    context=self.context,
                    generated_queries=generated_image_queries,
                    image_category=image_category,
                    category=self.pbn_category,
                )
                image_data = await self.ai.gpt_request(
                    prompt=prompt,
                    output_schema=PBNLeadPageImageMetadata,
                    system_prompt=PBNPrompt.IMAGE_GENERATION_ASSISTANT,
                    temperature=1.0,
                )

                img_query = image_data.prompt
                generated_image_queries.append(img_query)
                img_alt = image_data.image_alt_tag

                img_url = await self.image_generator.retrieve_image_from_stock(
                    session=self.session,
                    image_query=img_query,
                    orientation=orientation,
                    large_image=large_image,
                )

                content[img_element] = {
                    "id": image_id,
                    "src": img_url,
                    "alt": img_alt,
                }

            except Exception as e:
                logger.exception(e)
                pattern = "Template render for {0} type failed. Image generation failed. Pbn = {1}"
                raise PBNPageTemplateException(
                    message_pattern=(pattern, "page_type", "detail"),
                    page_type=str(self._type),
                    detail=f"Image generation failed. Pbn = {self.pbn_id}",
                )

        logger.success(f"Generation images for {self._type} page, pbn = {self.pbn_id} finished.")

        return content

    @staticmethod
    def _convert_to_dict(updated_tags: UpdatedTags = None) -> dict:
        data = updated_tags.updated_tags if updated_tags else []
        return {tag.tag_placeholder: tag.new_content for tag in data}

    @staticmethod
    def get_elements(data: list) -> str:
        return "\n".join(f"{idx + 1}. HTML Tag Placeholder: <<{e}>>" for idx, e in enumerate(data))

    async def _generate_texts(self, data: list) -> dict:
        logger.info(f"Starting generation texts for {self._type} page, pbn = {self.pbn_id}.")

        try:
            response = await self.ai.gpt_request(
                prompt=PBNPrompt.CONTENT_GENERATION_PROMPT_TEMPLATE.format(
                    elements=self.get_elements(data),
                    keyword=self.keyword,
                    language=self.language,
                    country=self.country,
                    n=len(data),
                    category=self.pbn_category,
                ),
                output_schema=UpdatedTags,
                system_prompt=PBNPrompt.CONTENT_GENERATION_SYSTEM,
            )

            response = self._convert_to_dict(response)
            self.context += "".join(response.values())

            logger.success(f"Generation texts for {self._type} page, pbn = {self.pbn_id} finished.")

            return response

        except Exception:
            pattern = "Template render for {0} type failed. Text injection failed. Pbn = {1}"
            raise PBNPageTemplateException(
                message_pattern=(pattern, "page_type", "pbn_id"),
                page_type=str(self._type),
                pbn_id=self.pbn_id,
            )

    def process_images(self, obj: dict, mapping: dict) -> Any:
        attrs = obj.get("attrs")

        if not isinstance(attrs, dict):
            return obj

        if not (image_id := attrs.get("id")):
            return obj

        for key, value in mapping.items():
            if not value.get("id") == str(image_id):
                continue

            new_src = value.get("src", "")
            new_alt = value.get("alt", "")

            if "url" in attrs and obj.get("blockName", "") == "core/cover":
                obj["attrs"]["url"] = new_src

            if "innerHTML" in obj and 'src="' in obj["innerHTML"]:
                text = self.replace_image_tags(new_src=new_src, new_alt=new_alt, text=obj["innerHTML"])
                obj["innerHTML"] = text

            if "innerContent" not in obj:
                continue

            inner_content = []

            for data in obj.get("innerContent", []):
                if data and 'src="' in data:
                    data = self.replace_image_tags(new_src=new_src, new_alt=new_alt, text=data)

                inner_content.append(data)

            obj["innerContent"] = inner_content

        return obj

    def insert_images(self, obj: dict, mapping: dict) -> Any:
        try:
            obj = self.process_images(obj, mapping)

            if "innerBlocks" not in obj:
                return obj

            inner_blocks = []

            for i in obj["innerBlocks"]:
                data = self.insert_images(i, mapping)

                inner_blocks.append(data)

            obj["innerBlocks"] = inner_blocks

            return obj

        except Exception:
            pattern = "Template render for {0} type failed. Image injection failed. Pbn = {1}"
            raise PBNPageTemplateException(
                message_pattern=(pattern, "page_type", "pbn_id"),
                page_type=str(self._type),
                pbn_id=self.pbn_id,
            )

    async def generate(self) -> PBNPageCreate:
        placeholders, template = await self.download_sample()

        image_placeholders_list = [key for key in placeholders if key.startswith("img__")]
        text_placeholders_list = [key for key in placeholders if key not in image_placeholders_list]

        logger.info(f"Starting generation data for {self._type} page, pbn = {self.pbn_id}.")
        text_placeholders_mapper = await self._generate_texts(text_placeholders_list)

        image_placeholders_mapper = await self._generate_images(image_placeholders_list)
        logger.success(f"Data generation for {self._type} page, pbn = {self.pbn_id} finished.")

        logger.info(f"Starting inserting generated data for {self._type} page, pbn = {self.pbn_id}.")
        result = []
        backlink_obj = None

        if self.backlink:
            block, backlink_obj = await self.insert_backlink_block()

            if block:
                result.append(block)

        template = self.insert_texts(template, text_placeholders_mapper)

        for block in template:
            result.append(self.insert_images(block, image_placeholders_mapper))

        with tempfile.NamedTemporaryFile(
            mode="w+",
            encoding="utf-8",
            prefix=(f"pbn_{self.pbn_id}_{self.s3_template_folder.replace(' ', '_')}{self._type.wp_path}_"),
        ) as temp_file:
            temp_file.write(json.dumps(result, skipkeys=True, ensure_ascii=False))
            temp_file.seek(0)
            data = temp_file.read().encode()

        json_link = await ovh_service.save_file(
            data=data,
            object_name=ovh_service.construct_object_name(
                user_email=self.user_email,
                pbn_id=self.pbn_id,
                page_id=self.page_id,
                extension=ObjectExtension.JSON,
            ),
        )

        if not json_link:
            pattern = "Template render for {0} type failed. Page was not uploaded. Pbn = {1}"
            raise PBNPageTemplateException(
                message_pattern=(pattern, "page_type", "pbn_id"),
                page_type=str(self._type),
                pbn_id=self.pbn_id,
            )

        logger.success(f"Generated data for {self._type} page, pbn = {self.pbn_id} inserted.")

        return PBNPageCreate(
            id=self.page_id,
            page_type=self._type,
            original_content_file=json_link,
            releases=[json_link],
            pbn_id=self.pbn_id,
            backlink=backlink_obj,
            status=PageStatus.GENERATED,
        )
