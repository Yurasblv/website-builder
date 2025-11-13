from uuid import uuid4

from pydantic import UUID4, BaseModel, Field

from app.enums.page import PageStatus, PageType


class PageBase(BaseModel):
    id: UUID4 = Field(default_factory=uuid4)
    content_file: list | None = Field(default=[], description="File contains generated page.")
    status: PageStatus = Field(default=PageStatus.DRAFT)
    page_type: PageType
