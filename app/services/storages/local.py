import os
from pathlib import Path
from typing import Any

import aiofiles
from aiohttp import ClientSession
from loguru import logger

from app.core import settings
from app.enums import ObjectExtension
from app.enums.base import StorageBackend
from app.services.storages.abc import AbstractStorageRepository
from app.utils import webp_converter


class LocalStorageRepository(AbstractStorageRepository):
    """S3 storage backend."""

    def __init__(self) -> None:
        self.settings = settings.storage.local

        self.folder: Path = self.settings.base
        self.folder.mkdir(exist_ok=True)

    # Specific backend methods
    def get_folder(self, folder_name: str = None) -> Path:
        """
        Create folder if not exists.

        Args:
            folder_name: folder name

        Returns:
            Folder path
        """

        folder = self.folder / (folder_name or self.settings.topics)
        folder.mkdir(exist_ok=True)
        return folder

    # Protocol methods
    async def get_file_by_name(self, file_name: str, bucket: str = None) -> bytes | None:
        """
        Retrieve object by file name from local storage.

        Args:
            file_name: object path
            bucket: folder name

        Returns:
            if jsonify object in file, otherwise byte string
        """
        try:
            async with aiofiles.open(self.get_folder(bucket) / file_name, "rb") as file:
                return await file.read()

        except Exception as e:
            logger.exception(e)

    async def get_files(self, *keys: str, folder_name: str = None) -> list[dict[str, bytes | None]]:
        """
        Fetch multiple files from local storage.

        Args:
            keys: list of file paths
            folder_name: folder name

        Returns:
            list of dicts with file paths and data in bytes
        """

        folder = self.get_folder(folder_name)
        files = []

        for key in keys:
            try:
                async with aiofiles.open(folder / key, "rb") as file:
                    files.append({key: await file.read()})

            except Exception as e:
                logger.exception(e)

        return files

    async def get_link(self, key: str, bucket: str = None, **kwargs: Any) -> str:
        """
        Return file path.

        Args:
            key: object path
            bucket: bucket name

        Returns:
            File path
        """

        return (self.get_folder(bucket) / key).as_uri()

    async def stream_file(self) -> None: ...

    async def get_files_with_prefix(self, prefix: str, folder_name: str = None) -> list[str]:
        """
        Retrieve objects by file name prefix.

        Args:
            prefix: part of the name
            folder_name: folder name

        Returns:
            list of strings with file names
        """

        folder = self.get_folder(folder_name)
        files = [file.name for file in folder.glob(f"{prefix}*")]

        logger.debug(f"Found {len(files)} files with {prefix=}")
        return files

    async def save_file(self, data: bytes, object_name: str, bucket: str = None) -> str | None:
        """
        Save object to local storage.

        Args:
            data: bytes content
            object_name: file name to save
            bucket: folder name

        Returns:
            file path in S3 bucket
        """

        try:
            async with aiofiles.open(self.get_folder(bucket) / object_name, "wb") as file:
                await file.write(data)
            return object_name

        except Exception as e:
            logger.error(e)

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
                return (self.get_folder() / fetch_path).as_uri()

        except Exception as e:
            logger.error(e)

    async def delete_files_with_prefix(self, prefix: str, bucket: str = None) -> None:
        """
        Delete objects by file name prefix.

        Args:
            prefix: part of the name
            bucket: folder name
        """

        folder_name = bucket

        files_to_delete = await self.get_files_with_prefix(prefix=prefix, folder_name=folder_name)

        if not files_to_delete:
            logger.info("No files to delete.")
            return

        folder = self.get_folder(folder_name)
        for file in files_to_delete:
            os.remove(folder / file)

        logger.success(f"Removed {len(files_to_delete)} files with {prefix=}")

    # Proxy methods TODO: replace with Protocol methods after merging
    async def fetch_files(self, *keys: str, bucket: str = None) -> list[dict[str, bytes | None]]:
        return await self.get_files(*keys, folder_name=bucket)

    async def upload_remote_file_to_s3(
        self,
        link: str | None,
        object_name: str,
        extension_with: ObjectExtension = ObjectExtension.WEBP,
    ) -> str | None:
        return await self.save_remote_file(link, object_name, extension_with)

    async def stream_file_from_s3(self, file_name: str, bucket: str = None) -> None: ...

    async def get_folders_list(self, bucket: str = None) -> list[str]:
        # Not implemented
        return []

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

        folder = self.get_folder(bucket)

        for file in folder.glob(f"{prefix}*{suffix or ''}"):
            return file.name


is_local = settings.storage.backend_type == StorageBackend.LOCAL
repository: LocalStorageRepository | None = LocalStorageRepository() if is_local else None
