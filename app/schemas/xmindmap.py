from __future__ import annotations

from datetime import UTC, datetime

from pydantic import UUID4, BaseModel, ConfigDict, Field


class XMindmapBase(BaseModel):
    id: UUID4
    topic: str
    parent_id: UUID4 | None = None
    children: list[XMindmapBase] = Field(default_factory=list, description="List of children.")
    created_at: datetime | None = Field(default_factory=lambda: datetime.now(UTC), description="MindMap creation date.")

    model_config = ConfigDict(arbitrary_types_allowed=True)
