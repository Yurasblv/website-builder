from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDModel


class Backlink(UUIDModel, Base):
    __tablename__ = "backlink"

    keyword: Mapped[str]
    url: Mapped[str]
    publish_at: Mapped[datetime]
    is_visible: Mapped[bool]
    page_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("page.id", name="backlink_page_id_fkey", ondelete="CASCADE"), nullable=True
    )
    pbn_id: Mapped[UUID] = mapped_column(
        ForeignKey("pbn.id", name="backlink_pbn_id_fkey", ondelete="CASCADE"), nullable=False
    )

    page = relationship("Page", passive_deletes=True)
    pbn = relationship("PBN", passive_deletes=True)

    @property
    def html_visibility(self) -> str:
        return r'style="display: block;"' if self.is_visible else r'style="display: none;"'
