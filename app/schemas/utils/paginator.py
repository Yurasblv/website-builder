from typing import Generic, TypeVar

from pydantic import BaseModel, Field, model_validator

M = TypeVar("M")


class PaginateBase(BaseModel):
    count: int = Field(description="Number of total items")
    total_pages: int = Field(description="Number of total pages")


class PaginatedOutput(BaseModel, Generic[M]):
    count: int = Field(description="Number of total items")
    total_pages: int = Field(description="Number of total pages")
    input_items: list[M] = Field(description="List of items before pagination")


class PaginatedResponse(PaginateBase, Generic[M]):
    items: list[M] = Field(None, description="List of items returned in a paginated response")

    input_items: list[M] = Field(description="List of items before grouping", exclude=True)

    @model_validator(mode="after")
    def fill_items(self) -> "PaginatedResponse[M]":
        self.items: list[M] = self.input_items
        return self


class PaginatedGroupedResponse(PaginateBase, Generic[M]):
    items: dict[str, list[M]] = Field(None, description="List of items returned in a paginated response")

    input_items: list[M] = Field(description="List of items before grouping", exclude=True)

    @model_validator(mode="after")
    def group_items(self) -> "PaginatedGroupedResponse[M]":
        self.items: dict[str, list[M]] = {}

        for item in self.input_items:
            created_at = str(item.created_at.date())  # type: ignore
            self.items.setdefault(created_at, []).append(item)

        return self


class PaginationFilter(BaseModel):
    page: int = Field(1, description="Page number", ge=1)
    per_page: int = Field(10, description="Number of items per page", ge=1)
