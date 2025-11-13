import asyncio
import os
import shutil
import subprocess
from functools import wraps
from typing import Any, Callable, Coroutine
from uuid import uuid4

from loguru import logger
from pydantic import UUID4
from sentry_sdk import capture_exception

from app.core.config import settings
from app.core.exc import ClusterBuilderException
from app.enums import ClusterEventEnum, PBNExtraPageEventEnum
from app.schemas.elements.cluster_pages.base import BaseStyle
from app.services.cluster import ClusterService
from app.services.storages import ovh_service
from app.utils import UnitOfWorkNoPool, enqueue_global_message


def track_progress(start_progress: int = 0, end_progress: int = 100, duration: int = 30) -> Callable:
    """
    Decorator to track the progress of a function.

    Args:
        start_progress: Initial progress from 0 to 1
        end_progress: Final progress from 0 to 1
        duration: Period in seconds for the progress to complete
    """

    async def progress_reporter(start: int, end: int, period: int, instance: "ClusterStaticBuilder") -> None:
        progress = start
        progress_range = end - start_progress
        progress_interval = period / progress_range

        while progress <= end:
            await instance.update_progress(progress)
            progress += 1
            await asyncio.sleep(progress_interval)

    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
        @wraps(func)
        async def wrapper(self: "ClusterStaticBuilder", *args: Any, **kwargs: Any) -> Any:
            progress_task = None
            try:
                progress_task = asyncio.create_task(progress_reporter(start_progress, end_progress, duration, self))

                result = await func(self, *args, **kwargs)

                if progress_task.done():
                    return result

                try:
                    progress_task.cancel()
                except asyncio.CancelledError:
                    pass

                await self.update_progress(end_progress)
                return result

            except Exception as e:
                if progress_task and not progress_task.done():
                    progress_task.cancel()

                raise e

        return wrapper

    return decorator


