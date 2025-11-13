import datetime
import pickle
from typing import Any, Callable, Type
from uuid import uuid4

import aiohttp
from loguru import logger
from pydantic.v1 import UUID4

from app.celery.schemas.pbn import (
    PBNServerDeploy,
    PBNServerSetup,
    PBNServerStatusCheck,
    PBNServerWPSetup,
    ServerRequest,
)
from app.core import settings
from app.core.exc.server_provider import ServerNotAvailable
from app.enums.provider import ServerProviderEndpoint, ServerProviderStatus, ServerProviderType
from app.models import PBN, ServerProvider
from app.schemas.server_provider import (
    CreateProviderServer,
    CreateServerDns,
    HetznerServerRead,
    ProviderServerRead,
    ScalewayServerRead,
    WPConfig,
)
from app.services.storages import storage
from app.utils.unitofwork import UnitOfWork, UnitOfWorkNoPool


class ScriptsService:
    construct_url: Callable
    username: str = "root"

    @classmethod
    async def setup_instance_environment(cls, obj_in: PBNServerSetup) -> None:
        """
        Send request to set up environment on server instance.
        """

        url = cls.construct_url(ServerProviderEndpoint.SCRIPT_SETUP)
        data = obj_in.model_dump(include={"public_net_ipv4", "ssh_private_key"}, mode="json")
        data["server_ip"] = data.pop("public_net_ipv4")
        data["username"] = cls.username

        async with aiohttp.ClientSession(raise_for_status=True) as s, s.post(url, json=data) as _:
            ...

    @classmethod
    async def setup_wp(cls, data: PBNServerWPSetup, **_: Any) -> WPConfig:
        """
        Send request to set up WordPress on server instance.

        Args:
            data: PBNServerWPSetup instance containing server details

        Returns:
            WPConfig: Configuration details for WordPress setup
        """

        url = cls.construct_url(ServerProviderEndpoint.SCRIPT_WORDPRESS)

        async with aiohttp.ClientSession() as s, s.post(url, json=data.model_dump()) as response:
            logger.info(f"Response from {url}: {response.status} - {response.reason}")
            response_data = await response.json()
            logger.info(f"Response data: {response_data}")
            response.raise_for_status()
            return WPConfig.model_validate(response_data)

    @classmethod
    async def drop_wp(cls, data: ServerRequest) -> None:
        """
        Send request to drop WordPress on server instance.

        Args:
            data: Credentials for SSH connection and server IP
        """

        url = cls.construct_url(ServerProviderEndpoint.SCRIPT_WORDPRESS)

        async with aiohttp.ClientSession(raise_for_status=True) as s, s.delete(url, json=data.model_dump()) as _:
            ...


