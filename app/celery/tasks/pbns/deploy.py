import asyncio
import pickle

from loguru import logger

from app.celery import celery_app
from app.celery.schemas.pbn import (
    PBNServerDeploy,
    PBNServerSetup,
    PBNServerStatusCheck,
    PickledPBNServerDeploy,
    PickledPBNServerSetup,
    PickledPBNServerStatusCheck,
)
from app.core.exc import CloudflareARecordCreationException
from app.enums import PBNGenerationStatus
from app.services import CloudflareService
from app.services.generation.pbn import PBNPagesGenerator
from app.services.pbn import PBNService
from app.services.server_provider.base import get_provider


@celery_app.task(
    name="check_server_status_task", autoretry_for=(Exception,), retry_jitter=False, retry_backoff=20, max_retries=3
)
def check_server_status_task(data: PickledPBNServerStatusCheck) -> bytes:
    """
    Check the status of the server instance.

    Args:
        data: The pickled PBNServerStatusCheck object.

    Returns:
        The pickled PBNServerSetup object.
    """

    obj_in: PBNServerStatusCheck = pickle.loads(data)
    logger.info(f"check_server_status_task data: {obj_in}")  # TODO: REMOVE
    provider = get_provider(obj_in.provider_type)

    with asyncio.Runner() as runner:
        result = runner.run(provider.check_running_status(obj_in))
        return result


@celery_app.task(
    name="setup_instance_environment_task",
    autoretry_for=(Exception,),
    retry_jitter=False,
    retry_backoff=20,
    max_retries=3,
)
def setup_instance_environment_task(data: PickledPBNServerSetup) -> bytes:
    """
    Set up the environment for the server instance.

    Args:
        data: The pickled PBNServerSetup object.

    Returns:
        The input pickled PBNServerSetup object.
    """

    obj_in: PBNServerSetup = pickle.loads(data)
    logger.info(f"setup_instance_environment_task data: {obj_in}")  # TODO: REMOVE
    provider = get_provider(obj_in.provider_type)

    async def f() -> None:
        await provider.setup_instance_environment(obj_in)
        await asyncio.sleep(60)

    with asyncio.Runner() as runner:
        runner.run(f())

    return data


@celery_app.task
def register_a_record(data: PickledPBNServerSetup) -> bytes:
    """
    Register an A record in Cloudflare for the given domain and IP address.

    Args:
        data: The pickled PBNServerSetup object.

    Returns:
        The input pickled PBNServerSetup object.
    """

    obj_in: PBNServerSetup = pickle.loads(data)
    logger.info(f"register_a_rec data: {obj_in}")  # TODO: REMOVE

    with asyncio.Runner() as runner:
        try:
            runner.run(CloudflareService.add_a_record(domain_name=obj_in.domain, ip=obj_in.public_net_ipv4))

        except Exception as e:
            raise CloudflareARecordCreationException(user_id=obj_in.user_id, domain=obj_in.domain, exc=str(e))

    return data


@celery_app.task(
    name="setup_wp_tools_task", autoretry_for=(Exception,), retry_jitter=False, retry_backoff=20, max_retries=3
)
def setup_wp_tools_task(data: PickledPBNServerSetup) -> bytes:
    """
    Setup WordPress tools on the server instance.

    Args:
        data: The pickled PBNServerSetup object.

    Returns:
        The pickled PBNServerDeploy object.
    """

    obj_in: PBNServerSetup = pickle.loads(data)
    logger.info(f"setup_wp_tools_task data: {obj_in}")  # TODO: REMOVE
    provider = get_provider(obj_in.provider_type)

    with asyncio.Runner() as runner:
        return runner.run(provider.setup_wp_tools(obj_in))


@celery_app.task(
    name="pbn_upload_to_instance_task", autoretry_for=(Exception,), retry_jitter=False, retry_backoff=20, max_retries=3
)
def pbn_upload_to_instance_task(data: PickledPBNServerDeploy) -> None:
    """
    Upload PBN to the server instance.

    Args:
        data: The pickled PBNServerDeploy object.
    """

    obj_in: PBNServerDeploy = pickle.loads(data)
    logger.info(f"upload_pbn_to_instance_task data: {obj_in}")  # TODO: REMOVE

    with asyncio.Runner() as runner:
        runner.run(PBNService.upload_pbn_to_wp(obj_in))


@celery_app.task
def pbn_finalize_deploy_handler_task(pbn_id: str, status_to_set: PBNGenerationStatus) -> None:
    """
    Finalize the PBN deployment process.

    Args:
        pbn_id: The ID of the PBN.
        status_to_set: The status to set for the PBN.
    """

    with asyncio.Runner() as runner:
        runner.run(PBNPagesGenerator.finalize_deploy(pbn_id=pbn_id, status_to_set=status_to_set))
