from abc import ABC, abstractmethod
from typing import Any

from pydantic import EmailStr

from app.core import settings
from app.enums import ObjectExtension
from app.utils.convertors import text_normalize


class AbstractStorageRepository(ABC):
    @abstractmethod
    async def get_file_by_name(self, *args: Any, **kwargs: Any) -> Any:
        """Fetch file from storage by name."""
        raise NotImplementedError

    @abstractmethod
    async def get_files(self, *args: Any, **kwargs: Any) -> Any:
        """Get files from storage."""
        raise NotImplementedError

    @abstractmethod
    async def get_link(self, *args: Any, **kwargs: Any) -> str:
        """Create public link to file."""
        raise NotImplementedError

    @abstractmethod
    async def stream_file(self, *args: Any, **kwargs: Any) -> Any:
        """Stream file from storage."""
        raise NotImplementedError

    @abstractmethod
    async def get_files_with_prefix(self, *args: Any, **kwargs: Any) -> Any:
        """Stream file from storage."""
        raise NotImplementedError

    @abstractmethod
    async def save_file(self, *args: Any, **kwargs: Any) -> Any:
        """Save file to storage."""
        raise NotImplementedError

    @abstractmethod
    async def save_remote_file(self, *args: Any, **kwargs: Any) -> Any:
        """Save file from remote link to storage."""
        raise NotImplementedError

    # @abstractmethod
    async def delete_file(self, *args: Any, **kwargs: Any) -> Any:
        """Delete file from storage."""
        raise NotImplementedError

    # @abstractmethod
    async def delete_files(self, *args: Any, **kwargs: Any) -> Any:
        """Delete file from storage."""
        raise NotImplementedError

    @abstractmethod
    async def delete_files_with_prefix(self, *args: Any, **kwargs: Any) -> Any:
        """Delete files with prefix from storage."""
        raise NotImplementedError

    @abstractmethod
    async def get_first(self, *args: Any, **kwargs: Any) -> Any:
        """Get first file from storage."""
        raise NotImplementedError

    @abstractmethod
    async def get_folders_list(self, *args: Any, **kwargs: Any) -> Any:
        """Get first file from storage."""
        raise NotImplementedError

    @staticmethod
    def construct_object_name(
        user_email: str | EmailStr = None, extension: ObjectExtension = None, **kwargs: Any
    ) -> str:
        """
        Creating object name basing on arguments.

        Args:
            user_email: customers email
            extension: extension postfix

        Returns:
            concatenated string which represents file path in S3 bucket
        """
        parts = [text_normalize(user_email if user_email else settings.PROJECT_NAME.lower())]
        parts.extend(str(value) for value in kwargs.values() if value)
        file_name = "_".join(parts)
        if extension:
            file_name += extension
        return file_name
