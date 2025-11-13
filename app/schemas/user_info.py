import string
from datetime import datetime
from decimal import Decimal

import bcrypt
from pydantic import UUID4, BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core import settings
from app.enums import AppType, Language


def validate_password(password: str) -> str:
    _password = set(password)

    if not settings.auth.PASSWORD_INCLUDE_CHARACTERS.intersection(_password):
        raise ValueError(
            f"Password must contains at least one special symbol. Allowed: {settings.auth.PASSWORD_INCLUDE_CHARACTERS}"
        )

    elif not set(string.digits).intersection(_password):
        raise ValueError("Password must contains at least 1 digit.")

    elif not set(string.ascii_uppercase).intersection(_password):
        raise ValueError("Password must contains at least 1 upper letter.")

    elif not set(string.ascii_lowercase).intersection(_password):
        raise ValueError("Password must contains at least 1 lower letter.")

    return password


class SignIn(BaseModel):
    email: EmailStr
    password: str = Field(description="Password must be hashed before saving to the database.", min_length=8)

    @field_validator("password")
    @classmethod
    def validate_password(cls, password: str) -> str:
        return validate_password(password)


class SignInOutput(BaseModel):
    access_token: str
    refresh_token: str
    access_token_expires: int
    refresh_token_expires: int


class UserInfoBase(BaseModel):
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    language: Language = Field(default=Language.US)


class UserInfoResponse(UserInfoBase):
    is_active: bool
    last_online: datetime
    role: str
    balance: Decimal
    is_card_validated: bool
    invited_by_id: UUID4 | None
    company_id: UUID4 | None
    is_bound: bool = False

    model_config = ConfigDict(from_attributes=True)

    @field_validator("balance")
    @classmethod
    def validate_balance(cls, balance: Decimal) -> Decimal:
        return round(balance, 2)


class UserInfoRead(UserInfoResponse):
    id: UUID4
    is_blogger: bool = False
    created_at: datetime
    ctr_access: bool = False


class UserCreate(SignIn, UserInfoBase):
    app: AppType | None = Field(None, description="App type, which user used to sign in.")
    referral_code: str | None = None

    @field_validator("language", mode="before")
    @classmethod
    def validate_language(cls, language: str) -> str:
        if language not in Language.list():
            return Language.US
        return language


class UserInfoUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    password: str | None = Field(None, description="Hash before saving to the database.", min_length=8)
    language: Language | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, password: str | None) -> str | None:
        if password is None:
            return None

        if password := validate_password(password):
            return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


class UserInfoReferral(UserInfoBase):
    id: UUID4
    amount: Decimal