class ClusterStaticBuilder(ClusterService):
    unit_of_work = UnitOfWorkNoPool

    def __init__(self, cluster_id: str, user_id: str) -> None:
        super().__init__()
        self.cluster_id = cluster_id
        self.user_id = user_id
        self.keyword = None
        self.container = f"{settings.build.image}-{uuid4()}"
        self.image = settings.build.image
        self.volume = settings.build.BUILD_DATA_VOLUME_NAME

        self.temp_dir = os.path.join(os.getcwd(), "temp", self.cluster_id)
        self.build_dir = os.path.join(self.temp_dir, "build")

    async def __aenter__(self) -> "ClusterStaticBuilder":
        await self.setup()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.teardown()
        await logger.complete()

        if exc_val:
            raise exc_val

    async def setup(self) -> None:
        """Setup method to create the temporary directories."""

        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.build_dir, exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, "pages"), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, "images"), exist_ok=True)

        # print structure for debugging
        logger.debug(f"Temporary directory structure: {os.listdir(self.temp_dir)}")

    async def teardown(self) -> None:
        """Cleanup method to remove temporary files and directories."""

        try:
            shutil.rmtree(self.temp_dir)
        except Exception as e:
            capture_exception(e)

    @track_progress(end_progress=10, duration=20)
    async def prepare_data(self) -> tuple[str, dict, dict, bytes | None]:
        return await self.get_static_cluster_files(self.cluster_id, self.user_id)

    @track_progress(start_progress=10, end_progress=15, duration=10)
    async def save_temp_files(self, pages: dict, images: dict, author: bytes | None) -> None:
        """
        Saves temporary files to the temporary directory.

        Args:
            pages: The pages to save.
            images: The images to save.
            author: The author image to save.
        """

        for page_name, page in pages.items():
            with open(os.path.join(self.temp_dir, "pages", f"{page_name}.json"), "w") as f:
                f.write(page.model_dump_json())

        for image_name, content in images.items():
            with open(os.path.join(self.temp_dir, "images", image_name), "wb") as f:
                f.write(content)

        if author:
            with open(os.path.join(self.temp_dir, "images", "author.webp"), "wb") as f:
                f.write(author)

    @track_progress(start_progress=15, end_progress=70, duration=40)
    async def build_command(self) -> None:
        """Constructs the command to build the static files for a cluster."""

        build_command = (
            f"docker run "
            f"--name {self.container} "
            f"-e NEXT_PUBLIC_CLUSTER_KEYWORD='{self.keyword}' "
            f"-e NEXT_PUBLIC_CLUSTER_ID='{self.cluster_id}' "
            f"-v {self.volume}:/app/data "
            f"{self.image}"
        )

        logger.debug(f"Running build command: {build_command}")

        build_process = await asyncio.create_subprocess_shell(
            build_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        stdout, stderr = await build_process.communicate()

        if build_process.returncode != 0:
            error = stderr.decode()
            raise ClusterBuilderException(f"Error building files: {error}", error=error)

        logger.debug("Build completed successfully.")

    @track_progress(start_progress=70, end_progress=75, duration=5)
    async def copy_command(self) -> None:
        """Constructs the command to copy the static files from the Docker container to the local directory."""

        copy_command = f"docker cp {self.container}:app/build/ {self.build_dir}"
        logger.debug(f"Copying static files with command: {copy_command}")

        copy_process = await asyncio.create_subprocess_shell(
            copy_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        stdout, stderr = await copy_process.communicate()

        if copy_process.returncode != 0:
            error = stderr.decode()
            raise ClusterBuilderException(f"Error copying files: {error}", error=error)

        logger.debug("Static files copied successfully.")

    @track_progress(start_progress=75, end_progress=95, duration=15)
    async def save_archive(self) -> str:
        """Uploads a cluster archive to cloud storage and updates the database."""

        with open(os.path.join(self.build_dir, "build", f"{self.keyword}.zip"), "rb") as f:
            object_name = f"{self.cluster_id}/{self.keyword}.zip"
            return await ovh_service.save_file(object_name=object_name, data=f.read())  # type:ignore[return-value]

    @track_progress(start_progress=95, duration=5)
    async def remove_command(self) -> None:
        """Constructs the command to remove the Docker container."""

        remove_command = f"docker rm {self.container}"
        logger.debug(f"Removing container with command: {remove_command}")

        remove_process = await asyncio.create_subprocess_shell(
            remove_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        stdout, stderr = await remove_process.communicate()

        if remove_process.returncode != 0:
            error = stderr.decode()
            raise ClusterBuilderException(f"Error removing container: {error}", error=error)

        logger.debug("Container removed successfully.")

    async def build(self) -> str:
        """
        Collects static files for a cluster, builds the static content, and saves it to a zip archive.

        Returns:
            The path to the saved zip archive.
        """

        async with self:
            self.keyword, pages, images, author = await self.prepare_data()

            await self.save_temp_files(pages, images, author)
            await self.build_command()
            await self.copy_command()
            file_path = await self.save_archive()

            await self.remove_command()

        return file_path

    async def update_progress(self, progress: float) -> None:
        await enqueue_global_message(
            event=ClusterEventEnum.BUILDING,
            user_id=self.user_id,
            cluster_id=self.cluster_id,
            progress=round(progress, 2),
        )


class PageStaticBuilder(ClusterStaticBuilder):
    def __init__(
        self, *args: Any, page_id: UUID4 | str, pbn_id: UUID4 | str, page_style: BaseStyle, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.page_id = page_id
        self.page_style = page_style
        self.pbn_id = pbn_id

    @track_progress(end_progress=10, duration=20)
    async def prepare_data(self) -> tuple[str, dict, dict, bytes | None]:
        from app.services.pbn import PBNService

        return await PBNService.get_static_extra_page_files(
            pbn_id=self.pbn_id, page_id=self.page_id, page_style=self.page_style
        )

    async def update_progress(self, progress: float) -> None:
        await enqueue_global_message(
            event=PBNExtraPageEventEnum.BUILDING,
            user_id=self.user_id,
            page_id=self.page_id,
            pbn_id=self.pbn_id,
            progress=round(progress, 2),
        )
