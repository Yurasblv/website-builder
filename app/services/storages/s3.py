import asyncio
from typing import AsyncIterator

from aiobotocore.client import AioBaseClient
from aiobotocore.config import AioConfig
from aiobotocore.session import ClientCreatorContext, get_session
from aiohttp import ClientSession
from botocore.exceptions import ClientError
from loguru import logger
from sentry_sdk import capture_exception
from urllib3.util import parse_url

from app.core import settings
from app.core.exc import OVHFailedFetchFileException, OVHMaxRetryException
from app.enums import ObjectExtension
from app.enums.base import StorageBackend
from app.services.storages.abc import AbstractStorageRepository
from app.utils import webp_converter


class S3StorageRepository(AbstractStorageRepository):
    """S3 storage backend."""

    def __init__(self) -> None:
        self.settings = settings.storage.s3
        self.config = AioConfig(retries={"max_attempts": 10, "mode": "standard"}, read_timeout=60)
        self.session = get_session()

    # Specific backend methods
    async def create_client(self) -> ClientCreatorContext:
        """Init session for connection to OVH"""
        return self.session.create_client(
            "s3",
            region_name=self.settings.REGION,
            endpoint_url=f"https://{self.settings.ENDPOINT_URL}",
            aws_secret_access_key=self.settings.SECRET_KEY,
            aws_access_key_id=self.settings.ACCESS_KEY,
            config=self.config,
        )

    async def get_link(self, key: str, bucket: str = None, folder: str = None, expires_in: int = None) -> str:
        """
        Create public link to file.

        Args:
            key: file path
            bucket: bucket name
            folder: folder name
            expires_in: time in seconds

        Returns:
            Public link to file
        """

        bucket = bucket or self.settings.topics
        expires_in = expires_in or self.settings.LINK_EXPIRES

        if folder:
            key = f"{folder}/{key}"

        async with await self.create_client() as client:
            return await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expires_in,
            )

    async def fetch_file(self, client: AioBaseClient, key: str, bucket: str = None) -> dict[str, bytes | None]:
        """
        Fetch file from S3 bucket.

        Args:
            client: S3 client
            key: file path
            bucket: bucket name

        Returns:
            dict with file path and data in bytes

        """

        max_retries = 4
        backoff_factor = 2

        bucket = bucket or self.settings.topics

        for attempt in range(max_retries):
            try:
                file = await client.get_object(Bucket=bucket, Key=key)
                data = await file.get("Body").read()
                return {key: data}

            except ClientError as e:
                if e.response["Error"]["Code"] == "SlowDown":
                    wait_time = backoff_factor**attempt
                    logger.warning(f"Throttling detected. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue

                logger.error(f"Error fetching {key}: {e}")
                break

            except asyncio.TimeoutError:
                wait_time = backoff_factor**attempt
                logger.warning(f"Timeout occurred. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue

            except Exception as e:
                capture_exception(e)
                logger.error(f"Error fetching {key}: {e}")
                break

        return {key: None}

    # Protocol methods
    async def get_file_by_name(self, file_name: str, bucket: str = None) -> bytes | None:
        """
        Retrieve object by file name which represent path to file in S3.

        Args:
            file_name: object path
            bucket: bucket name

        Returns:
            if jsonify object in file, otherwise byte string
        """
        bucket = bucket or self.settings.topics

        try:
            async with await self.create_client() as client:
                ret = await self.fetch_file(client=client, key=file_name, bucket=bucket)
                return ret[file_name]

        except Exception as e:
            logger.exception(e)

    async def get_files(self, *keys: str, bucket: str = None) -> list[dict[str, bytes | None]]:
        """
        Fetch multiple files from S3 bucket.

        Args:
            keys: list of file paths
            bucket: bucket name

        Returns:
            list of dicts with file paths and data in bytes
        """

        if not keys:
            return []

        bucket = bucket or self.settings.topics
        async with await self.create_client() as client:
            tasks = [self.fetch_file(client, key, bucket) for key in keys]
            return await asyncio.gather(*tasks)

    async def stream_file(self, file_name: str, bucket: str = None) -> AsyncIterator[bytes]:  # type: ignore
        """
        Stream file from S3 bucket.

        Args:
            file_name: object path
            bucket: bucket name

        Raises:
            OVHFailedFetchFileException: if file not found

        Returns:
            stream of bytes
        """
        bucket = bucket or self.settings.topics
        async with await self.create_client() as client:
            try:
                response = await client.get_object(Bucket=bucket, Key=file_name)
                if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
                    raise OVHFailedFetchFileException(error=response["ResponseMetadata"])

                async for chunk in response["Body"].iter_chunks():
                    yield chunk

            except OVHFailedFetchFileException:
                raise

            except Exception as e:
                capture_exception(e)
                raise OVHFailedFetchFileException(error=e)

    async def get_first(self, prefix: str, suffix: str = None, bucket: str = None) -> str | None:
        """
        Get the first object by prefix and suffix.

        Args:
            prefix: part of the name
            suffix: part of the name
            bucket: bucket name

        Returns:
            file path
        """

        bucket = bucket or self.settings.topics

        async with await self.create_client() as s3:
            paginator = s3.get_paginator("list_objects_v2")

            async for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    key = obj["Key"]

                    if suffix and not key.endswith(suffix):
                        continue

                    return key

    async def get_folders_list(self, bucket: str = None) -> list[str]:
        bucket = bucket or self.settings.pbn_assets

        folders = []

        try:
            async with await self.create_client() as s3:
                paginator = s3.get_paginator("list_objects_v2")
                paginator_args = {"Bucket": bucket, "Delimiter": "/"}
                async for page in paginator.paginate(**paginator_args):
                    for prefix in page.get("CommonPrefixes", []):
                        folder: str = prefix["Prefix"].replace("/", "")

                        folders.append(folder)

        except Exception as e:
            logger.exception(e)

        return folders

    async def get_files_with_prefix(self, prefix: str, bucket: str = None) -> list[str]:
        """
        Retrieve objects by file name prefix.

        Args:
            prefix: part of the name
            bucket: bucket name

        Returns:
            list of strings with file paths
        """

        bucket = bucket or self.settings.topics

        async with await self.create_client() as s3:
            paginator = s3.get_paginator("list_objects_v2")
            async for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                folder_files = [obj["Key"] for obj in page.get("Contents", [])]

        logger.debug(f"Found files. PREFIX:{prefix}. FILES:{folder_files}")
        return folder_files

    async def save_file(self, data: bytes, object_name: str, bucket: str = None) -> str:
        """
        Upload bytes data into file with object_name name .

        Args:
            data: bytes content
            object_name: file name to upload
            bucket: bucket name

        Raises:
            OVHMaxRetryException: if max retries reached

        Returns:
            file path in S3 bucket
        """

        bucket = bucket or self.settings.topics
        delay = self.settings.UPLOAD_DELAY

        for attempt in range(self.settings.UPLOAD_RETRIES):
            try:
                async with await self.create_client() as s3:
                    await s3.put_object(Bucket=bucket, Key=object_name, Body=data, ACL="public-read")
                    logger.info(f"File was uploaded. URL: {object_name}")
                    return object_name

            except Exception as e:
                logger.exception(e)
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff

        else:
            error = OVHMaxRetryException
            logger.exception(error)
            raise error

    async def save_remote_file(
        self,
        link: str | None,
        object_name: str,
        extension_with: ObjectExtension = ObjectExtension.WEBP,
    ) -> str | None:
        if not link:
            return None

        try:
            async with ClientSession() as session:
                response = await session.get(link)
                data = await response.read()

            if extension_with == ObjectExtension.WEBP:
                data = webp_converter(data)

            fetch_path = await self.save_file(data=data, object_name=object_name)

            if fetch_path:
                return parse_url(f"{self.settings.topics_uri}/{fetch_path}").url

        except Exception as e:
            logger.error(e)

    async def delete_files(self, *keys: str, bucket: str = None) -> None:
        """
        Delete objects by file names.

        Args:
            keys: list of file paths
            bucket: bucket name
        """

        if not keys:
            return

        bucket = bucket or self.settings.topics
        delete_requests = [{"Key": key} for key in keys]

        async with await self.create_client() as s3:
            await s3.delete_objects(Bucket=bucket, Delete={"Objects": delete_requests})

        logger.debug(f"Files with {keys=} successfully deleted")

    async def delete_files_with_prefix(self, prefix: str, bucket: str = None) -> None:
        """
        Delete objects by file name prefix.

        Args:
            prefix: part of the name
            bucket: bucket name
        """

        bucket = bucket or self.settings.topics
        files_to_delete = await self.get_files_with_prefix(prefix=prefix, bucket=bucket)
        if not files_to_delete:
            logger.info("No files to delete.")
            return

        await self.delete_files(*files_to_delete, bucket=bucket)

    # Proxy methods TODO: replace with Protocol methods after merging
    async def fetch_files(self, *keys: str, bucket: str = None) -> list[dict[str, bytes | None]]:
        return await self.get_files(*keys, bucket=bucket)

    async def stream_file_from_s3(self, file_name: str, bucket: str = None) -> AsyncIterator[bytes]:
        async for chunk in self.stream_file(file_name, bucket):
            yield chunk

    async def upload_remote_file_to_s3(
        self,
        link: str | None,
        object_name: str,
        extension_with: ObjectExtension = ObjectExtension.WEBP,
    ) -> str | None:
        return await self.save_remote_file(link, object_name, extension_with)


is_s3 = settings.storage.backend_type == StorageBackend.S3
repository: S3StorageRepository | None = S3StorageRepository() if is_s3 else None
