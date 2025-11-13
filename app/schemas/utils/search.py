from pydantic import BaseModel, Field, SerializationInfo, field_validator, model_serializer


class Search(BaseModel):
    search: str | None = Field(None, description="String for search by")

    @field_validator("search")
    @classmethod
    def check_search(cls, v: str | None) -> str | None:
        return f"%{v}%" if v else None

    @model_serializer
    def serialize(self, info: SerializationInfo) -> dict:
        if not info.context or not self.search:  # type: ignore[attr-defined]
            return {}

        fields = info.context.get("fields", [])  # type: ignore[attr-defined]

        return {f"{field}__icontains": self.search for field in fields}
