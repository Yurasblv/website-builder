import random
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import UUID4, BaseModel, Field

from app.enums import PageType
from app.enums.pbn import BacklinkPublishPeriodEnum
from app.models import Backlink


class BacklinkRead(BaseModel):
    id: UUID
    pbn_id: UUID4
    page_id: UUID4
    content_file: str
    page_type: PageType
    wp_host: str
    wp_port: str

    @classmethod
    def init(cls, backlink: Backlink) -> "BacklinkRead":
        return cls(
            id=backlink.id,
            pbn_id=backlink.pbn_id,
            page_id=backlink.page_id,
            content_file=backlink.page.current_release,
            page_type=backlink.page.page_type,
            wp_host=backlink.pbn.domain.name,
            wp_port=backlink.pbn.wp_port,
        )


class BacklinkCreate(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    keyword: str
    url: str
    publish_at: datetime
    is_visible: bool = False
    page_id: UUID4
    pbn_id: UUID4

    @classmethod
    def init(
        cls,
        keyword: str,
        url: str,
        pbn_id: UUID,
        page_id: UUID,
        backlink_publish_period_option: BacklinkPublishPeriodEnum,
    ) -> "BacklinkCreate":
        option = backlink_publish_period_option == BacklinkPublishPeriodEnum.IMMEDIATE
        days = 0 if option else random.randint(3, 14)

        publish_at = datetime.now(UTC) + timedelta(days=days)

        return cls(keyword=keyword, url=url, publish_at=publish_at, pbn_id=pbn_id, page_id=page_id, is_visible=option)

    @property
    def html_visibility(self) -> str:
        return r'style="display: block;"' if self.is_visible else r'style="display: none;"'


PickledBacklinkRead = Annotated[bytes, "Pickled[BacklinkRead]"]