class ProviderBaseService(ScriptsService):
    settings = settings.provider_manager
    provider_type: str
    read_model = ProviderServerRead
    repository = "server_provider"

    @classmethod
    def construct_url(cls, endpoint: ServerProviderEndpoint, **kwargs: Any) -> str:
        """
        Construct URL for the given endpoint and parameters.
        Args:
            endpoint: The endpoint to construct the URL for.
            **kwargs: Additional parameters to include in the URL.

        Returns:
            str: The constructed URL.
        """
        return cls.settings.construct_url(endpoint, provider_type=cls.provider_type, **kwargs)

    @classmethod
    async def create(cls, data: CreateProviderServer) -> ProviderServerRead:
        """
        Create new server instance

        Args:
            data: CreateProviderServer

        Returns:
            Created server instance
        """

        url = cls.construct_url(ServerProviderEndpoint.CREATE, location=data.location)
        request_data = data.model_dump(exclude={"id"})

        async with aiohttp.ClientSession(raise_for_status=True) as s, s.post(url, json=request_data) as response:
            response_data = await response.json()
            response_data["id"] = data.id
            response_data["provider_type"] = cls.provider_type

        return cls.read_model(**response_data)

    @classmethod
    async def get(cls, server_id: str, location: str, instance_id: UUID4 = None) -> ProviderServerRead:
        """
        Retrieve server instance by ID

        Args:
            server_id: Server ID
            location: Server location
            instance_id: UUID4

        Returns:
            Server instance details
        """

        url = cls.construct_url(ServerProviderEndpoint.GET, location=location, server_id=server_id)

        async with aiohttp.ClientSession(raise_for_status=True) as s, s.get(url) as response:
            response_data = await response.json()
            response_data["id"] = instance_id
            response_data["provider_type"] = cls.provider_type

        return cls.read_model(**response_data)

    @classmethod
    async def delete(cls, server_id: str, location: str) -> None:
        """
        Delete server instance

        Args:
            server_id: Server ID
            location: Server location
        """

        url = cls.construct_url(ServerProviderEndpoint.DELETE, location=location, server_id=server_id)

        async with aiohttp.ClientSession(raise_for_status=True) as s, s.delete(url) as _:
            ...

    @classmethod
    async def dns(cls, server_id: str, location: str, data: CreateServerDns) -> dict[str, str]:
        """
        Create DNS record for server

        Args:
            server_id: Server ID
            location: Server location
            data: BaseProviderIdentifier

        Returns:
            dict[str, str]: DNS record success message
        """

        url = cls.construct_url(ServerProviderEndpoint.DNS, location=location, server_id=server_id)
        json_data = data.model_dump(include={"ip", "domain"})

        async with aiohttp.ClientSession(raise_for_status=True) as s, s.post(url, json=json_data) as response:
            return await response.json()

    @classmethod
    async def check_running_status(cls, obj_in: PBNServerStatusCheck) -> bytes:
        """
        Check server status -> Then call setup instance environment task.

        Args:
            obj_in: includes[
                user_id: user id
                pbn_id: PBN id
                server_id: server id
                location: server location
                provider_type: provider type
            ]
        Raises:
            Exception: if server status is not running
        """

        response = await cls.get(server_id=obj_in.server_id, location=obj_in.location)

        if response.status != ServerProviderStatus.RUNNING:
            raise ServerNotAvailable(name=obj_in.server_id, status=response.status)

        async with UnitOfWorkNoPool() as uow:
            server: ServerProvider = await uow.server_provider.get_one(server_id=obj_in.server_id)
            server.status = ServerProviderStatus.RUNNING

        return pickle.dumps(
            PBNServerSetup(
                user_id=obj_in.user_id,
                pbn_id=obj_in.pbn_id,
                domain=obj_in.domain,
                public_net_ipv4=server.public_net_ipv4,
                ssh_private_key=server.ssh_private_key,
                provider_type=server.provider_type,
            )
        )

    @classmethod
    async def launch_server(cls, uow: UnitOfWork, *, server_data: dict) -> ServerProvider:
        """
        Create new server instance
        Args:
            uow: unit of work
            server_data: server data

        Returns:
            ServerProvider: created server instance
        """

        # TODO: remove uow

        server_id = uuid4()
        data = CreateProviderServer(
            **server_data,
            id=server_id,
            name=f"instance-{datetime.date.today().isoformat()}-{str(server_id)[-4:]}",
        )

        response = await cls.create(data)
        repository = getattr(uow, cls.repository)

        obj_in = response.model_dump()

        return await repository.create(obj_in=obj_in)

    @classmethod
    async def setup_wp_tools(cls, obj_in: PBNServerSetup) -> bytes:
        async with UnitOfWorkNoPool() as uow:
            pbn: PBN = await uow.pbn.get_one(join_load_list=[uow.pbn.domain_load], id=obj_in.pbn_id)

        backup_file_url = await storage.get_link(
            "backup.wpress", folder=pbn.template, bucket=settings.storage.pbn_assets
        )

        requests = PBNServerWPSetup(
            server_ip=obj_in.public_net_ipv4,
            domain_name=pbn.domain.name,
            template_url=backup_file_url,
            ssh_private_key=obj_in.ssh_private_key,
            username=cls.username,
        )

        wp_config: WPConfig = await cls.setup_wp(requests)

        pbn_data = dict(wp_token=wp_config.WP_TOKEN, wp_port=wp_config.WP_PORT)

        async with UnitOfWorkNoPool() as uow:
            await uow.pbn.update(pbn_data, id=obj_in.pbn_id)

        return pickle.dumps(
            PBNServerDeploy(
                user_id=obj_in.user_id,
                pbn_id=obj_in.pbn_id,
                url=wp_config.SERVER_DOMAIN,
                host=obj_in.public_net_ipv4,
                **pbn_data,
            )
        )


class ProviderHetznerService(ProviderBaseService):
    provider_type = ServerProviderType.HETZNER
    read_model = HetznerServerRead
    repository = "server_provider_hetzner"
    username: str = "root"


class ProviderScalewayService(ProviderBaseService):
    provider_type = ServerProviderType.SCALEWAY
    read_model = ScalewayServerRead
    repository = "server_provider_scaleway"
    username: str = "ubuntu"


def get_provider(provider_type: ServerProviderType) -> Type[ProviderBaseService]:
    """
    Get the service class for the given provider type.

    Args:
        provider_type: The provider type to get the service for.

    Returns:
        ProviderBaseService: The service class for the given provider type.
    """

    match provider_type:
        case ServerProviderType.HETZNER:
            return ProviderHetznerService

        case ServerProviderType.SCALEWAY:
            return ProviderScalewayService

        case _:
            raise ValueError(f"Unsupported provider type: {provider_type}")
