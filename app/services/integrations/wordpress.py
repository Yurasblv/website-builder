import asyncio
from datetime import datetime, timedelta

import httpx
from fastapi import status
from loguru import logger
from pydantic import UUID4, HttpUrl
from sentry_sdk import capture_exception

from app.core import settings
from app.core.exc import (
    IntegrationWPAlreadyExistsException,
    IntegrationWPConnectionException,
    IntegrationWPDomainNotFoundException,
    IntegrationWPInvalidAPIKeyException,
    IntegrationWPWrongPluginUrl,
    ObjectNotFoundException,
    PermissionDeniedException,
)
from app.core.exc.integration import IntegrationWPIsNotLatestVersionException, IntegrationWPStillInProgressException
from app.enums import ClusterEventEnum, ExceptionAlias, PageType, WebsocketEventEnum, WPEndpoint, WPIntegrationType
from app.models import Cluster, Integration, IntegrationWordPress
from app.schemas.integrations import (
    IntegrationWordPressCreateRequest,
    IntegrationWordPressUpdate,
    IntegrationWordPressUpload,
    IntegrationWordPressUploadByChunks,
    IntegrationWordPressVersionResponse,
)
from app.services.storages import ovh_service
from app.utils import ABCUnitOfWork, UnitOfWork, enqueue_global_message, text_normalize

from .base import IntegrationBaseService


