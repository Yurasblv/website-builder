from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class UUIDModel:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4, index=True)


class CreatedAtModel:
    created_at: Mapped[datetime] = mapped_column(default=func.now(), server_default=func.now(), index=True)


class UpdatedAtModel:
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now(), server_default=func.now())


class TimestampModel(CreatedAtModel, UpdatedAtModel):
    """Model with created_at and updated_at fields"""


class Base(DeclarativeBase):
    type_annotation_map = {
        UUID: postgresql.UUID,
        dict[str, Any]: postgresql.JSON,
        list[dict[str, Any]]: postgresql.ARRAY(postgresql.JSON),
        list[str]: postgresql.ARRAY(String),
        list[UUID]: postgresql.ARRAY(postgresql.UUID),
        Decimal: postgresql.NUMERIC(10, 2),
        datetime: DateTime(timezone=True),
        bool: Boolean,
    }
