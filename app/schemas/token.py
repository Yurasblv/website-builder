from pydantic import UUID4, AliasChoices, BaseModel, Field


class Token(BaseModel):
    email: str
    first_name: str | None = Field(None, validation_alias=AliasChoices("first_name", "given_name", "email"))
    last_name: str | None = Field(None, validation_alias=AliasChoices("last_name", "family_name", "email"))


class TokenCredentials(BaseModel):
    access_token: str
    api_key: str
    user_email: str
    user_id: UUID4
