from pydantic import UUID4, BaseModel, Field, RootModel

from app.enums import Language


class IndustryDetail(BaseModel):
    us: str = Field(description="Industry title in English")
    fr: str = Field(description="Industry title in French")

    def get_for_language(self, language: Language) -> str:
        return getattr(self, language.lower())


class IndustryResponse(RootModel):
    root: dict[UUID4, IndustryDetail]


class IndustrySelect(BaseModel):
    id: UUID4 = Field(description="Industry ID")
    title: str = Field(description="Industry title")