class IntegrationWordPressService(IntegrationBaseService):
    repository: str = "integration_wordpress"
    default_type: WPIntegrationType = WPIntegrationType.CUSTOMER
    default_filter: dict = {"type": default_type}
    settings = settings.integrations.wp
    upload_percentage: int = 5
    processing_percentage: int = 95

    @classmethod
    async def upload(
        cls,
        unit_of_work: ABCUnitOfWork,
        *,
        user_id: UUID4 | str,
        cluster_id: UUID4 | str,
        integration_id: UUID4,
        data: IntegrationWordPressUpload,
    ) -> None:
        """
        Uploads a file to the WordPress site for a specified domain.

        Args:
            unit_of_work
            integration_id: The ID of the WordPress integration.
            cluster_id: The ID of the cluster to fetch the file link.
            data: Data for the WordPress integration.
            user_id: user ID

        Raises:
            PermissionDeniedException: If the user does not have permission to upload to the WordPress site.
            ObjectNotFoundException: If the static file is not found for the cluster.
        """

        async with unit_of_work:
            integration = await unit_of_work.integration_wordpress.get_one(id=integration_id, user_id=user_id)
            cluster: Cluster = await unit_of_work.cluster.get_one(id=cluster_id, user_id=user_id)

        if not cluster.link:
            raise PermissionDeniedException

        # await cls._get_version(integration, ensure_latest=True)
        #
        # await cls.ready(integration.domain, integration.api_key)

        if not (file_bytes := await ovh_service.get_file_by_name(cluster.link)):
            raise ObjectNotFoundException(f"Static file not found for cluster {cluster_id}")

        chunk_data = IntegrationWordPressUploadByChunks(
            domain=integration.domain,
            api_key=integration.api_key,
            keyword=cluster.keyword,
            data=data,
            cluster_id=str(cluster_id),
            user_id=str(user_id),
            file_bytes=file_bytes,
        )

        asyncio.create_task(cls._chunk_uploading(chunk_data))

    @classmethod
    async def _chunk_uploading(cls, chunk_data: IntegrationWordPressUploadByChunks) -> None:
        """
        Uploads a file to the WordPress site for a specified domain by chunks.

        Args:
            chunk_data: Chunk data with the file to upload.

        """
        start = datetime.now()
        headers = {"Authorization": f"Bearer {chunk_data.api_key}"}

        async with httpx.AsyncClient(timeout=cls.settings.timeout, headers=headers) as client:
            limit = await cls.get_limit(client, chunk_data.domain, chunk_data.api_key)

            quotient, rest = divmod(len(chunk_data.file_bytes), limit)
            total_chunks = quotient if not rest else quotient + 1
            filename = f"{text_normalize(chunk_data.keyword)}.zip"
            integration_data = chunk_data.data

            try:
                for chunk_index in range(total_chunks):
                    chunk_bytes = chunk_data.file_bytes[chunk_index * limit : (chunk_index + 1) * limit]

                    response = await client.post(
                        cls.settings.base_url.format(domain=chunk_data.domain, endpoint=WPEndpoint.UPLOAD),
                        data=integration_data.get_data(
                            chunkIndex=chunk_index, totalChunks=total_chunks, fileName=filename
                        ),
                        files={"html_archive": (filename, chunk_bytes, "application/zip")},
                    )
                    cls._check_status_code(response)
                    progress = (chunk_index + 1) / total_chunks

                    await enqueue_global_message(
                        event=ClusterEventEnum.UPLOADING,
                        user_id=chunk_data.user_id,
                        cluster_id=chunk_data.cluster_id,
                        progress=int(progress * cls.upload_percentage),
                        message="Uploading archive",
                    )

                result = response.json()
                if result.get("status") != "unpacked":
                    raise Exception("Unexpected server response")

                current_batch = 0
                total_batches = int(result.get("total_batches", current_batch))

                while start < datetime.now() + timedelta(minutes=10) and current_batch < total_batches:
                    response = await client.post(
                        cls.settings.base_url.format(domain=chunk_data.domain, endpoint=WPEndpoint.PROCESS_BATCH),
                    )

                    cls._check_status_code(response)
                    data = response.json()
                    current_batch = int(data.get("current_batch", total_batches))
                    progress = current_batch / total_batches

                    await enqueue_global_message(
                        event=ClusterEventEnum.UPLOADING,
                        user_id=chunk_data.user_id,
                        cluster_id=chunk_data.cluster_id,
                        progress=cls.upload_percentage + int(progress * cls.processing_percentage),
                        message="Processing archive",
                    )

            except Exception as e:
                capture_exception(e)
                await enqueue_global_message(
                    event=WebsocketEventEnum.ERROR,
                    user_id=chunk_data.user_id,
                    cluster_id=chunk_data.cluster_id,
                    alias=getattr(e, "_exception_alias", ExceptionAlias.FailToUploadToWordPress),
                )

            else:
                await enqueue_global_message(
                    event=ClusterEventEnum.UPLOADED,
                    user_id=chunk_data.user_id,
                    cluster_id=chunk_data.cluster_id,
                )

    @classmethod
    async def ready(cls, domain: HttpUrl | str, api_key: str) -> None:
        """
        Checks if the WordPress site is ready for uploading.

        Args:
            domain: The domain of the WordPress site.
            api_key: The API key for the WordPress site.

        Raises:
            IntegrationWPConnectionException: If there is an issue connecting to the WordPress site.
            IntegrationWPStillInProgressException: If the WordPress site is still in progress.

        """

        async with httpx.AsyncClient(timeout=cls.settings.timeout) as client:
            try:
                response = await client.get(
                    cls.settings.base_url.format(domain=domain, endpoint=WPEndpoint.UPLOAD_READY),
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                cls._check_status_code(response)
                data = response.json()
                ready = data.get("message")

                if not ready:
                    raise IntegrationWPStillInProgressException(domain=domain)

            except httpx.ConnectError as e:
                raise IntegrationWPConnectionException(
                    url=domain,
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    response_text=str(e),
                )

        cls._check_status_code(response)

    @classmethod
    async def ping(cls, domain: HttpUrl | str, api_key: str) -> None:
        """
        Pings the WordPress site to check if the API key is valid.

        Args:
            domain: The domain of the WordPress site.
            api_key: The API key for the WordPress site.

        Raises:
            IntegrationWPConnectionException: If there is an issue connecting to the WordPress site.
        """

        async with httpx.AsyncClient(timeout=cls.settings.timeout) as client:
            try:
                response = await client.get(
                    cls.settings.base_url.format(domain=domain, endpoint=WPEndpoint.PING),
                    headers={"Authorization": f"Bearer {api_key}"},
                )

            except httpx.ConnectError as e:
                raise IntegrationWPConnectionException(
                    url=domain,
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    response_text=str(e),
                )

        cls._check_status_code(response)

    @classmethod
    async def create(
        cls, unit_of_work: ABCUnitOfWork, *, user_id: UUID4 | str, data: IntegrationWordPressCreateRequest
    ) -> Integration:
        """
        Creates a new WordPress integration for a user.

        Args:
            unit_of_work
            user_id: user ID
            data: Data for the new integration.

        Raises:
            IntegrationWordPressValidationException: If WordPress validation fails.

        Returns:
            The created WordPress integration.
        """

        await cls.ping(data.domain, data.api_key)

        obj_in = data.model_dump(mode="json")
        obj_in["user_id"] = user_id
        obj_in["type"] = cls.default_type

        async with unit_of_work:
            if await unit_of_work.integration_wordpress.get_one_or_none(domain=str(data.domain), user_id=user_id):
                raise IntegrationWPAlreadyExistsException

            return await unit_of_work.integration_wordpress.create(obj_in)

    @staticmethod
    def _check_status_code(response: httpx.Response) -> None:
        match response.status_code:
            case status.HTTP_200_OK | status.HTTP_201_CREATED:
                return

            case status.HTTP_403_FORBIDDEN | status.HTTP_401_UNAUTHORIZED:
                raise IntegrationWPInvalidAPIKeyException(url=response.url)

            case status.HTTP_404_NOT_FOUND:
                raise IntegrationWPDomainNotFoundException(url=response.url)

            case stat if 300 <= stat < 400:
                raise IntegrationWPWrongPluginUrl(url=response.url, status_code=response.status_code)

            case _:
                raise IntegrationWPConnectionException(
                    url=response.url,
                    status_code=response.status_code,
                    response_text=response.text,
                )

    @classmethod
    async def prepare_update(  # type: ignore[override]
        cls, obj: IntegrationWordPress, data: IntegrationWordPressUpdate
    ) -> None:
        """
        Check a new api_key before updating the integration.

        Args:
            obj: The WordPress integration to update.
            data: Data to update the WordPress integration.
        """

        await cls.ping(obj.domain, data.api_key)

    @classmethod
    async def get_limit(cls, client: httpx.AsyncClient, domain: HttpUrl | str, api_key: str) -> int:
        """
        Get the chunk size limit for the WordPress site.

        Args:
            client: The HTTPX client.
            domain: The domain of the WordPress site.
            api_key: The API key for the WordPress site.

        Returns:
            The chunk size limit for the WordPress site.
        """

        response = await client.get(
            cls.settings.base_url.format(domain=domain, endpoint=WPEndpoint.LIMIT),
            headers={"Authorization": f"Bearer {api_key}"},
        )
        cls._check_status_code(response)
        data = response.json()
        limit = data.get("chunk_size", 1 * 1024 * 1024)

        return min(limit, 10 * 1024 * 1024)

    @classmethod
    async def _get_version(
        cls, integration: IntegrationWordPress, ensure_latest: bool = False
    ) -> IntegrationWordPressVersionResponse:
        """
        Get the version of the WordPress plugin.

        Args:
            integration: The WordPress integration.
            ensure_latest: Whether to ensure the version is the latest one.

        Raises:
            IntegrationWPIsNotLatestVersionException: If the version is not the latest one.

        Returns:
            The version of the WordPress plugin.
        """

        try:
            async with httpx.AsyncClient(timeout=cls.settings.timeout) as client:
                response = await client.get(
                    cls.settings.base_url.format(domain=integration.domain, endpoint=WPEndpoint.VERSION),
                    headers={"Authorization": f"Bearer {integration.api_key}"},
                )
                cls._check_status_code(response)
                data = IntegrationWordPressVersionResponse.model_validate(response.json())

        except Exception as e:
            if response.status_code != status.HTTP_404_NOT_FOUND:
                capture_exception(e)

            logger.warning(f"Error getting version for {integration.domain}: {e}")
            raise IntegrationWPIsNotLatestVersionException(
                domain=integration.domain, current_version="unknown", latest_version="unknown"
            )

        if ensure_latest and not data.is_latest:
            raise IntegrationWPIsNotLatestVersionException(
                domain=integration.domain, current_version=data.current_version, latest_version=data.latest_version
            )

        return data

    @classmethod
    async def retrieve_version(
        cls, unit_of_work: ABCUnitOfWork, *, integration_id: UUID4, user_id: UUID4
    ) -> IntegrationWordPressVersionResponse:
        """
        Retrieve the version of the WordPress plugin.

        Args:
            unit_of_work
            integration_id: The ID of the WordPress integration.
            user_id: The ID of the user.

        Returns:
            The version of the WordPress plugin.
        """

        async with unit_of_work:
            integration = await unit_of_work.integration_wordpress.get_one(id=integration_id, user_id=user_id)

        return await cls._get_version(integration)


class IntegrationWordPressPBNService(IntegrationWordPressService):
    default_type: WPIntegrationType = WPIntegrationType.PBN

    @staticmethod
    async def get_integration(domain: str) -> IntegrationWordPress:
        async with UnitOfWork() as uow:
            return await uow.integration_wordpress.get_one(domain=domain)

    @classmethod
    async def get_content(cls, page_type: str, domain: str) -> None:
        """
        Get the content of a page on the WordPress site.

        Args:
            page_type: The page to get the content of.
            domain: The domain of the WordPress site.

        Raises:
            IntegrationWPConnectionException: If there is an issue connecting to the WordPress site.
        """

        integration = await cls.get_integration(domain)

        endpoint = cls.settings.base_url.format(domain=integration.domain, endpoint=WPEndpoint.PBN_CONTENT)
        url = endpoint.format(type=page_type)

        async with httpx.AsyncClient(timeout=cls.settings.timeout) as client:
            try:
                response = await client.get(url, headers={"Authorization": f"Bearer {integration.api_key}"})

            except httpx.ConnectError as e:
                raise IntegrationWPConnectionException(
                    url=integration.domain,
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    response_text=str(e),
                )

        cls._check_status_code(response)

    @classmethod
    async def put_page_content(
        cls, pbn_id: UUID4, *, page_type: PageType, content_file: str, domain: str, wp_token: str
    ) -> None:
        """
        Update the content of a page on the WordPress site.

        Args:
            page_type: The page to update.
            content_file: The new content of the page.
            pbn_id: The ID of the PBN
            domain: domain to upload
            wp_token: api key

        Raises:
            IntegrationWPConnectionException: If there is an issue connecting to the WordPress site.
        """

        endpoint = cls.settings.base_url.format(domain=domain, endpoint=WPEndpoint.PBN_CONTENT)
        url = endpoint.format(type=page_type.wp_path)

        if not (file_data := await ovh_service.get_file_by_name(file_name=content_file)):
            raise ObjectNotFoundException(f"Not found Page {page_type} for {pbn_id=}")

        async with httpx.AsyncClient(timeout=cls.settings.timeout) as client:
            try:
                logger.info(f"Sending updated template for {page_type} page, pbn = {pbn_id}.")

                response = await client.put(
                    url,
                    headers={"Authorization": f"Bearer {wp_token}"},
                    data={"content": file_data.decode()},
                )

            except httpx.ConnectError as e:
                raise IntegrationWPConnectionException(
                    url=domain,
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    response_text=str(e),
                )

        cls._check_status_code(response)

        logger.success(f"Template for {page_type} page, pbn = {pbn_id} updated.")

    @classmethod
    async def change_site_name(cls, new_name: str, domain: str) -> None:
        """
        Change the name of the WordPress site.

        Args:
            new_name: The new name of the WordPress site.
            domain: The domain of the WordPress site.

        Raises:
            IntegrationWPConnectionException: If there is an issue connecting to the WordPress site.
        """

        integration = await cls.get_integration(domain)

        endpoint = cls.settings.base_url.format(domain=integration.domain, endpoint=WPEndpoint.PBN_NAME)
        url = endpoint.format(name=new_name)

        async with httpx.AsyncClient(timeout=cls.settings.timeout) as client:
            try:
                response = await client.put(url, headers={"Authorization": f"Bearer {integration.api_key}"})

            except httpx.ConnectError as e:
                raise IntegrationWPConnectionException(
                    url=domain,
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    response_text=str(e),
                )

        cls._check_status_code(response)
