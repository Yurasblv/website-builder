from pydantic import UUID4, BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.utils.password_encryptor import PasswordEncryptor


class ServiceAccountBase(BaseModel):
    id: UUID4
    email: EmailStr
    password: str
    session: str

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


class ServiceAccountUpdate(BaseModel):
    password: str = Field(description="Service account password")

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    @field_validator("password", mode="before")
    @classmethod
    def encrypt_password(cls, value: str) -> str:
        """Encrypts the password before storing it in the model."""

        value = value.strip()
        if not value:
            raise ValueError("Password cannot be empty")

        return PasswordEncryptor.encrypt(value)


class ServiceAccountCreate(ServiceAccountUpdate):
    email: EmailStr


class ServiceAccountResponse(BaseModel):
    id: UUID4 = Field(description="Service account db id")
    email: EmailStr
