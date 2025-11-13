from pydantic import BaseModel, Field

from app.enums import OrderDirection


class Ordering(BaseModel):
    order_by: str = Field("created_at", description="Field name to order by", examples=["created_at", "updated_at"])
    order_direction: OrderDirection = Field(
        OrderDirection.DESC, description="Ordering direction", examples=OrderDirection.list()
    )
