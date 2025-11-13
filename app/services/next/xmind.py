import aiohttp
from loguru import logger
from pydantic import UUID4
from sentry_sdk import capture_exception

from app.core import settings
from app.services.storages import ovh_service
from app.utils import UnitOfWorkNoPool


class XMindGeneratorService:
    url = settings.next.URL + "/api/xmind/"

    @classmethod
    async def generate(cls, cluster_id: UUID4 | str) -> bytes | None:
        """
        Generate xmind file, upload it to S3 and update cluster with the link.
        Args:
            cluster_id: cluster id

        Returns:
            bytes: xmind file
        """

        from app.services.page.page_cluster import ClusterPageService

        async with UnitOfWorkNoPool() as uow:
            pages = await uow.page_cluster.get_multi(cluster_id=cluster_id)

        page_map, children_map = ClusterPageService._create_maps(pages)
        root_pages = [page for page in pages if not page.parent_id]
        data = ClusterPageService._build_pages_relations(root_pages, children_map)

        json_data = data[0].model_dump(mode="json", exclude_none=True)

        try:
            async with (
                aiohttp.ClientSession(raise_for_status=True, headers={"Content-Type": "application/json"}) as session,
                session.post(cls.url, json=json_data) as response,
            ):
                xmind_content = await response.read()

            link = await ovh_service.save_file(data=xmind_content, object_name=f"{cluster_id}/mindmap.xmind")

            async with UnitOfWorkNoPool() as uow:
                await uow.cluster.update(dict(xmind=link), id=cluster_id)

            return xmind_content

        except aiohttp.ConnectionTimeoutError as e:
            logger.warning(f"Timeout making request to Next service: {e}")

        except Exception as e:
            capture_exception(e)
            logger.warning(f"Error making request to Next service: {e}")
