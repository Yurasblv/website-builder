import pickle
import random
from urllib.parse import urlparse

from celery import chain
from loguru import logger
from redis import Redis

from app.celery.schemas.pbn import PBNServerSetup, PBNServerStatusCheck
from app.db.redis import redis_pool
from app.enums import PBNEventEnum, PBNGenerationStatus
from app.enums.provider import ServerProviderType
from app.models import PBN, DomainCustom, MoneySite, ServerProvider
from app.models.association import MoneySiteServerAssociation
from app.schemas.pbn import PBNClusterRead, PBNDeploy
from app.services.ai.base import AIBase
from app.services.pbn import PBNService
from app.services.server_provider.base import get_provider
from app.utils import UnitOfWorkNoPool, enqueue_global_message


class PBNDeployService(PBNService):
    def __init__(self) -> None:
        super().__init__()

        self.ai: AIBase = None
        self.redis: Redis = None

        self.obj: PBNDeploy
        self.tx_id: str = None

    @staticmethod
    async def _init() -> "PBNDeployService":
        self = PBNDeployService()
        self.redis = await redis_pool.get_redis()
        self.ai = AIBase()

        return self

    async def _set_params(self, obj: PBNDeploy) -> None:
        self.obj = obj

    @staticmethod
    async def prepare() -> list[PBNDeploy]:
        async with UnitOfWorkNoPool() as uow:
            generate_list = []

            objs: list[PBN] = await uow.pbn.get_all(
                join_load_list=[uow.pbn.user_load, uow.pbn.money_site_load, uow.pbn.domain_load, uow.pbn.server_load],
                status__in=[
                    PBNGenerationStatus.GENERATED,
                    PBNGenerationStatus.BUILD_FAILED,
                    PBNGenerationStatus.DEPLOY_FAILED,
                ],
            )

            for pbn in objs:
                clusters = await uow.cluster.get_all(pbn_id=pbn.id)

                generate_list.append(
                    PBNDeploy(
                        id=pbn.id,
                        user_id=str(pbn.user_id),
                        user_email=pbn.user.email,
                        money_site_id=pbn.money_site.id,
                        money_site_url=pbn.money_site.url,
                        pages_number=pbn.pages_number,
                        status=pbn.status,
                        host=pbn.server.public_net_ipv4,
                        wp_token=pbn.wp_token or "",
                        wp_port=pbn.wp_port or "",
                        clusters=[
                            PBNClusterRead(
                                id=cluster.id,
                                keyword=cluster.keyword,
                                link=cluster.link,
                                topics_number=cluster.topics_number,
                            )
                            for cluster in clusters
                        ],
                    )
                )

        return generate_list

    @classmethod
    async def finalize(cls, pbn_id: str, status_to_set: PBNGenerationStatus = None) -> None:
        from app.services.cloudflare import CloudflareService

        self = await cls._init()
        pbn = await self.set_pbn_status(id_=pbn_id, status=status_to_set)

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

    async def run(self) -> None:
        from app.celery.tasks.pbn import (
            check_server_status_task,
            finalize_redeploy_task,
            register_a_record,
            setup_instance_environment_task,
            setup_wp_tools_task,
            upload_pbn_to_instance_task,
        )

        if self.obj.not_built:
            await self.rebuild_pbn_clusters(obj=self.obj, initial=False)
            logger.success(f"PBN {self.obj.id} has been rebuilt.")

        if self.obj.not_deployed:
            async with UnitOfWorkNoPool() as uow:
                pbn: PBN = await uow.pbn.get_one(join_load_list=[uow.pbn.server_load], id=self.obj.id)

                if pbn.server:
                    task_chain = chain(
                        register_a_record.s(
                            data=pickle.dumps(
                                PBNServerSetup(
                                    user_id=self.obj.user_id,
                                    pbn_id=str(pbn.id),
                                    domain=pbn.domain.name,
                                    public_net_ipv4=pbn.server.public_net_ipv4,
                                    ssh_private_key=pbn.server.ssh_private_key,
                                    provider_type=pbn.server.provider_type,
                                )
                            ),
                        ),
                        setup_wp_tools_task.s(),
                        upload_pbn_to_instance_task.s(),
                    )
                    task_chain.apply_async(
                        link=finalize_redeploy_task.s(pbn_id=str(pbn.id), status_to_set=PBNGenerationStatus.DEPLOYED),
                        link_error=finalize_redeploy_task.s(
                            pbn_id=str(pbn.id), status_to_set=PBNGenerationStatus.ERROR
                        ),
                    )
                else:
                    server_data = random.choice(ServerProviderType.combinations())
                    provider = get_provider(server_data["provider_type"])
                    try:
                        server: ServerProvider = await provider.launch_server(uow, server_data=server_data)

                    except Exception as e:
                        logger.exception(e)
                        pbn.status = PBNGenerationStatus.DEPLOY_FAILED
                        await uow.session.flush([pbn])
                        raise e

                    await uow.session.flush([server])
                    server_association = MoneySiteServerAssociation(
                        money_site_id=self.obj.money_site_id,
                        server_provider_id=server.id,
                        money_site_domain=urlparse(self.obj.money_site_url).netloc.replace("www.", ""),
                    )
                    uow.session.add(server_association)

                    pbn.server_id = server.id
                    pbn.status = PBNGenerationStatus.DEPLOYING

                    await uow.session.flush()

                    task_chain = chain(
                        check_server_status_task.s(
                            data=pickle.dumps(
                                PBNServerStatusCheck(
                                    user_id=self.obj.user_id,
                                    pbn_id=str(pbn.id),
                                    domain=pbn.domain.name,
                                    server_id=server.server_id,
                                    location=server.location,
                                    provider_type=server.provider_type,
                                )
                            ),
                        ),
                        setup_instance_environment_task.s(),
                        register_a_record.s(),
                        setup_wp_tools_task.s(),
                        upload_pbn_to_instance_task.s(),
                    )

                    task_chain.apply_async(
                        link=finalize_redeploy_task.s(pbn_id=str(pbn.id), status_to_set=PBNGenerationStatus.DEPLOYED),
                        link_error=finalize_redeploy_task.s(
                            pbn_id=str(pbn.id), status_to_set=PBNGenerationStatus.ERROR
                        ),
                    )
